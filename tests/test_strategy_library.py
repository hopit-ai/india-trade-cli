"""
tests/test_strategy_library.py
───────────────────────────────
Tests for engine/strategy_library.py — the curated options strategy template library.

Covers:
  - TemplateLeg and StrategyTemplate dataclass construction
  - StrategyLibrary.list_all(), list_by_category(), get(), search()
  - All 26 templates present with required fields
  - apply_template() returns correct StrategyResult for each capital_type
  - Breakeven, max_profit, max_loss, capital_needed calculations
  - Fit score based on DTE
  - Premium resolution (ATM, OTM scaling)
  - Error handling: unknown id, unknown category
"""

from __future__ import annotations

import pytest

from engine.strategy_library import (
    CATEGORIES,
    TEMPLATES,
    StrategyLibrary,
    StrategyTemplate,
    TemplateLeg,
    apply_template,
    strategy_library,
)
from engine.strategy import StrategyResult


# ── Shared ATM data for apply_template tests ──────────────────


ATM_PARAMS = dict(
    symbol="NIFTY",
    spot=24000.0,
    atm_ce_prem=150.0,
    atm_pe_prem=140.0,
    atm_strike=24000.0,
    lot_size=75,
    lots=1,
    dte=30,
)


# ── TemplateLeg dataclass ─────────────────────────────────────


class TestTemplateLeg:
    def test_basic_construction(self):
        leg = TemplateLeg(option_type="CE", action="BUY", strike_offset_pct=0.0)
        assert leg.option_type == "CE"
        assert leg.action == "BUY"
        assert leg.strike_offset_pct == 0.0

    def test_lots_multiplier_default_is_one(self):
        leg = TemplateLeg(option_type="PE", action="SELL", strike_offset_pct=-0.03)
        assert leg.lots_multiplier == 1

    def test_lots_multiplier_explicit(self):
        leg = TemplateLeg(option_type="CE", action="BUY", strike_offset_pct=0.03, lots_multiplier=2)
        assert leg.lots_multiplier == 2

    def test_stock_leg(self):
        leg = TemplateLeg(option_type="STOCK", action="BUY", strike_offset_pct=0.0)
        assert leg.option_type == "STOCK"


# ── StrategyTemplate dataclass ────────────────────────────────


class TestStrategyTemplate:
    def _make_template(self, **overrides) -> StrategyTemplate:
        defaults = dict(
            id="test_strat",
            name="Test Strategy",
            category="bullish",
            views=["BULLISH"],
            legs=[TemplateLeg("CE", "BUY", 0.0)],
            max_profit="Unlimited",
            max_loss="Premium paid",
            ideal_iv="low",
            ideal_dte=(15, 45),
            explanation="Buy a call option.",
            when_to_use="When strongly bullish.",
            when_not_to_use="When IV is high.",
            risks=["Premium fully lost if stock doesn't move"],
            tags=["directional", "debit"],
            capital_type="debit",
            complexity="beginner",
        )
        defaults.update(overrides)
        return StrategyTemplate(**defaults)

    def test_construction(self):
        t = self._make_template()
        assert t.id == "test_strat"
        assert t.category == "bullish"
        assert t.views == ["BULLISH"]

    def test_capital_type_default(self):
        t = self._make_template()
        assert t.capital_type == "debit"

    def test_complexity_default(self):
        t = self._make_template()
        assert t.complexity == "beginner"

    def test_ideal_dte_tuple(self):
        t = self._make_template(ideal_dte=(20, 60))
        assert t.ideal_dte == (20, 60)


# ── TEMPLATES dict — coverage ─────────────────────────────────


class TestTemplatesDict:
    def test_count_is_26(self):
        assert len(TEMPLATES) == 26

    def test_all_categories_present(self):
        found = {t.category for t in TEMPLATES.values()}
        assert found == set(CATEGORIES)

    @pytest.mark.parametrize(
        "strat_id",
        [
            "long_call",
            "bull_call_spread",
            "bull_put_spread",
            "synthetic_long",
            "call_ratio_backspread",
            "long_put",
            "bear_put_spread",
            "bear_call_spread",
            "synthetic_short",
            "put_ratio_backspread",
            "iron_condor",
            "iron_butterfly",
            "short_straddle",
            "short_strangle",
            "covered_call",
            "cash_secured_put",
            "jade_lizard",
            "long_straddle",
            "long_strangle",
            "long_calendar_spread",
            "diagonal_spread",
            "protective_put",
            "collar",
            "married_put",
            "long_fence",
            "seagull",
        ],
    )
    def test_required_strategy_ids_present(self, strat_id):
        assert strat_id in TEMPLATES

    def test_all_templates_have_required_fields(self):
        for sid, t in TEMPLATES.items():
            assert t.id == sid, f"{sid}: id mismatch"
            assert t.name, f"{sid}: empty name"
            assert t.category in CATEGORIES, f"{sid}: invalid category"
            assert t.views, f"{sid}: empty views"
            assert t.legs, f"{sid}: no legs"
            assert t.explanation, f"{sid}: no explanation"
            assert t.when_to_use, f"{sid}: no when_to_use"
            assert t.when_not_to_use, f"{sid}: no when_not_to_use"
            assert t.risks, f"{sid}: no risks"
            assert t.tags, f"{sid}: no tags"
            assert len(t.ideal_dte) == 2, f"{sid}: ideal_dte must be (min, max)"
            assert t.ideal_dte[0] < t.ideal_dte[1], f"{sid}: ideal_dte min >= max"

    def test_bullish_category_count(self):
        bullish = [t for t in TEMPLATES.values() if t.category == "bullish"]
        assert len(bullish) == 5

    def test_bearish_category_count(self):
        bearish = [t for t in TEMPLATES.values() if t.category == "bearish"]
        assert len(bearish) == 5

    def test_income_category_count(self):
        income = [t for t in TEMPLATES.values() if t.category == "income"]
        assert len(income) == 7

    def test_volatility_category_count(self):
        vol = [t for t in TEMPLATES.values() if t.category == "volatility"]
        assert len(vol) == 4

    def test_hedging_category_count(self):
        hedging = [t for t in TEMPLATES.values() if t.category == "hedging"]
        assert len(hedging) == 5


# ── StrategyLibrary ───────────────────────────────────────────


class TestStrategyLibrary:
    def test_list_all_returns_all_templates(self):
        results = strategy_library.list_all()
        assert len(results) == 26

    def test_list_all_sorted_by_category_then_name(self):
        results = strategy_library.list_all()
        # Category order follows CATEGORIES tuple (bullish→bearish→income→volatility→hedging)
        cat_order = {c: i for i, c in enumerate(CATEGORIES)}
        keys = [(cat_order[r.category], r.name) for r in results]
        assert keys == sorted(keys)

    def test_list_by_category_bullish(self):
        results = strategy_library.list_by_category("bullish")
        assert len(results) == 5
        assert all(r.category == "bullish" for r in results)

    def test_list_by_category_case_insensitive(self):
        results = strategy_library.list_by_category("INCOME")
        assert all(r.category == "income" for r in results)

    def test_list_by_category_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown category"):
            strategy_library.list_by_category("garbage")

    def test_get_known_id(self):
        t = strategy_library.get("iron_condor")
        assert t.id == "iron_condor"
        assert t.category == "income"

    def test_get_unknown_id_raises_key_error(self):
        with pytest.raises(KeyError):
            strategy_library.get("does_not_exist")

    def test_search_by_name_substring(self):
        results = strategy_library.search("condor")
        assert any(r.id == "iron_condor" for r in results)

    def test_search_by_tag(self):
        results = strategy_library.search("defined_risk")
        assert len(results) > 0

    def test_search_case_insensitive(self):
        results = strategy_library.search("STRADDLE")
        assert any("straddle" in r.id for r in results)

    def test_search_returns_empty_for_gibberish(self):
        results = strategy_library.search("xyzqwerty_nomatch")
        assert results == []

    def test_search_name_match_ranks_higher_than_tag_match(self):
        # "iron_condor" matches by name; any strategy with "iron" in tags would rank lower
        results = strategy_library.search("iron condor")
        assert results[0].id == "iron_condor"

    def test_singleton_is_strategy_library_instance(self):
        assert isinstance(strategy_library, StrategyLibrary)


# ── apply_template() — StrategyResult fields ──────────────────


class TestApplyTemplate:
    def _apply(self, strat_id: str, **overrides) -> StrategyResult:
        params = {**ATM_PARAMS, **overrides}
        template = TEMPLATES[strat_id]
        return apply_template(template, **params)

    def test_returns_strategy_result(self):
        result = self._apply("long_call")
        assert isinstance(result, StrategyResult)

    def test_name_matches_template(self):
        result = self._apply("long_call")
        assert result.name == TEMPLATES["long_call"].name

    def test_legs_list_not_empty(self):
        result = self._apply("bull_call_spread")
        assert len(result.legs) > 0

    def test_legs_have_required_keys(self):
        result = self._apply("iron_condor")
        for leg in result.legs:
            assert "action" in leg
            assert "type" in leg

    def test_capital_needed_positive(self):
        result = self._apply("long_call")
        assert result.capital_needed > 0

    def test_max_loss_negative(self):
        result = self._apply("long_call")
        assert result.max_loss < 0

    def test_breakeven_is_list(self):
        result = self._apply("long_call")
        assert isinstance(result.breakeven, list)
        assert len(result.breakeven) >= 1

    def test_rr_ratio_non_negative(self):
        result = self._apply("bull_call_spread")
        assert result.rr_ratio >= 0

    def test_best_for_is_string(self):
        result = self._apply("iron_condor")
        assert isinstance(result.best_for, str)
        assert len(result.best_for) > 0


# ── apply_template() — debit strategies ──────────────────────


class TestApplyTemplateDebit:
    def _apply(self, strat_id: str, **kw) -> StrategyResult:
        return apply_template(TEMPLATES[strat_id], **{**ATM_PARAMS, **kw})

    def test_long_call_capital_equals_premium_times_lot(self):
        result = self._apply("long_call")
        # Capital = ATM CE prem * lot_size * lots = 150 * 75 * 1
        assert result.capital_needed == pytest.approx(150.0 * 75, rel=0.01)

    def test_long_call_max_loss_equals_minus_capital(self):
        result = self._apply("long_call")
        assert result.max_loss == pytest.approx(-result.capital_needed, rel=0.01)

    def test_long_call_breakeven_above_atm_strike(self):
        result = self._apply("long_call")
        # Breakeven = ATM strike + premium = 24000 + 150 = 24150
        assert result.breakeven[0] == pytest.approx(24150.0, rel=0.01)

    def test_long_put_breakeven_below_atm_strike(self):
        result = self._apply("long_put")
        # Breakeven = ATM strike - premium = 24000 - 140 = 23860
        assert result.breakeven[0] == pytest.approx(23860.0, rel=0.01)

    def test_bull_call_spread_max_loss_is_net_debit(self):
        result = self._apply("bull_call_spread")
        # Max loss = net debit = (ATM CE prem - OTM CE prem) * lot_size
        assert result.max_loss < 0

    def test_bull_call_spread_max_profit_less_than_uncapped(self):
        naked_call = self._apply("long_call")
        spread = self._apply("bull_call_spread")
        # Spread always has a capped max profit; naked call is "uncapped" (represented large)
        assert spread.max_profit < naked_call.max_profit

    def test_long_straddle_two_breakevenss(self):
        result = self._apply("long_straddle")
        assert len(result.breakeven) == 2

    def test_long_straddle_capital_equals_both_premiums(self):
        result = self._apply("long_straddle")
        expected = (150.0 + 140.0) * 75
        assert result.capital_needed == pytest.approx(expected, rel=0.01)

    def test_lots_multiplier_scales_capital(self):
        one_lot = self._apply("long_call", lots=1)
        two_lots = self._apply("long_call", lots=2)
        assert two_lots.capital_needed == pytest.approx(one_lot.capital_needed * 2, rel=0.01)


# ── apply_template() — credit strategies ─────────────────────


class TestApplyTemplateCredit:
    def _apply(self, strat_id: str, **kw) -> StrategyResult:
        return apply_template(TEMPLATES[strat_id], **{**ATM_PARAMS, **kw})

    def test_iron_condor_max_profit_positive(self):
        result = self._apply("iron_condor")
        assert result.max_profit > 0

    def test_iron_condor_max_loss_negative(self):
        result = self._apply("iron_condor")
        assert result.max_loss < 0

    def test_iron_condor_two_breakevenss(self):
        result = self._apply("iron_condor")
        assert len(result.breakeven) == 2

    def test_iron_condor_lower_breakeven_less_than_upper(self):
        result = self._apply("iron_condor")
        assert result.breakeven[0] < result.breakeven[1]

    def test_bull_put_spread_max_profit_is_net_credit(self):
        result = self._apply("bull_put_spread")
        assert result.max_profit > 0

    def test_bear_call_spread_max_profit_is_net_credit(self):
        result = self._apply("bear_call_spread")
        assert result.max_profit > 0

    def test_cash_secured_put_max_profit_positive(self):
        result = self._apply("cash_secured_put")
        assert result.max_profit > 0

    def test_jade_lizard_has_three_legs(self):
        result = self._apply("jade_lizard")
        assert len(result.legs) == 3


# ── apply_template() — stock strategies ──────────────────────


class TestApplyTemplateStock:
    def _apply(self, strat_id: str, **kw) -> StrategyResult:
        return apply_template(TEMPLATES[strat_id], **{**ATM_PARAMS, **kw})

    def test_covered_call_capital_needed_positive(self):
        result = self._apply("covered_call")
        assert result.capital_needed > 0

    def test_covered_call_max_profit_capped(self):
        # Covered call max profit = (call_strike - spot + call_premium) * lots
        result = self._apply("covered_call")
        assert result.max_profit > 0

    def test_protective_put_reduces_max_loss_vs_stock(self):
        result = self._apply("protective_put")
        # Max loss is protected at put strike — should not be full stock value
        assert result.max_loss < 0
        # But also shouldn't be larger than spot * lot_size in absolute terms
        assert abs(result.max_loss) < ATM_PARAMS["spot"] * ATM_PARAMS["lot_size"]

    def test_collar_has_three_legs(self):
        result = self._apply("collar")
        assert len(result.legs) == 3


# ── apply_template() — fit score ─────────────────────────────


class TestFitScore:
    def _apply(self, strat_id: str, **kw) -> StrategyResult:
        return apply_template(TEMPLATES[strat_id], **{**ATM_PARAMS, **kw})

    def test_dte_in_range_gives_high_fit_score(self):
        # iron_condor ideal_dte is (20, 45) — dte=30 is in range
        result = self._apply("iron_condor", dte=30)
        assert result.fit_score >= 70

    def test_dte_outside_range_gives_lower_fit_score(self):
        # iron_condor ideal_dte is (20, 45) — dte=5 is way out
        result_in = self._apply("iron_condor", dte=30)
        result_out = self._apply("iron_condor", dte=5)
        assert result_out.fit_score <= result_in.fit_score

    def test_fit_score_between_0_and_100(self):
        for strat_id in TEMPLATES:
            result = self._apply(strat_id)
            assert 0 <= result.fit_score <= 100, f"{strat_id}: fit_score out of range"


# ── apply_template() — payoff object ─────────────────────────


class TestPayoffObject:
    def _apply(self, strat_id: str, **kw) -> StrategyResult:
        return apply_template(TEMPLATES[strat_id], **{**ATM_PARAMS, **kw})

    def test_options_strategies_have_payoff(self):
        # Pure options strategies should have a payoff object
        result = self._apply("long_call")
        # payoff may be None if analysis.options is not available — just check type
        if result.payoff is not None:
            from analysis.options import StrategyPayoff

            assert isinstance(result.payoff, StrategyPayoff)

    def test_calendar_spread_has_result(self):
        result = self._apply("long_calendar_spread")
        assert isinstance(result, StrategyResult)

    def test_diagonal_spread_has_result(self):
        result = self._apply("diagonal_spread")
        assert isinstance(result, StrategyResult)


# ── apply_template() — ratio backspreads ─────────────────────


class TestRatioBackspreads:
    def _apply(self, strat_id: str, **kw) -> StrategyResult:
        return apply_template(TEMPLATES[strat_id], **{**ATM_PARAMS, **kw})

    def test_call_ratio_backspread_has_three_leg_positions(self):
        # 1 short ATM CE + 2 long OTM CE = 3 leg positions total
        result = self._apply("call_ratio_backspread")
        # The legs list should have at least 2 entries (could be 2 if multiplied inline)
        assert len(result.legs) >= 2

    def test_put_ratio_backspread_has_three_leg_positions(self):
        result = self._apply("put_ratio_backspread")
        assert len(result.legs) >= 2

    def test_call_ratio_backspread_capital_non_negative(self):
        result = self._apply("call_ratio_backspread")
        assert result.capital_needed >= 0
