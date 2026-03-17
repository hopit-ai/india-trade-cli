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
        Tool-calling loop implemented via repeated CLI calls.
        Tools are described in the prompt; results injected as user messages.
        """
        tool_descriptions = self._build_tool_descriptions()
        history           = list(messages)

        for _ in range(MAX_TOOL_ROUNDS):
            full_prompt = self._render_prompt(history, tool_descriptions)
            raw_output  = self._call_cli(full_prompt)

            # Try to parse tool calls from model output
            tool_calls = self._parse_tool_calls(raw_output)

            if tool_calls:
                # Strip the tool_call JSON from the output text
                display_text = self._strip_tool_calls(raw_output)
                if display_text.strip():
                    console.print(display_text, highlight=False)

                # Build assistant turn
                history.append(_assistant_msg(raw_output))

                # Execute and inject results
                results_text = ""
                for tc in tool_calls:
                    _print_tool_call(tc["name"], tc["input"])
                    result = self.registry.execute(tc["name"], tc["input"])
                    results_text += (
                        f"\n<tool_result name=\"{tc['name']}\">\n"
                        f"{json.dumps(result, indent=2)}\n"
                        f"</tool_result>\n"
                    )
                history.append(_user_msg(results_text))

            else:
                # No tool calls → this is the final answer
                console.print(raw_output, highlight=False)
                return raw_output

        return "[Agent hit tool-round limit]"

    # ── Private ───────────────────────────────────────────────

    def _call_cli(self, prompt: str) -> str:
        """Invoke `claude -p <prompt>` and return output."""
        try:
            result = subprocess.run(
                [self._cli, "-p", prompt, "--output-format", "text"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                err = result.stderr.strip()
                return f"[Claude CLI error: {err}]"
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return "[Claude CLI timed out after 120 seconds]"
        except FileNotFoundError:
            return "[Claude CLI not found — install with: npm i -g @anthropic-ai/claude-code]"

    def _build_tool_descriptions(self) -> str:
        """Describe available tools to the model in the system prompt."""
        lines = ["You have access to the following tools. Call them by outputting JSON like:"]
        lines.append('{"tool_call": {"name": "tool_name", "arguments": {...}}}')
        lines.append("")
        for t in self.registry.anthropic_schema():
            lines.append(f"• {t['name']}: {t['description']}")
        return "\n".join(lines)

    def _render_prompt(self, history: list[dict], tool_descriptions: str) -> str:
        """Render conversation history into a single prompt string."""
        parts = [
            "SYSTEM:\n" + self.system_prompt,
            "\nAVAILABLE TOOLS:\n" + tool_descriptions,
            "\n--- CONVERSATION ---",
        ]
        for msg in history:
            role    = msg["role"].upper()
            content = msg["content"] if isinstance(msg["content"], str) else json.dumps(msg["content"])
            parts.append(f"\n{role}:\n{content}")
        parts.append("\nASSISTANT:")
        return "\n".join(parts)

    @staticmethod
    def _parse_tool_calls(text: str) -> list[dict]:
        """Extract tool_call JSON blocks from model output."""
        import re
        pattern = r'\{["\']tool_call["\']\s*:\s*\{.*?\}\s*\}'
        calls   = []
        for m in re.finditer(pattern, text, re.DOTALL):
            try:
                obj = json.loads(m.group())
                tc  = obj.get("tool_call", {})
                calls.append({"name": tc.get("name", ""), "input": tc.get("arguments", {})})
            except json.JSONDecodeError:
                pass
        return calls

    @staticmethod
    def _strip_tool_calls(text: str) -> str:
        """Remove tool_call JSON from display text."""
        import re
        return re.sub(r'\{["\']tool_call["\']\s*:\s*\{.*?\}\s*\}', "", text, flags=re.DOTALL).strip()


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
    """
    reg = registry or build_registry()

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
    return cls(chosen_model, reg, system)


def _has_anthropic_key() -> bool:
    """Check whether an Anthropic API key is available without prompting."""
    from config.credentials import _kr_get
    return bool(os.environ.get("ANTHROPIC_API_KEY") or _kr_get("ANTHROPIC_API_KEY"))


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
    """Infer provider from environment — whichever credentials are present."""
    env = os.environ
    if env.get("ANTHROPIC_API_KEY"):
        return PROVIDER_ANTHROPIC
    if env.get("OPENAI_API_KEY"):
        return PROVIDER_OPENAI
    if env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY"):
        return PROVIDER_GEMINI
    if env.get("GOOGLE_CLOUD_PROJECT"):
        return PROVIDER_GEMINI_SUB
    if env.get("OPENAI_SESSION_TOKEN"):
        return PROVIDER_OPENAI_SUB
    import shutil
    if shutil.which("claude") or shutil.which("claude-code"):
        return PROVIDER_CLAUDE_CLI
    return PROVIDER_ANTHROPIC   # will fail gracefully with clear error


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
