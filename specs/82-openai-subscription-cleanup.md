# Spec: OpenAI Subscription Provider Cleanup (#82)

## Problem
`OpenAISubscriptionProvider` in `agent/core.py` uses the unofficial ChatGPT web API.
It does not support tool calling (which the platform requires for all analysis), and
violates OpenAI's Terms of Service. Users who select `openai_subscription` get a broken
experience with no clear guidance to a working alternative.

## Decision
Do **not** delete the class (could break existing .env files). Instead:
1. Mark it as **deprecated / non-functional** — add a banner warning in the docstring
2. Make `__init__` raise `RuntimeError` immediately with a clear, helpful message
3. Update the credentials wizard (`config/credentials.py`) — option 5 (ChatGPT subscription)
   should now show a deprecation notice and steer users to OpenRouter
4. Update `web/skills.py` — `/api/status` endpoint that lists `openai_subscription` as a
   deprecated provider

## Alternative guidance to include
```
The openai_subscription provider is no longer functional.

To use GPT-4o without paying per-token, try one of these options:
  • OpenRouter (free tier): set AI_PROVIDER=openai, OPENAI_BASE_URL=https://openrouter.ai/api/v1,
    OPENAI_MODEL=openai/gpt-4o — free tier available, full tool calling support
  • Groq (free, fast): set AI_PROVIDER=openai, OPENAI_BASE_URL=https://api.groq.com/openai/v1,
    OPENAI_MODEL=llama-3.3-70b-versatile — free tier, tool calling supported
  • OpenAI API key: platform.openai.com → usage-based billing, full support
```

## Files Changed
- `agent/core.py` — `OpenAISubscriptionProvider.__init__` raises immediately with guidance
- `config/credentials.py` — option 5 wizard shows deprecation notice + OpenRouter setup
- `web/skills.py` — `openai_subscription` marked deprecated in provider list

## Tests
- Attempting to instantiate `OpenAISubscriptionProvider` raises `RuntimeError` with "openrouter" in the message
- Credentials wizard option 5 outputs deprecation text

## Acceptance Criteria
- `AI_PROVIDER=openai_subscription` → immediate clear error with migration instructions
- No silent failures, no broken partial execution
- Existing `AI_PROVIDER=openai` (with API key or compatible base URL) unaffected
