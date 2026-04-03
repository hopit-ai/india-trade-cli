"""Tests for engine/trader.py — TraderAgent, position sizing, strategy selection."""

from engine.trader import (
    TraderAgent, TradePlan, OrderLeg, ExitPlan, RISK_PROFILES, LOT_SIZES, _parse_synthesis_verdict,
)


# ── Risk Profiles ────────────────────────────────────────────

class TestRiskProfiles:
    def test_all_three_profiles_exist(self):
        assert "aggressive" in RISK_PROFILES
        assert "neutral" in RISK_PROFILES
        assert "conservative" in RISK_PROFILES

    def test_aggressive_has_highest_risk(self):
        assert RISK_PROFILES["aggressive"].risk_pct > RISK_PROFILES["neutral"].risk_pct
        assert RISK_PROFILES["neutral"].risk_pct > RISK_PROFILES["conservative"].risk_pct

    def test_conservative_has_widest_stop(self):
        assert RISK_PROFILES["conservative"].sl_atr_mult > RISK_PROFILES["aggressive"].sl_atr_mult

    def test_profile_fields(self):
        p = RISK_PROFILES["neutral"]
        assert p.name == "Neutral"
        assert p.risk_pct > 0
        assert p.sl_atr_mult > 0
        assert p.max_position_pct > 0
        assert p.target_rr > 0


# ── TraderAgent construction ────────────────────────────────

class TestTraderAgentInit:
    def test_default_capital(self):
        t = TraderAgent()
        assert t.capital == 200000

    def test_custom_capital(self):
        t = TraderAgent(capital=500000)
        assert t.capital == 500000

    def test_default_profile_is_neutral(self):
        t = TraderAgent()
        assert t.profile.name == "Neutral"

    def test_aggressive_profile(self):
        t = TraderAgent(profile="aggressive")
        assert t.profile.name == "Aggressive"

    def test_conservative_profile(self):
        t = TraderAgent(profile="conservative")
        assert t.profile.name == "Conservative"

    def test_unknown_profile_falls_back_to_neutral(self):
        t = TraderAgent(profile="unknown_xyz")
        assert t.profile.name == "Neutral"


# ── generate_plan ────────────────────────────────────────────

class TestGeneratePlan:
    def test_hold_returns_none(self):
        t = TraderAgent(capital=200000)
        plan = t.generate_plan("RELIANCE", verdict="HOLD", confidence=50, ltp=2500, atr=50)
        assert plan is None

    def test_buy_returns_plan(self):
        t = TraderAgent(capital=200000)
        plan = t.generate_plan(
            "RELIANCE", verdict="BUY", confidence=75,
            ltp=2500, atr=50, support=2400, resistance=2700,
        )
        assert plan is not None
        assert isinstance(plan, TradePlan)
        assert plan.direction == "LONG"
        assert plan.symbol == "RELIANCE"

    def test_sell_returns_short_plan(self):
        t = TraderAgent(capital=200000)
        plan = t.generate_plan(
            "RELIANCE", verdict="SELL", confidence=80,
            ltp=2500, atr=50,
        )
        assert plan is not None
        assert plan.direction == "SHORT"

    def test_negative_ltp_returns_none(self):
        t = TraderAgent(capital=200000)
        plan = t.generate_plan("RELIANCE", verdict="BUY", confidence=75, ltp=-1)
        assert plan is None

    def test_plan_has_entry_orders(self):
        t = TraderAgent(capital=200000)
        plan = t.generate_plan(
            "RELIANCE", verdict="BUY", confidence=75,
            ltp=2500, atr=50,
        )
        assert plan is not None
        assert len(plan.entry_orders) > 0
        assert isinstance(plan.entry_orders[0], OrderLeg)

    def test_plan_has_exit_plan(self):
        t = TraderAgent(capital=200000)
        plan = t.generate_plan(
            "RELIANCE", verdict="BUY", confidence=75,
            ltp=2500, atr=50,
        )
        assert plan is not None
        assert plan.exit_plan is not None
        assert plan.exit_plan.stop_loss > 0

    def test_risk_amount_respects_capital(self):
        t = TraderAgent(capital=100000)
        plan = t.generate_plan(
            "TCS", verdict="BUY", confidence=70,
            ltp=3500, atr=70,
        )
        assert plan is not None
        assert plan.capital_deployed <= 100000
        assert plan.max_risk <= 100000

    def test_symbol_uppercased(self):
        t = TraderAgent(capital=200000)
        plan = t.generate_plan("reliance", verdict="BUY", confidence=75, ltp=2500, atr=50)
        assert plan is not None
        assert plan.symbol == "RELIANCE"


# ── generate_all_plans ───────────────────────────────────────

class TestGenerateAllPlans:
    def test_returns_three_personas(self):
        t = TraderAgent(capital=200000)
        plans = t.generate_all_plans(
            "RELIANCE", verdict="BUY", confidence=75,
            ltp=2500, atr=50,
        )
        assert "aggressive" in plans
        assert "neutral" in plans
        assert "conservative" in plans

    def test_aggressive_deploys_more_capital(self):
        t = TraderAgent(capital=200000)
        plans = t.generate_all_plans(
            "INFY", verdict="BUY", confidence=75,
            ltp=1500, atr=30,
        )
        agg = plans["aggressive"]
        con = plans["conservative"]
        if agg and con:
            assert agg.max_risk >= con.max_risk


# ── _parse_synthesis_verdict ─────────────────────────────────

class TestParseSynthesisVerdict:
    def test_buy_verdict(self):
        text = "Verdict: BUY\nConfidence: 75%\nStrategy: Delivery"
        verdict, conf, strat = _parse_synthesis_verdict(text)
        assert verdict == "BUY"
        assert conf == 75
        assert "Delivery" in strat

    def test_strong_sell(self):
        verdict, conf, _ = _parse_synthesis_verdict("Verdict: STRONG_SELL\nConfidence: 85%")
        assert verdict == "STRONG_SELL"
        assert conf == 85

    def test_hold_default(self):
        verdict, conf, _ = _parse_synthesis_verdict("No clear signal")
        assert verdict == "HOLD"
        assert conf == 50

    def test_confidence_without_percent(self):
        _, conf, _ = _parse_synthesis_verdict("Verdict: BUY\nConfidence: 60")
        assert conf == 60


# ── Lot sizes ────────────────────────────────────────────────

class TestLotSizes:
    def test_nifty_lot(self):
        assert LOT_SIZES["NIFTY"] == 75

    def test_banknifty_lot(self):
        assert LOT_SIZES["BANKNIFTY"] == 15

    def test_reliance_has_lot(self):
        assert "RELIANCE" in LOT_SIZES
        assert LOT_SIZES["RELIANCE"] > 0


# ── Data classes ─────────────────────────────────────────────

class TestDataClasses:
    def test_order_leg_creation(self):
        leg = OrderLeg(
            action="BUY", instrument="RELIANCE", exchange="NSE",
            product="CNC", order_type="MARKET", quantity=10,
        )
        assert leg.action == "BUY"
        assert leg.quantity == 10
        assert leg.price is None

    def test_exit_plan_creation(self):
        ep = ExitPlan(
            stop_loss=2400, stop_loss_pct=-4.0, stop_loss_type="ATR_BASED",
            target_1=2700, target_1_pct=8.0,
        )
        assert ep.stop_loss == 2400
        assert ep.target_2 is None

    def test_trade_plan_print_does_not_raise(self):
        plan = TradePlan(
            symbol="TEST", exchange="NSE",
            timestamp="2026-01-01T00:00:00",
            strategy_name="Test", direction="LONG",
            instrument_type="EQUITY", timeframe="SWING",
            capital_deployed=10000, capital_pct=5.0,
            max_risk=2000, risk_pct=1.0, reward_risk=2.0,
            entry_orders=[OrderLeg(
                action="BUY", instrument="TEST", exchange="NSE",
                product="CNC", order_type="MARKET", quantity=10,
            )],
            exit_plan=ExitPlan(
                stop_loss=95, stop_loss_pct=-5.0, stop_loss_type="FIXED",
                target_1=110, target_1_pct=10.0,
            ),
        )
        plan.print_plan()  # should not raise
