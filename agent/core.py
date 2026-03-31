"""
agent/core.py
─────────────
TradingAgent — the AI guidance brain of the platform.

Supports multiple LLM providers and access modes:

  ┌─────────────────────────┬──────────────────────────────────────────────────────┐
  │ Provider                │ Access Method                                        │
  ├─────────────────────────┼──────────────────────────────────────────────────────┤
  │ anthropic               │ ANTHROPIC_API_KEY (API key / Claude Max API access)  │
  │ openai                  │ OPENAI_API_KEY   (API key)                           │
  │ gemini                  │ GEMINI_API_KEY   (Google AI Studio key, free tier)   │
  │ claude_subscription     │ `claude` CLI tool (Claude Pro/Max browser sub)       │
  │ openai_subscription     │ OPENAI_SESSION_TOKEN (ChatGPT Plus, unofficial)      │
  │ gemini_subscription     │ Vertex AI + Application Default Credentials (GCP)    │
  └─────────────────────────┴──────────────────────────────────────────────────────┘

Notes on subscriptions vs API keys:

  ANTHROPIC (Claude):
    • Claude API key → use `anthropic` provider  (ANTHROPIC_API_KEY)
    • Claude Pro/Max subscription, no key → use `claude_subscription`
      Delegates to the `claude` CLI binary (Claude Code) which auths via browser.
      Install: npm install -g @anthropic-ai/claude-code  then `claude login`
    • Claude Max with API access → still use `anthropic` (Max plan includes API quota)

  OPENAI (GPT):
    • OpenAI API key → use `openai` provider  (OPENAI_API_KEY)
    • ChatGPT Plus/Team subscription → use `openai_subscription`
      Uses browser session token (unofficial, may break; for personal use only)
      Get token: chatgpt.com → DevTools → Application → Cookies → __Secure-next-auth.session-token
    • Note: ChatGPT subscription does NOT include API credits (billed separately)

  GOOGLE (Gemini):
    • Google AI Studio key → use `gemini` provider  (GEMINI_API_KEY)
      Free at aistudio.google.com — supports Gemini 2.5 Pro, Flash, etc.
    • Gemini Advanced (Google One) or Google Workspace → use `gemini_subscription`
      Uses Vertex AI with Application Default Credentials (gcloud auth login)
      Requires a GCP project: gcloud config set project <PROJECT_ID>
    • Note: Gemini Advanced UI subscription ≠ Vertex AI access automatically;
      Workspace/Enterprise Google customers get Vertex AI by default.

Provider selected via AI_PROVIDER env var or runtime argument.
Model selected via AI_MODEL env var or runtime argument.

The agent runs a tool-calling agentic loop:
  1. Send user message + history to LLM
  2. LLM returns tool calls → execute each via ToolRegistry
  3. Send tool results back to LLM
  4. Repeat until LLM returns final text (no more tool calls)
  5. Stream the final response to terminal
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Any

from rich.console import Console

from agent.prompts import build_system_prompt
from agent.tools import build_registry, ToolRegistry
from config.credentials import get_credential

console = Console()


# ── Constants ──────────────────────────────────────────────────

ANTHROPIC_DEFAULT_MODEL = "claude-opus-4-5"
OPENAI_DEFAULT_MODEL    = "gpt-4o"

MAX_TOOL_ROUNDS = 10   # agentic loop safety cap


# ── Provider names ─────────────────────────────────────────────

PROVIDER_ANTHROPIC    = "anthropic"
PROVIDER_OPENAI       = "openai"
PROVIDER_GEMINI       = "gemini"
PROVIDER_CLAUDE_CLI   = "claude_subscription"
PROVIDER_OPENAI_SUB   = "openai_subscription"
PROVIDER_GEMINI_SUB   = "gemini_subscription"

GEMINI_DEFAULT_MODEL  = "gemini-2.5-pro"

ALL_PROVIDERS = [
    PROVIDER_ANTHROPIC,
    PROVIDER_OPENAI,
    PROVIDER_GEMINI,
    PROVIDER_CLAUDE_CLI,
    PROVIDER_OPENAI_SUB,
    PROVIDER_GEMINI_SUB,
]


# ── Message helpers ────────────────────────────────────────────

def _user_msg(content: str) -> dict:
    return {"role": "user", "content": content}

def _assistant_msg(content: str) -> dict:
    return {"role": "assistant", "content": content}


# ── Abstract provider ──────────────────────────────────────────

class LLMProvider(ABC):
    """Common interface for all LLM providers."""

    def __init__(self, model: str, registry: ToolRegistry, system_prompt: str) -> None:
        self.model         = model
        self.registry      = registry
        self.system_prompt = system_prompt

    @abstractmethod
    def chat(self, messages: list[dict], stream: bool = True) -> str:
        """
        Send messages, run tool loop, return final text response.
        Streams text live to terminal when stream=True.
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name shown in the UI."""


# ── Anthropic provider (API key) ───────────────────────────────

class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude via official `anthropic` SDK.

    Access modes (both use same ANTHROPIC_API_KEY):
      - Personal API key from console.anthropic.com
      - Claude Max / Claude for Work (includes API access, same key)

    Set AI_PROVIDER=anthropic in .env
    """

    def __init__(self, model: str, registry: ToolRegistry, system_prompt: str) -> None:
        super().__init__(model, registry, system_prompt)
        try:
            import anthropic as _sdk
            self._sdk = _sdk
            # Use required=False so we never prompt interactively inside a command
            api_key = get_credential(
                "ANTHROPIC_API_KEY", "Anthropic API Key", secret=True, required=False
            )
            if not api_key:
                raise RuntimeError(
                    "Anthropic API key not set.\n"
                    "Run [bold]credentials setup[/bold] → AI Provider → choose your option\n"
                    "  or set AI_PROVIDER=claude_subscription to use your Claude subscription."
                )
            self._client = _sdk.Anthropic(api_key=api_key)
        except ImportError:
            raise RuntimeError("anthropic not installed. Run: pip install anthropic")

    @property
    def provider_name(self) -> str:
        return f"Anthropic / {self.model}"

    def chat(self, messages: list[dict], stream: bool = True) -> str:
        local  = list(messages)
        tools  = self.registry.anthropic_schema()
        final  = ""

        for _ in range(MAX_TOOL_ROUNDS):
            text, tool_calls = (
                self._stream_round(local, tools) if stream
                else self._call_round(local, tools)
            )

            if tool_calls:
                # Build assistant content block list
                content: list[dict] = []
                if text:
                    content.append({"type": "text", "text": text})
                for tc in tool_calls:
                    content.append({"type": "tool_use", "id": tc["id"],
                                    "name": tc["name"], "input": tc["input"]})
                local.append({"role": "assistant", "content": content})

                # Execute tools → tool_result blocks
                results: list[dict] = []
                for tc in tool_calls:
                    _print_tool_call(tc["name"], tc["input"])
                    result = self.registry.execute(tc["name"], tc["input"])
                    results.append({"type": "tool_result", "tool_use_id": tc["id"],
                                    "content": json.dumps(result)})
                local.append({"role": "user", "content": results})
            else:
                final = text
                break
        else:
            final = "[Agent hit tool-round limit]"

        return final

    # ── Private ───────────────────────────────────────────────

    def _call_round(self, messages, tools):
        r = self._client.messages.create(
            model=self.model, max_tokens=4096,
            system=self.system_prompt, tools=tools, messages=messages,
        )
        text, tcs = "", []
        for blk in r.content:
            if blk.type == "text":
                text = blk.text
            elif blk.type == "tool_use":
                tcs.append({"id": blk.id, "name": blk.name, "input": blk.input})
        return text, tcs

    def _stream_round(self, messages, tools):
        text = ""
        tcs: list[dict] = []
        cur_tool: dict  = {}
        cur_json        = ""
        in_tool         = False

        with self._client.messages.stream(
            model=self.model, max_tokens=4096,
            system=self.system_prompt, tools=tools, messages=messages,
        ) as s:
            for ev in s:
                et = ev.type
                if et == "content_block_start":
                    blk = ev.content_block
                    if blk.type == "tool_use":
                        in_tool  = True
                        cur_tool = {"id": blk.id, "name": blk.name}
                        cur_json = ""
                    else:
                        in_tool = False

                elif et == "content_block_delta":
                    d = ev.delta
                    if hasattr(d, "text") and not in_tool:
                        text += d.text
                        console.print(d.text, end="", markup=False, highlight=False)
                    elif hasattr(d, "partial_json"):
                        cur_json += d.partial_json

                elif et == "content_block_stop" and in_tool and cur_tool:
                    try:
                        cur_tool["input"] = json.loads(cur_json) if cur_json else {}
                    except json.JSONDecodeError:
                        cur_tool["input"] = {}
                    tcs.append(cur_tool)
                    cur_tool = {}
                    cur_json = ""
                    in_tool  = False

        if text:
            console.print()
        return text, tcs


# ── OpenAI provider (API key) ──────────────────────────────────

class OpenAIProvider(LLMProvider):
    """
    OpenAI GPT via official `openai` SDK.

    Access modes:
      - Personal API key (OPENAI_API_KEY) — paid per token
      - OpenAI Plus / Team / Enterprise users still need a separate API key;
        the ChatGPT Plus subscription does not include API credits.
        → For subscription-only users, see OpenAISubscriptionProvider below.

    Set AI_PROVIDER=openai in .env
    """

    def __init__(self, model: str, registry: ToolRegistry, system_prompt: str) -> None:
        super().__init__(model, registry, system_prompt)
        try:
            import openai as _sdk
            self._sdk    = _sdk
            self._client = _sdk.OpenAI(
                api_key=get_credential("OPENAI_API_KEY", "OpenAI API Key", secret=True)
            )
        except ImportError:
            raise RuntimeError("openai not installed. Run: pip install openai")

    @property
    def provider_name(self) -> str:
        return f"OpenAI / {self.model}"

    def chat(self, messages: list[dict], stream: bool = True) -> str:
        # OpenAI takes system message inline
        oai = [{"role": "system", "content": self.system_prompt}] + list(messages)
        tools = self.registry.openai_schema()
        final = ""

        for _ in range(MAX_TOOL_ROUNDS):
            text, tcs = (
                self._stream_round(oai, tools) if stream
                else self._call_round(oai, tools)
            )

            if tcs:
                oai.append({
                    "role": "assistant",
                    "content": text or None,
                    "tool_calls": [
                        {"id": tc["id"], "type": "function",
                         "function": {"name": tc["name"], "arguments": json.dumps(tc["input"])}}
                        for tc in tcs
                    ],
                })
                for tc in tcs:
                    _print_tool_call(tc["name"], tc["input"])
                    result = self.registry.execute(tc["name"], tc["input"])
                    oai.append({"role": "tool", "tool_call_id": tc["id"],
                                "content": json.dumps(result)})
            else:
                final = text
                break
        else:
            final = "[Agent hit tool-round limit]"

        return final

    # ── Private ───────────────────────────────────────────────

    def _call_round(self, messages, tools):
        r   = self._client.chat.completions.create(model=self.model, messages=messages, tools=tools)
        msg = r.choices[0].message
        tcs = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tcs.append({"id": tc.id, "name": tc.function.name, "input": args})
        return msg.content or "", tcs

    def _stream_round(self, messages, tools):
        text     = ""
        tc_acc: dict[int, dict] = {}

        with self._client.chat.completions.stream(
            model=self.model, messages=messages, tools=tools
        ) as s:
            for chunk in s:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    text += delta.content
                    console.print(delta.content, end="", markup=False, highlight=False)
                if delta.tool_calls:
                    for d in delta.tool_calls:
                        idx = d.index
                        if idx not in tc_acc:
                            tc_acc[idx] = {"id": "", "name": "", "args": ""}
                        if d.id:
                            tc_acc[idx]["id"] += d.id
                        if d.function:
                            if d.function.name:
                                tc_acc[idx]["name"] += d.function.name
                            if d.function.arguments:
                                tc_acc[idx]["args"] += d.function.arguments

        if text:
            console.print()

        tcs = []
        for idx in sorted(tc_acc):
            tc = tc_acc[idx]
            try:
                args = json.loads(tc["args"]) if tc["args"] else {}
            except json.JSONDecodeError:
                args = {}
            tcs.append({"id": tc["id"], "name": tc["name"], "input": args})
        return text, tcs


# ── Claude CLI provider (subscription) ────────────────────────

class ClaudeCLIProvider(LLMProvider):
    """
    Uses the `claude` CLI tool (Claude Code) to interact with Claude.

    This lets users with a Claude Pro or Max **subscription** (no API key
    required) use the same AI brain as the trading platform.

    How it works:
      - The `claude` CLI authenticates via your browser session at claude.ai
      - We call `claude -p "<prompt>"` as a subprocess and capture output
      - Tool results are injected back as follow-up prompts (no native tool loop)

    Limitations vs API mode:
      - No true streaming (output printed after full response)
      - No native tool_use protocol — tools are injected as JSON in the prompt
      - Slower round-trips (subprocess overhead)
      - Requires `claude` CLI installed: https://claude.ai/download
        or: npm install -g @anthropic-ai/claude-code

    Set AI_PROVIDER=claude_subscription in .env
    """

    def __init__(self, model: str, registry: ToolRegistry, system_prompt: str) -> None:
        super().__init__(model, registry, system_prompt)
        self._cli = self._find_claude_cli()

    @property
    def provider_name(self) -> str:
        return "Claude Subscription (CLI)"

    @staticmethod
    def _find_claude_cli() -> str:
        import shutil
        for name in ("claude", "claude-code"):
            path = shutil.which(name)
            if path:
                return path
        raise RuntimeError(
            "Claude CLI not found. Install it with:\n"
            "  npm install -g @anthropic-ai/claude-code\n"
            "Then run `claude login` to authenticate."
        )

    def chat(self, messages: list[dict], stream: bool = True) -> str:
        """
        Two-phase approach to avoid multiple slow subprocess calls.

        Problem: each `claude -p` subprocess takes 30–90 s to start + respond.
        The old approach made one call per tool round (5–6 for morning-brief)
        → 3–9 minutes total, always timing out.

        New approach (2 CLI calls total, regardless of tool count):

          Phase 1 — Planner call
            Send a tiny prompt (user question + bare tool names, no descriptions,
            no system prompt). Claude returns a JSON array of tool calls to make.
            Fast: small context, no tool descriptions to read.

          Phase 2 — Execute tools locally (Python, instant)
            Run every requested tool via the ToolRegistry in this process.
            No subprocess overhead at all.

          Phase 3 — Synthesis call
            Send ONE CLI call with: system prompt + user question + all tool
            results. Claude writes the final narrative.

        If the planner fails to return valid JSON (network error, unexpected
        output, etc.) we fall back to a direct synthesis call without tool data.
        """
        last_user_msg = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user_msg = (
                    m["content"] if isinstance(m["content"], str)
                    else json.dumps(m["content"])
                )
                break

        # ── Phase 1: in-process tool matching (no subprocess) ─────
        # Instead of asking the Claude CLI which tools to call (which
        # triggers Claude Code's coding-agent behaviour and asks for
        # permission to run Python), we scan the prompt text for tool
        # names that exist in our registry.  This is instant and reliable.
        tool_plan = self._match_tools_in_text(last_user_msg)
        if tool_plan:
            console.print(f"[dim]  Matched {len(tool_plan)} tools: "
                           f"{[t[0] for t in tool_plan]}[/dim]")

        # ── Phase 2: execute matched tools locally (fast) ─────────
        # Suppress interactive credential prompts during batch tool execution.
        # Without this, tools like get_stock_news pause for a NewsAPI key input,
        # blocking the entire flow.
        os.environ["_CLI_BATCH_MODE"] = "1"
        collected: list[str] = []
        for name, args in tool_plan:
            _print_tool_call(name, args)
            try:
                result = self.registry.execute(name, args)
                collected.append(
                    f'<tool_result name="{name}">\n'
                    f"{json.dumps(result, indent=2)}\n"
                    f"</tool_result>"
                )
                pass  # tool executed OK
            except Exception as exc:
                console.print(f"[dim]  ⚠ {name} skipped: {exc}[/dim]")
        os.environ.pop("_CLI_BATCH_MODE", None)

        if collected:
            console.print(f"[dim]  {len(collected)} tool results fetched[/dim]")

        # ── Fast path: simple data queries skip the LLM ──────────
        # If the only tools are data-only (quote, snapshot, vix, funds)
        # AND the user is asking a simple data question (not seeking advice),
        # format the results directly — no need for a 30s LLM call.
        data_only_tools = {
            "get_quote", "get_market_snapshot", "get_vix",
            "get_sector_snapshot", "get_funds", "get_holdings",
            "get_positions", "get_orders", "get_market_breadth",
            "get_fii_dii_data", "list_alerts",
        }
        # Detect if user wants reasoning (not just data)
        _reasoning_keywords = {
            "should", "buy", "sell", "hold", "recommend", "opinion",
            "think", "suggest", "advise", "compare", "better",
            "analysis", "analyze", "analyse", "why", "how",
            "strategy", "invest", "good time", "right time",
            "worth", "bullish", "bearish", "outlook", "view",
        }
        needs_reasoning = any(
            kw in last_user_msg.lower() for kw in _reasoning_keywords
        )
        matched_names = {t[0] for t in tool_plan}
        if (collected and matched_names and
                matched_names.issubset(data_only_tools) and
                not needs_reasoning):
            # Format data directly — no LLM needed
            response = _format_tool_results_directly(collected, last_user_msg)
            console.print(response, highlight=False)
            return response

        # ── Phase 3: synthesis — ONE CLI call to write the response ─
        # Build the full prompt with: system context + conversation history
        # + tool results + latest user message.
        if collected:
            _extra = (
                "\n\nIMPORTANT: Market data has already been collected for you below. "
                "Use it to answer — do NOT run any code."
            )
        else:
            _extra = (
                "\n\nYou have access to WebSearch and WebFetch tools. "
                "USE THEM to look up live market data, current prices, news, "
                "option chains, and fundamentals before answering. "
                "Always fetch real data — never guess prices. Do NOT run any code."
            )
        _context = self.system_prompt + _extra

        # Include conversation history so follow-up messages have context
        # (e.g. user says "1 year" after asking about RELIANCE vs SHAKTI)
        history_parts: list[str] = []
        for msg in messages[:-1]:  # all messages except the last (already in last_user_msg)
            role = msg["role"].upper()
            content = msg["content"] if isinstance(msg["content"], str) else json.dumps(msg["content"])
            # Truncate very long assistant messages to keep prompt manageable
            if role == "ASSISTANT" and len(content) > 1500:
                content = content[:1500] + "\n[...truncated...]"
            history_parts.append(f"{role}: {content}")

        parts = [_context]

        if history_parts:
            parts.append("\n--- CONVERSATION HISTORY ---\n" + "\n\n".join(history_parts))

        if collected:
            parts.append(
                "\n--- DATA COLLECTED FROM MARKET TOOLS ---\n"
                + "\n\n".join(collected)
            )

        parts.append(
            "\n--- CURRENT USER MESSAGE ---\n" + last_user_msg
        )

        if collected:
            parts.append(
                "\nWrite a concise, well-formatted response for a terminal. "
                "Use bullet points, cite the actual numbers from the data above."
            )

        synthesis_prompt = "\n".join(parts)

        console.print("[dim]  Generating response…[/dim]")
        response = self._call_cli(
            synthesis_prompt,
            timeout=300,
            label="Generating response",
        )
        console.print(response, highlight=False)
        return response

    # ── Private ───────────────────────────────────────────────

    def _call_cli(
        self,
        prompt:  str,
        timeout: int  = 300,
        label:   str  = "Claude is thinking",
    ) -> str:
        """
        Invoke `claude -p` non-interactively, sending the prompt via **stdin**.

        Args:
            prompt:  Full prompt text (sent via stdin to avoid OS arg-length limits).
                     The system prompt / trading context should already be embedded
                     in this text (not passed via CLI flags, which fail on long
                     strings with special characters).
            timeout: Seconds to wait before giving up (default 5 min).
            label:   Spinner label shown while waiting.

        Uses subprocess.Popen + a reader thread so we can show a live spinner
        while the process runs, and still collect stdout/stderr when it exits.

        --disallowedTools blocks all of Claude Code's built-in tools (Bash,
        Read, Edit, etc.) so it can ONLY respond with text.
        """
        import threading
        from rich.live    import Live
        from rich.spinner import Spinner

        # Whitelist: ONLY allow WebSearch + WebFetch (for market data lookups).
        # This implicitly blocks Bash, Read, Write, Edit, etc.
        # Each tool must be a separate --allowedTools flag (space-separated
        # in a single string is treated as one tool name by the CLI parser).
        cmd = [
            self._cli, "-p",
            "--output-format", "text",
            "--allowedTools", "WebSearch",
            "--allowedTools", "WebFetch",
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin  = subprocess.PIPE,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                text   = True,
            )
            # Write prompt via stdin then close so the CLI knows input is done
            proc.stdin.write(prompt)
            proc.stdin.close()

            out_buf: list[str] = []
            err_buf: list[str] = []

            def _read_out() -> None:
                for line in proc.stdout:
                    out_buf.append(line)

            def _read_err() -> None:
                for line in proc.stderr:
                    err_buf.append(line)

            t_out = threading.Thread(target=_read_out, daemon=True)
            t_err = threading.Thread(target=_read_err, daemon=True)
            t_out.start()
            t_err.start()

            with Live(
                Spinner("dots", text=f" {label}… (may take 1–2 min)"),
                console=console,
                transient=True,
                refresh_per_second=8,
            ):
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    t_out.join(timeout=2)
                    t_err.join(timeout=2)
                    mins = timeout // 60
                    return f"[Claude CLI timed out after {mins} min — try a simpler request]"

            t_out.join(timeout=5)
            t_err.join(timeout=5)

            stderr_text = "".join(err_buf).strip()

            if proc.returncode != 0:
                err = stderr_text or "".join(out_buf).strip() or "non-zero exit"
                return f"[Claude CLI error: {err}]"

            return "".join(out_buf).strip()

        except FileNotFoundError:
            return (
                "[Claude CLI not found — install with:\n"
                "  npm install -g @anthropic-ai/claude-code\n"
                "then run: claude login]"
            )

    # ── Keyword → tool mapping for freeform questions ───────────
    # When users type "ai how's reliance doing?", no tool names appear in
    # the text.  This map lets us infer which tools are relevant from
    # natural-language keywords.

    _KEYWORD_TOOL_MAP: dict[str, list[str]] = {
        # Market overview
        "market":       ["get_market_snapshot", "get_vix"],
        "nifty":        ["get_market_snapshot"],
        "banknifty":    ["get_market_snapshot"],
        "sensex":       ["get_market_snapshot"],
        "vix":          ["get_vix"],
        "sector":       ["get_sector_snapshot"],
        "sectors":      ["get_sector_snapshot"],
        # Stock analysis
        "price":        ["get_quote"],
        "quote":        ["get_quote"],
        "doing":        ["get_quote"],
        "trading at":   ["get_quote"],
        "ltp":          ["get_quote"],
        "news":         ["get_market_news"],
        "headlines":    ["get_market_news"],
        "technical":    ["technical_analyse"],
        "rsi":          ["technical_analyse"],
        "macd":         ["technical_analyse"],
        "chart":        ["technical_analyse"],
        "support":      ["technical_analyse"],
        "resistance":   ["technical_analyse"],
        "fundamental":  ["fundamental_analyse"],
        "pe ratio":     ["fundamental_analyse"],
        "roe":          ["fundamental_analyse"],
        "financials":   ["fundamental_analyse"],
        "balance sheet": ["fundamental_analyse"],
        "analyze":      ["get_quote", "technical_analyse", "fundamental_analyse"],
        "analyse":      ["get_quote", "technical_analyse", "fundamental_analyse"],
        "analysis":     ["get_quote", "technical_analyse", "fundamental_analyse"],
        # Advisory — needs analysis tools for proper reasoning
        "should":       ["get_quote", "technical_analyse", "fundamental_analyse"],
        "buy":          ["get_quote", "technical_analyse", "fundamental_analyse"],
        "sell":         ["get_quote", "technical_analyse"],
        "invest":       ["get_quote", "technical_analyse", "fundamental_analyse"],
        "recommend":    ["get_quote", "technical_analyse", "fundamental_analyse"],
        "outlook":      ["get_quote", "technical_analyse", "get_market_snapshot"],
        "compare":      ["get_quote", "technical_analyse", "fundamental_analyse"],
        "good time":    ["get_quote", "technical_analyse", "get_market_snapshot"],
        # Options
        "option":       ["get_options_chain"],
        "options":      ["get_options_chain"],
        "chain":        ["get_options_chain"],
        "pcr":          ["get_pcr"],
        "put call":     ["get_pcr"],
        "max pain":     ["get_max_pain"],
        "greeks":       ["compute_greeks"],
        "iv rank":      ["get_iv_rank"],
        "straddle":     ["get_options_chain"],
        "strangle":     ["get_options_chain"],
        "iron condor":  ["get_options_chain"],
        # Portfolio
        "holdings":     ["get_holdings"],
        "portfolio":    ["get_holdings", "get_positions"],
        "positions":    ["get_positions"],
        "orders":       ["get_orders"],
        "funds":        ["get_funds"],
        "balance":      ["get_funds"],
        # Flows & breadth
        "fii":          ["get_fii_dii_data"],
        "dii":          ["get_fii_dii_data"],
        "breadth":      ["get_market_breadth"],
        "advance":      ["get_market_breadth"],
        "decline":      ["get_market_breadth"],
        # Events
        "expiry":       ["get_upcoming_events"],
        "earnings":     ["get_upcoming_events"],
        "events":       ["get_upcoming_events"],
        "rbi":          ["get_upcoming_events"],
        # Alerts
        "alert":        ["set_price_alert", "set_technical_alert"],
        "notify":       ["set_price_alert"],
        "alerts":       ["list_alerts"],
        # Morning brief (catch "brief" / "morning" without full command)
        "brief":        ["get_market_snapshot", "get_market_news",
                         "get_fii_dii_data", "get_market_breadth",
                         "get_upcoming_events"],
        "morning":      ["get_market_snapshot", "get_market_news",
                         "get_fii_dii_data", "get_market_breadth",
                         "get_upcoming_events"],
    }

    # Common stock name → NSE symbol (case-insensitive lookup)
    _STOCK_NAMES: dict[str, str] = {
        "reliance": "RELIANCE", "hdfc": "HDFCBANK", "hdfc bank": "HDFCBANK",
        "infosys": "INFY", "infy": "INFY", "tcs": "TCS", "wipro": "WIPRO",
        "icici": "ICICIBANK", "icici bank": "ICICIBANK",
        "sbi": "SBIN", "state bank": "SBIN",
        "bharti": "BHARTIARTL", "airtel": "BHARTIARTL",
        "kotak": "KOTAKBANK", "kotak bank": "KOTAKBANK",
        "axis": "AXISBANK", "axis bank": "AXISBANK",
        "maruti": "MARUTI", "tata motors": "TATAMOTORS", "tatamotors": "TATAMOTORS",
        "tata steel": "TATASTEEL", "tatasteel": "TATASTEEL",
        "tata power": "TATAPOWER", "adani": "ADANIENT",
        "adani ports": "ADANIPORTS", "adani ent": "ADANIENT",
        "lt": "LT", "larsen": "LT", "bajaj finance": "BAJFINANCE",
        "bajaj finserv": "BAJFINSV", "bajaj": "BAJFINANCE",
        "hul": "HINDUNILVR", "hindustan unilever": "HINDUNILVR",
        "itc": "ITC", "ongc": "ONGC", "coal india": "COALINDIA",
        "power grid": "POWERGRID", "ntpc": "NTPC", "sun pharma": "SUNPHARMA",
        "dr reddy": "DRREDDY", "divi": "DIVISLAB", "cipla": "CIPLA",
        "titan": "TITAN", "asian paints": "ASIANPAINT",
        "ultra cement": "ULTRACEMCO", "ultratech": "ULTRACEMCO",
        "m&m": "M&M", "mahindra": "M&M",
        "indusind": "INDUSINDBK", "bandhan": "BANDHANBNK",
        "zomato": "ZOMATO", "paytm": "PAYTM",
        "shakti": "SHAKTIPUMP", "shakti pumps": "SHAKTIPUMP",
        "muthoot": "MUTHOOTFIN", "muthoot finance": "MUTHOOTFIN",
        "oil india": "OIL",
    }

    def _match_tools_in_text(self, text: str) -> list[tuple[str, dict]]:
        """
        Determine which tools to call, using two strategies:

          1. Exact tool-name matching — for structured command prompts
             (MORNING_BRIEF_PROMPT, ANALYZE_STOCK_PROMPT) which list tool
             names explicitly.  Instant and reliable.

          2. Keyword inference — for freeform ``ai`` questions like
             "how's Reliance doing?" where no tool names appear.
             Maps natural-language keywords to relevant tools.

        Also extracts stock symbols from natural language (both uppercase
        "RELIANCE" and lowercase "reliance" / "hdfc bank").

        Returns list of (tool_name, arguments_dict) tuples.
        """
        import re
        known = {t["name"] for t in self.registry.anthropic_schema()}
        seen:    set[str]                = set()
        matched: list[tuple[str, dict]]  = []

        # ── Extract stock symbol ──────────────────────────────────
        symbol = self._extract_symbol(text)

        # ── Strategy 1: exact tool-name matching ──────────────────
        for name in known:
            if name in text and name not in seen:
                seen.add(name)

        # ── Strategy 2: keyword inference (freeform questions) ────
        text_lower = text.lower()
        for keyword, tools in self._KEYWORD_TOOL_MAP.items():
            if keyword in text_lower:
                for t in tools:
                    if t in known and t not in seen:
                        seen.add(t)

        # ── Auto-add stock-specific tools if symbol detected ──────
        if symbol and not seen.intersection({
            "get_quote", "technical_analyse", "get_stock_news",
            "fundamental_analyse",
        }):
            for default in ("get_quote",):
                if default in known:
                    seen.add(default)

        # ── Build (name, args) tuples ─────────────────────────────
        for name in seen:
            args: dict = {}
            schema = self.registry._tools[name].get("parameters", {})
            props  = schema.get("properties", {})
            if symbol:
                if "symbol" in props:
                    args["symbol"] = symbol
                elif "instruments" in props:
                    args["instruments"] = [f"NSE:{symbol}"]
                elif "symbols" in props:
                    args["symbols"] = [f"NSE:{symbol}"]
                elif "underlying" in props:
                    args["underlying"] = symbol
            matched.append((name, args))

        return matched

    def _extract_symbol(self, text: str) -> str:
        """
        Extract a stock symbol from user text.

        Handles:
          - Explicit symbols: "NSE:RELIANCE", "RELIANCE"
          - Natural names:    "reliance", "hdfc bank", "tata motors"
        """
        import re

        # 1. Try the stock-name dictionary first (longest match wins)
        text_lower = text.lower()
        best_name = ""
        best_sym  = ""
        for name, sym in self._STOCK_NAMES.items():
            if name in text_lower and len(name) > len(best_name):
                best_name = name
                best_sym  = sym
        if best_sym:
            return best_sym

        # 2. Fall back to uppercase regex: "NSE:RELIANCE" or standalone "RELIANCE"
        _noise = {
            "NIFTY", "BANKNIFTY", "VIX", "SYSTEM", "USER", "ASSISTANT",
            "JSON", "NSE", "BSE", "IST", "RSI", "MACD", "PE", "CE", "PUT",
            "CALL", "BUY", "SELL", "STT", "GST", "RBI", "FII", "DII",
            "NOT", "USE", "THE", "FOR", "AND", "NFO", "CNC", "MIS",
            "NRML", "SL", "AM", "PM", "EMA", "SMA", "ATR",
            # Debate/analysis terms (not stock symbols)
            "BULLISH", "BEARISH", "NEUTRAL", "DEBATE", "BULL", "BEAR",
            "VERDICT", "HOLD", "STRONG", "ANALYSIS", "TRADE", "RISK",
            "FUND", "MANAGER", "RESEARCHER", "FACILITATOR", "ROUND",
            "TARGET", "ENTRY", "EXIT", "STOP", "LOSS", "PROFIT",
            "MARGIN", "CAPITAL", "PORTFOLIO", "SCORE", "CONFIDENCE",
            "HIGH", "LOW", "OPEN", "CLOSE", "ABOVE", "BELOW",
            "MARKET", "INDEX", "SECTOR", "IMPORTANT", "DATA",
            "OPTIONS", "OPTION", "FUTURES", "SPREAD", "STRADDLE",
            "STRANGLE", "CONDOR", "BUTTERFLY", "PREMIUM", "STRIKE",
            "EXPIRY", "SENTIMENT", "TECHNICAL", "FUNDAMENTAL",
            "EARNINGS", "RESULTS", "GROWTH", "REVENUE", "VOLUME",
            "SUPPORT", "RESISTANCE", "TREND", "SIGNAL", "PATTERN",
        }
        m = re.search(
            r'(?:NSE:|BSE:)?([A-Z][A-Z0-9&]{1,19})'
            r'(?=[\s"\'.,;:\]\)—?!]|$)',
            text,
        )
        if m and m.group(1) not in _noise:
            return m.group(1)

        return ""


# ── OpenAI subscription provider (session token) ───────────────

class OpenAISubscriptionProvider(LLMProvider):
    """
    Uses an OpenAI session token (from your logged-in ChatGPT Plus/Team browser)
    to make requests to the ChatGPT backend.

    This is for users who have a ChatGPT Plus/Team **subscription** but do NOT
    have a separate OpenAI API key.

    How to get OPENAI_SESSION_TOKEN:
      1. Log into chatgpt.com in Chrome/Firefox
      2. Open DevTools → Application → Cookies
      3. Copy the value of `__Secure-next-auth.session-token`
      4. Set it in .env: OPENAI_SESSION_TOKEN=<value>

    ⚠️  WARNING:
      - This uses an unofficial/undocumented ChatGPT API endpoint
      - May break if OpenAI updates their web app
      - Against OpenAI's Terms of Service for automated use
      - For development / personal use only
      - Token expires; you'll need to refresh it periodically

    For production or reliable use, get an API key at platform.openai.com.

    Set AI_PROVIDER=openai_subscription in .env
    """

    BACKEND_URL = "https://chat.openai.com/backend-api/conversation"
    AUTH_URL    = "https://chat.openai.com/api/auth/session"

    def __init__(self, model: str, registry: ToolRegistry, system_prompt: str) -> None:
        super().__init__(model, registry, system_prompt)
        try:
            import httpx
            self._httpx = httpx
        except ImportError:
            raise RuntimeError("httpx not installed. Run: pip install httpx")

        self._session_token = get_credential(
            "OPENAI_SESSION_TOKEN", "OpenAI Session Token (ChatGPT Plus)", secret=True, required=False
        )
        if not self._session_token:
            raise RuntimeError(
                "OPENAI_SESSION_TOKEN not set.\n"
                "See .env.example for instructions on getting your session token.\n"
                "Or use AI_PROVIDER=openai with an API key instead."
            )
        self._access_token = self._get_access_token()

    @property
    def provider_name(self) -> str:
        return "OpenAI ChatGPT Subscription (session)"

    def _get_access_token(self) -> str:
        """Exchange session cookie for a bearer access token."""
        cookies = {"__Secure-next-auth.session-token": self._session_token}
        try:
            r = self._httpx.get(
                self.AUTH_URL,
                cookies=cookies,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
                follow_redirects=True,
            )
            r.raise_for_status()
            return r.json().get("accessToken", "")
        except Exception as e:
            raise RuntimeError(
                f"Failed to authenticate with ChatGPT session token: {e}\n"
                "Token may be expired — log in to chatgpt.com and get a fresh token."
            )

    def chat(self, messages: list[dict], stream: bool = True) -> str:
        """
        Best-effort ChatGPT backend call.
        Does NOT support native tool calling (no tool loop).
        Tools are described in the system prompt as JSON instructions.
        """
        # Build payload — simplified, no tool calling
        user_text = "\n\n".join(
            msg["content"] for msg in messages
            if isinstance(msg.get("content"), str)
        )

        combined = (
            f"{self.system_prompt}\n\n"
            f"User request: {user_text}\n\n"
            f"(Note: You are running in subscription mode without tool access. "
            f"Provide analysis based on your knowledge and ask the user for specific data if needed.)"
        )

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type":  "application/json",
            "User-Agent":    "Mozilla/5.0",
        }

        payload = {
            "action":          "next",
            "messages": [{
                "id":      "msg-001",
                "role":    "user",
                "content": {"content_type": "text", "parts": [combined]},
            }],
            "model":           self.model or "gpt-4o",
            "parent_message_id": "00000000-0000-0000-0000-000000000000",
        }

        console.print(
            "[yellow]⚠  Running in subscription mode — tool calls unavailable.[/yellow]"
        )

        try:
            r = self._httpx.post(
                self.BACKEND_URL,
                json=payload,
                headers=headers,
                timeout=90,
            )
            r.raise_for_status()

            # Extract the last text message from SSE stream
            text = ""
            for line in r.text.splitlines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        chunk = json.loads(line[6:])
                        parts = (chunk.get("message", {})
                                      .get("content", {})
                                      .get("parts", []))
                        if parts:
                            text = parts[-1]
                    except json.JSONDecodeError:
                        pass

            console.print(text, highlight=False)
            return text

        except Exception as e:
            msg = f"[ChatGPT subscription request failed: {e}]"
            console.print(f"[red]{msg}[/red]")
            return msg


# ── Gemini provider (API key) ──────────────────────────────────

class GeminiProvider(LLMProvider):
    """
    Google Gemini via `google-generativeai` SDK.

    Access modes:
      - Free / paid API key from Google AI Studio (aistudio.google.com)
      - GEMINI_API_KEY in .env

    Models: gemini-2.5-pro, gemini-2.0-flash, gemini-1.5-pro, etc.

    Tool calling: uses Gemini's native function calling protocol.

    Set AI_PROVIDER=gemini in .env
    """

    def __init__(self, model: str, registry: ToolRegistry, system_prompt: str) -> None:
        super().__init__(model, registry, system_prompt)
        try:
            import google.generativeai as genai
            self._genai = genai
            api_key = (
                get_credential("GEMINI_API_KEY", "Google Gemini API Key", secret=True, required=False)
                or os.environ.get("GOOGLE_API_KEY", "")
            )
            if not api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY not set. Get a free key at aistudio.google.com"
                )
            genai.configure(api_key=api_key)
            self._tools_schema = self._build_gemini_tools()
            self._model_obj = genai.GenerativeModel(
                model_name     = self.model or GEMINI_DEFAULT_MODEL,
                system_instruction = self.system_prompt,
                tools          = self._tools_schema or None,
            )
        except ImportError:
            raise RuntimeError(
                "google-generativeai not installed.\n"
                "Run: pip install google-generativeai"
            )

    @property
    def provider_name(self) -> str:
        return f"Google Gemini / {self.model or GEMINI_DEFAULT_MODEL}"

    def _build_gemini_tools(self) -> list:
        """Convert ToolRegistry to Gemini FunctionDeclaration format."""
        try:
            from google.generativeai.types import FunctionDeclaration, Tool
            declarations = []
            for t in self.registry.anthropic_schema():
                params = t.get("input_schema", {})
                declarations.append(FunctionDeclaration(
                    name        = t["name"],
                    description = t["description"],
                    parameters  = params,
                ))
            return [Tool(function_declarations=declarations)]
        except Exception:
            return []

    def chat(self, messages: list[dict], stream: bool = True) -> str:
        """Agentic loop using Gemini's function calling."""
        # Convert history to Gemini format
        gemini_history = self._to_gemini_history(messages[:-1]) if len(messages) > 1 else []
        last_msg       = messages[-1]["content"] if messages else ""

        chat_session = self._model_obj.start_chat(history=gemini_history)
        final_text   = ""

        # Send the last user message
        current_input = last_msg

        for _ in range(MAX_TOOL_ROUNDS):
            try:
                response = chat_session.send_message(current_input)
            except Exception as e:
                return f"[Gemini error: {e}]"

            # Check for function calls
            tool_calls = []
            text_parts = []

            for part in response.parts:
                if hasattr(part, "function_call") and part.function_call.name:
                    fc = part.function_call
                    tool_calls.append({
                        "name":  fc.name,
                        "input": dict(fc.args),
                    })
                elif hasattr(part, "text") and part.text:
                    text_parts.append(part.text)

            text = "".join(text_parts)

            if tool_calls:
                if text:
                    console.print(text, highlight=False)

                # Execute tools, build function response parts
                from google.generativeai.types import content_types
                fn_responses = []
                for tc in tool_calls:
                    _print_tool_call(tc["name"], tc["input"])
                    result = self.registry.execute(tc["name"], tc["input"])
                    fn_responses.append(
                        self._genai.protos.Part(
                            function_response=self._genai.protos.FunctionResponse(
                                name     = tc["name"],
                                response = {"result": result},
                            )
                        )
                    )

                # Next iteration feeds function responses
                current_input = fn_responses

            else:
                # Final text response
                final_text = text
                if stream:
                    console.print(final_text, highlight=False)
                break
        else:
            final_text = "[Agent hit tool-round limit]"

        return final_text

    @staticmethod
    def _to_gemini_history(messages: list[dict]) -> list:
        """Convert our message format to Gemini history format."""
        history = []
        for msg in messages:
            role    = "user" if msg["role"] == "user" else "model"
            content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
            history.append({"role": role, "parts": [content]})
        return history


# ── Gemini Vertex AI provider (subscription / GCP) ────────────

class GeminiVertexProvider(LLMProvider):
    """
    Google Gemini via Vertex AI — for Google Workspace / GCP customers.

    Access modes:
      - Google Workspace Business/Enterprise (includes Gemini Advanced + Vertex AI)
      - GCP project with Vertex AI API enabled
      - Authentication: Application Default Credentials (ADC)
        → Run: gcloud auth application-default login
        → Set: GOOGLE_CLOUD_PROJECT in .env

    This is the enterprise/subscription path for Gemini — no API key needed,
    billing goes through your GCP project.

    Install extras: pip install google-cloud-aiplatform

    Set AI_PROVIDER=gemini_subscription in .env
    """

    def __init__(self, model: str, registry: ToolRegistry, system_prompt: str) -> None:
        super().__init__(model, registry, system_prompt)
        self._project  = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        self._location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        try:
            import vertexai
            from vertexai.generative_models import (
                GenerativeModel, FunctionDeclaration, Tool
            )
            self._GenerativeModel    = GenerativeModel
            self._FunctionDeclaration = FunctionDeclaration
            self._Tool               = Tool

            if not self._project:
                raise RuntimeError(
                    "GOOGLE_CLOUD_PROJECT not set.\n"
                    "Run: gcloud config set project <PROJECT_ID>\n"
                    "and add GOOGLE_CLOUD_PROJECT=<id> to .env"
                )

            vertexai.init(project=self._project, location=self._location)

            tools = self._build_vertex_tools()
            self._model_obj = GenerativeModel(
                model_name         = self.model or "gemini-2.5-pro",
                system_instruction = self.system_prompt,
                tools              = [tools] if tools else [],
            )

        except ImportError:
            raise RuntimeError(
                "google-cloud-aiplatform not installed.\n"
                "Run: pip install google-cloud-aiplatform"
            )

    @property
    def provider_name(self) -> str:
        return f"Google Vertex AI / {self.model or 'gemini-2.5-pro'} ({self._project})"

    def _build_vertex_tools(self):
        declarations = []
        for t in self.registry.anthropic_schema():
            declarations.append(self._FunctionDeclaration(
                name        = t["name"],
                description = t["description"],
                parameters  = t.get("input_schema", {}),
            ))
        return self._Tool(function_declarations=declarations) if declarations else None

    def chat(self, messages: list[dict], stream: bool = True) -> str:
        """Same agentic loop as GeminiProvider, using Vertex AI client."""
        gemini_history = GeminiProvider._to_gemini_history(messages[:-1]) if len(messages) > 1 else []
        last_msg       = messages[-1]["content"] if messages else ""

        chat_session   = self._model_obj.start_chat(history=gemini_history)
        current_input  = last_msg
        final_text     = ""

        for _ in range(MAX_TOOL_ROUNDS):
            try:
                response = chat_session.send_message(current_input)
            except Exception as e:
                return f"[Vertex AI error: {e}]"

            tool_calls, text_parts = [], []
            for part in response.candidates[0].content.parts:
                if part.function_call.name:
                    fc = part.function_call
                    tool_calls.append({"name": fc.name, "input": dict(fc.args)})
                elif part.text:
                    text_parts.append(part.text)

            text = "".join(text_parts)

            if tool_calls:
                if text:
                    console.print(text, highlight=False)

                from vertexai.generative_models import Part
                fn_responses = []
                for tc in tool_calls:
                    _print_tool_call(tc["name"], tc["input"])
                    result = self.registry.execute(tc["name"], tc["input"])
                    fn_responses.append(Part.from_function_response(
                        name     = tc["name"],
                        response = {"result": result},
                    ))
                current_input = fn_responses
            else:
                final_text = text
                if stream:
                    console.print(final_text, highlight=False)
                break
        else:
            final_text = "[Agent hit tool-round limit]"

        return final_text


# ── Provider factory ───────────────────────────────────────────

def get_provider(
    provider: str | None = None,
    model:    str | None = None,
    registry: ToolRegistry | None = None,
) -> LLMProvider:
    """
    Build the configured LLM provider.

    Provider resolution order:
      1. Explicit `provider` argument
      2. AI_PROVIDER env var / keychain
      3. Auto-detect from which keys/tokens are present in env
      4. If nothing found: interactive first-time setup menu

    If a saved provider fails (e.g. package not installed), the bad value is
    cleared from the keychain and the setup wizard runs automatically so the
    user can pick a working provider without ever seeing a raw traceback.
    """
    reg = registry or build_registry()

    # Remember whether the caller explicitly specified a provider so we know
    # whether to propagate construction failures or silently recover.
    explicit_provider = bool(provider)

    chosen = (
        provider
        or os.environ.get("AI_PROVIDER", "").lower()
        or _auto_detect_provider()
    )

    # If auto-detect fell back to anthropic but no key is available,
    # run the first-time setup instead of prompting for a key mid-command.
    if chosen == PROVIDER_ANTHROPIC and not _has_anthropic_key():
        chosen = _first_time_provider_setup()

    chosen_model = (
        model
        or os.environ.get("AI_MODEL", "")
        or _default_model(chosen)
    )

    system = build_system_prompt()

    if chosen == "none":
        raise RuntimeError(
            "No AI provider configured.\n"
            "Run [bold]credentials setup[/bold] → AI Provider to set one up."
        )

    dispatch = {
        PROVIDER_ANTHROPIC:  AnthropicProvider,
        PROVIDER_OPENAI:     OpenAIProvider,
        PROVIDER_GEMINI:     GeminiProvider,
        PROVIDER_CLAUDE_CLI: ClaudeCLIProvider,
        PROVIDER_OPENAI_SUB: OpenAISubscriptionProvider,
        PROVIDER_GEMINI_SUB: GeminiVertexProvider,
    }

    cls = dispatch.get(chosen, AnthropicProvider)

    try:
        return cls(chosen_model, reg, system)
    except RuntimeError as exc:
        # If the caller explicitly named a provider, propagate the error —
        # they asked for something specific and should see why it failed.
        if explicit_provider:
            raise

        # The provider came from a saved keychain value or auto-detect.
        # It's broken (missing package, missing key, etc.).  Clear it so we
        # don't hit the same error next time, then offer re-configuration.
        first_line = str(exc).splitlines()[0]
        console.print(
            f"\n[yellow]⚠  Saved AI provider [bold]{chosen!r}[/bold] is unavailable:[/yellow]"
            f" {first_line}\n"
            "[dim]Clearing saved provider and running one-time setup...[/dim]\n"
        )
        _clear_saved_provider()

        chosen = _first_time_provider_setup()
        if chosen == "none":
            raise RuntimeError(
                "No AI provider configured.\n"
                "Run [bold]credentials setup[/bold] → AI Provider to set one up."
            ) from exc

        cls2 = dispatch.get(chosen, AnthropicProvider)
        return cls2(_default_model(chosen), reg, system)


def _has_anthropic_key() -> bool:
    """Check whether an Anthropic API key is available without prompting."""
    from config.credentials import _kr_get
    return bool(os.environ.get("ANTHROPIC_API_KEY") or _kr_get("ANTHROPIC_API_KEY"))


def _clear_saved_provider() -> None:
    """
    Remove AI_PROVIDER from the OS keychain and the current process environment.

    Called when a saved provider fails to construct (e.g. required package not
    installed) so the next call to get_provider() doesn't keep hitting the same
    broken value.
    """
    try:
        from config.credentials import _kr_set
        _kr_set("AI_PROVIDER", "")   # blank it — falsy, so load_all() won't set os.environ
    except Exception:
        pass
    os.environ.pop("AI_PROVIDER", None)


def _first_time_provider_setup() -> str:
    """
    First-time AI provider setup — shown when no provider is configured.

    Saves the choice to the OS keychain so it's never asked again.
    Returns the chosen provider name string.
    """
    import shutil
    from rich.console import Console
    from rich.panel   import Panel
    from rich.prompt  import Prompt
    from config.credentials import _kr_set, _kr_get

    _c = Console()

    # Check what's available to inform the menu
    has_claude_cli = bool(shutil.which("claude") or shutil.which("claude-code"))

    subscription_hint = (
        "[bold green]✓ claude CLI detected[/bold green]"
        if has_claude_cli else
        "[dim](install: npm i -g @anthropic-ai/claude-code)[/dim]"
    )

    _c.print()
    _c.print(Panel(
        "\n"
        "  No AI provider configured yet. Pick one to continue:\n\n"
        f"  [cyan][1][/cyan] [bold]Claude subscription[/bold]  {subscription_hint}\n"
        "       Use your Claude Pro or Max plan — no API costs.\n\n"
        "  [cyan][2][/cyan] [bold]Claude API key[/bold]  [dim](console.anthropic.com)[/dim]\n"
        "       Pay-per-use. Claude Haiku is very cheap for trading analysis.\n\n"
        "  [cyan][3][/cyan] [bold]Gemini (Google)[/bold]  [dim][green]Free tier available — aistudio.google.com[/green][/dim]\n"
        "       Gemini 2.5 Pro is free with generous rate limits.\n\n"
        "  [cyan][4][/cyan] [bold]OpenAI (GPT-4o)[/bold]  [dim](platform.openai.com)[/dim]\n"
        "       Pay-per-use API key.\n\n"
        "  [cyan][5][/cyan] ChatGPT Plus subscription  "
        "[dim](session token, unofficial)[/dim]\n\n"
        "  [cyan][6][/cyan] Skip AI for now\n",
        title="[bold yellow]🤖  AI Provider Setup[/bold yellow]",
        border_style="yellow",
        padding=(0, 2),
    ))

    choice = Prompt.ask(
        "  [bold]Choose[/bold]",
        choices=["1", "2", "3", "4", "5", "6"],
        default="1" if has_claude_cli else "3",
    )

    def _save(key: str, value: str) -> None:
        _kr_set(key, value)
        os.environ[key] = value

    if choice == "1":
        if not has_claude_cli:
            _c.print(
                "\n  [yellow]claude CLI not found.[/yellow]  Install it first:\n"
                "    npm install -g @anthropic-ai/claude-code\n"
                "    claude login\n\n"
                "  Falling back to Gemini free tier for now.\n"
            )
            _save("AI_PROVIDER", PROVIDER_GEMINI)
            return PROVIDER_GEMINI
        _save("AI_PROVIDER", PROVIDER_CLAUDE_CLI)
        _c.print("  [green]✓ Using Claude subscription (claude CLI)[/green]\n")
        return PROVIDER_CLAUDE_CLI

    elif choice == "2":
        from config.credentials import get_credential
        api_key = get_credential("ANTHROPIC_API_KEY", "Anthropic API Key", secret=True, required=False)
        if api_key:
            _save("AI_PROVIDER", PROVIDER_ANTHROPIC)
            _c.print("  [green]✓ Using Anthropic API[/green]\n")
            return PROVIDER_ANTHROPIC
        _c.print("  [yellow]No key entered — skipping AI.[/yellow]\n")
        _save("AI_PROVIDER", "none")
        return "none"

    elif choice == "3":
        from config.credentials import get_credential
        api_key = get_credential(
            "GEMINI_API_KEY", "Google Gemini API Key", secret=True, required=False
        )
        if api_key:
            _save("AI_PROVIDER", PROVIDER_GEMINI)
            _c.print(
                "  [green]✓ Using Gemini.[/green]  "
                "[dim]Get a free key at aistudio.google.com[/dim]\n"
            )
            return PROVIDER_GEMINI
        _c.print("  [yellow]No key entered — skipping AI.[/yellow]\n")
        _save("AI_PROVIDER", "none")
        return "none"

    elif choice == "4":
        from config.credentials import get_credential
        api_key = get_credential("OPENAI_API_KEY", "OpenAI API Key", secret=True, required=False)
        if api_key:
            _save("AI_PROVIDER", PROVIDER_OPENAI)
            _c.print("  [green]✓ Using OpenAI GPT-4o[/green]\n")
            return PROVIDER_OPENAI
        _c.print("  [yellow]No key entered — skipping AI.[/yellow]\n")
        _save("AI_PROVIDER", "none")
        return "none"

    elif choice == "5":
        _c.print(
            "\n  [dim]Get token: chatgpt.com → F12 DevTools → Application → Cookies[/dim]\n"
            "  [dim]→ __Secure-next-auth.session-token[/dim]\n"
        )
        from config.credentials import get_credential
        token = get_credential(
            "OPENAI_SESSION_TOKEN", "ChatGPT Session Token", secret=True, required=False
        )
        if token:
            _save("AI_PROVIDER", PROVIDER_OPENAI_SUB)
            _c.print("  [green]✓ Using ChatGPT Plus subscription[/green]\n")
            return PROVIDER_OPENAI_SUB
        _c.print("  [yellow]No token entered — skipping AI.[/yellow]\n")
        _save("AI_PROVIDER", "none")
        return "none"

    else:  # skip
        _c.print("  [dim]AI skipped for this session.[/dim]\n")
        return "none"


def _auto_detect_provider() -> str:
    """
    Infer provider from environment — whichever credentials are present.

    Priority order (most explicit intent first):
      1. Explicit API keys — user clearly set these for this app
      2. claude CLI binary — present means Claude subscription is available
      3. Session tokens — slightly less reliable
      4. GOOGLE_CLOUD_PROJECT — too ambient (Claude Code, gcloud, etc. set this
         even without user intent to use Gemini), so it's last
    """
    env = os.environ

    # Explicit API keys first
    if env.get("ANTHROPIC_API_KEY"):
        return PROVIDER_ANTHROPIC
    if env.get("OPENAI_API_KEY"):
        return PROVIDER_OPENAI
    if env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY"):
        return PROVIDER_GEMINI

    # claude CLI binary — most reliable signal of subscription intent
    import shutil
    if shutil.which("claude") or shutil.which("claude-code"):
        return PROVIDER_CLAUDE_CLI

    # Less-reliable ambient signals
    if env.get("OPENAI_SESSION_TOKEN"):
        return PROVIDER_OPENAI_SUB

    # GOOGLE_CLOUD_PROJECT is set by many tools (gcloud, Claude Code workspace,
    # GCP VMs, etc.) — only use it as fallback, not auto-trigger
    if env.get("GOOGLE_CLOUD_PROJECT") and env.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return PROVIDER_GEMINI_SUB

    return PROVIDER_ANTHROPIC   # triggers first-time setup via _first_time_provider_setup


def _default_model(provider: str) -> str:
    if provider == PROVIDER_OPENAI:
        return OPENAI_DEFAULT_MODEL
    if provider in (PROVIDER_GEMINI, PROVIDER_GEMINI_SUB):
        return GEMINI_DEFAULT_MODEL
    return ANTHROPIC_DEFAULT_MODEL


# ── Trading Agent ──────────────────────────────────────────────

class TradingAgent:
    """
    Stateful trading agent: manages conversation history, routes messages
    through the configured LLM provider, and handles tool execution.

    Supports hot-switching providers mid-session (history preserved).

    Usage:
        agent = TradingAgent()
        agent.chat("Analyse RELIANCE for me")
        agent.chat("What's the options chain saying?")
        agent.switch_provider("openai")
        agent.chat("Give me a second opinion")
    """

    def __init__(
        self,
        provider:  str | None = None,
        model:     str | None = None,
        stream:    bool       = True,
    ) -> None:
        self._registry = build_registry()
        self._stream   = stream
        self._history: list[dict] = []

        self._provider = get_provider(
            provider=provider, model=model, registry=self._registry
        )

        console.print(
            f"\n[dim]🤖  AI: {self._provider.provider_name}[/dim]",
            highlight=False,
        )

    # ── Public API ────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        """
        Send a message, run the agentic loop, return the response.
        Response is also printed live to the terminal.
        """
        self._history.append(_user_msg(user_message))

        console.print()
        console.rule("[bold cyan]Agent[/bold cyan]", style="cyan dim")

        response = self._provider.chat(
            messages=self._history,
            stream=self._stream,
        )

        self._history.append(_assistant_msg(response))

        console.rule(style="cyan dim")
        console.print()

        return response

    def run_command(self, command: str, **template_vars) -> str:
        """
        Run a structured command prompt (morning_brief, analyze, strategy).
        One-shot — does NOT add to conversation history.
        """
        from agent.prompts import MORNING_BRIEF_PROMPT, ANALYZE_STOCK_PROMPT, STRATEGY_PROMPT

        templates = {
            "morning_brief": MORNING_BRIEF_PROMPT,
            "analyze":       ANALYZE_STOCK_PROMPT,
            "strategy":      STRATEGY_PROMPT,
        }

        tmpl   = templates.get(command, command)
        prompt = tmpl.format(**template_vars) if template_vars else tmpl

        console.print()
        console.rule(
            f"[bold cyan]{command.replace('_', ' ').title()}[/bold cyan]",
            style="cyan dim",
        )

        response = self._provider.chat(
            messages=[_user_msg(prompt)],
            stream=self._stream,
        )

        console.rule(style="cyan dim")
        console.print()

        return response

    def run_multi_agent_analysis(self, symbol: str, exchange: str = "NSE") -> str:
        """
        Run multi-agent analysis pipeline: 5 analysts + bull/bear debate + synthesis.

        Falls back to single-agent analysis if multi-agent fails.
        """
        try:
            from agent.multi_agent import MultiAgentAnalyzer

            analyzer = MultiAgentAnalyzer(
                registry=self._registry,
                llm_provider=self._provider,
                parallel=True,
                verbose=True,
            )
            result = analyzer.analyze(symbol, exchange)
            self._last_trade_plans = getattr(analyzer, 'last_trade_plans', {})
            return result
        except Exception as exc:
            console.print(
                f"[yellow]Multi-agent pipeline failed: {exc}[/yellow]\n"
                "[dim]Falling back to single-agent analysis...[/dim]"
            )
            return self.run_command("analyze", symbol=symbol)

    def switch_provider(self, provider: str, model: str | None = None) -> None:
        """
        Hot-switch LLM provider mid-session.
        Conversation history is preserved; new provider picks up context.
        """
        self._provider = get_provider(
            provider=provider, model=model, registry=self._registry
        )
        console.print(
            f"[dim]Switched provider → {self._provider.provider_name}[/dim]"
        )

    def clear_history(self) -> None:
        """Start a fresh conversation (clear history)."""
        self._history = []
        console.print("[dim]Conversation history cleared.[/dim]")

    def list_providers(self) -> None:
        """Print available providers and how to configure them."""
        console.print("\n[bold]Available AI providers:[/bold]")
        rows = [
            ("anthropic",           "ANTHROPIC_API_KEY",      "Claude API key or Claude Max"),
            ("openai",              "OPENAI_API_KEY",          "OpenAI API key"),
            ("gemini",              "GEMINI_API_KEY",          "Google AI Studio key (free tier available)"),
            ("claude_subscription", "claude CLI installed",    "Claude Pro/Max browser subscription"),
            ("openai_subscription", "OPENAI_SESSION_TOKEN",   "ChatGPT Plus/Team session (unofficial)"),
            ("gemini_subscription", "GOOGLE_CLOUD_PROJECT",   "Vertex AI / Google Workspace (GCP)"),
        ]
        for name, cred, note in rows:
            active = "✓" if name == _infer_current_name(self._provider) else " "
            console.print(f"  [{active}] [cyan]{name:<22}[/cyan]  {cred:<28}  [dim]{note}[/dim]")
        console.print(
            "\n  Switch with: [bold]provider <name>[/bold]  "
            "e.g. [cyan]provider claude_subscription[/cyan]\n"
            "  Or run [bold]credentials setup[/bold] → AI Provider to configure persistently.\n"
        )

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name


# ── Helpers ────────────────────────────────────────────────────

def _infer_current_name(provider: LLMProvider) -> str:
    if isinstance(provider, AnthropicProvider):
        return PROVIDER_ANTHROPIC
    if isinstance(provider, OpenAIProvider):
        return PROVIDER_OPENAI
    if isinstance(provider, GeminiProvider):
        return PROVIDER_GEMINI
    if isinstance(provider, GeminiVertexProvider):
        return PROVIDER_GEMINI_SUB
    if isinstance(provider, ClaudeCLIProvider):
        return PROVIDER_CLAUDE_CLI
    if isinstance(provider, OpenAISubscriptionProvider):
        return PROVIDER_OPENAI_SUB
    return ""


def _format_tool_results_directly(collected: list[str], user_msg: str) -> str:
    """
    Format tool results for direct display without LLM synthesis.
    Used for simple data queries like "what is RELIANCE trading at?"
    """
    import re

    output_parts = []
    for result_xml in collected:
        # Extract tool name and JSON data
        name_match = re.search(r'name="([^"]+)"', result_xml)
        tool_name = name_match.group(1) if name_match else "data"

        # Extract JSON between tags
        json_match = re.search(r'>\n(.*?)\n</tool_result>', result_xml, re.DOTALL)
        if not json_match:
            continue

        try:
            data = json.loads(json_match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue

        if tool_name == "get_quote" and isinstance(data, dict):
            for key, quote in data.items():
                if isinstance(quote, dict):
                    sym = quote.get("symbol", key)
                    ltp = quote.get("last_price", 0)
                    chg = quote.get("change", 0)
                    chg_pct = quote.get("change_pct", 0)
                    vol = quote.get("volume", 0)
                    emoji = "📈" if chg >= 0 else "📉"
                    output_parts.append(
                        f"{emoji} {sym}\n"
                        f"  LTP     : ₹{ltp:,.2f}\n"
                        f"  Change  : {chg:+.2f} ({chg_pct:+.2f}%)\n"
                        f"  Open    : ₹{quote.get('open', 0):,.2f}\n"
                        f"  High    : ₹{quote.get('high', 0):,.2f}\n"
                        f"  Low     : ₹{quote.get('low', 0):,.2f}\n"
                        f"  Volume  : {vol:,}"
                    )

        elif tool_name == "get_market_snapshot" and isinstance(data, dict):
            nifty = data.get("nifty", {})
            bnf = data.get("banknifty", {})
            vix = data.get("vix", {})
            posture = data.get("posture", "")
            output_parts.append(
                f"🇮🇳 Market Snapshot\n"
                f"  NIFTY     : {nifty.get('ltp', 0):,.0f} ({nifty.get('change_pct', 0):+.2f}%)\n"
                f"  BANKNIFTY : {bnf.get('ltp', 0):,.0f} ({bnf.get('change_pct', 0):+.2f}%)\n"
                f"  VIX       : {vix.get('ltp', 0):.1f}\n"
                f"  Posture   : {posture}\n"
                f"  {data.get('posture_reason', '')}"
            )

        elif tool_name == "get_vix" and isinstance(data, dict):
            vix_val = data.get("vix", 0)
            output_parts.append(f"⚡ India VIX: {vix_val:.1f}")

        else:
            # Generic: just pretty-print the JSON
            output_parts.append(f"[{tool_name}]\n{json.dumps(data, indent=2, default=str)[:500]}")

    return "\n\n".join(output_parts) if output_parts else "No data returned."


def _print_tool_call(name: str, args: dict) -> None:
    """Subtle tool-call indicator in the terminal."""
    args_str = ", ".join(
        f"{k}={json.dumps(v)}" for k, v in args.items()
    ) if args else ""
    console.print(
        f"  [dim cyan]⚙  {name}({args_str})[/dim cyan]",
        highlight=False,
    )


# ── Singleton access ───────────────────────────────────────────

_agent_instance: TradingAgent | None = None


def get_agent(
    provider:  str | None = None,
    model:     str | None = None,
    force_new: bool       = False,
) -> TradingAgent:
    """
    Return the shared TradingAgent singleton (creates it on first call).
    Pass force_new=True to create a fresh agent (e.g., after login).
    """
    global _agent_instance
    if _agent_instance is None or force_new:
        _agent_instance = TradingAgent(provider=provider, model=model)
    return _agent_instance
