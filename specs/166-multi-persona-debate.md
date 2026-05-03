# Spec: Multi-persona debate command (#166)

## Summary
Add a `debate` REPL command that runs all 5 named investor personas (Buffett, Jhunjhunwala,
Lynch, Soros, Munger) on a stock and displays a consensus table with dissent notes.

## Commands
- `debate INFY` — run all 5 personas on INFY (NSE)
- `debate NSE:RELIANCE` — explicit exchange
- `persona list` — list all available personas
- `persona buffett INFY` — single persona analysis

## Output Format
- Rich table: Persona | Signal | Confidence | Key Factor
- Consensus line: "3/5 BUY — Jhunjhunwala, Lynch, Munger"
- Dissent line: "HOLD camp: Buffett (moat premium), Soros (macro uncertain)"

## Implementation
- `app/commands/persona.py` — run_debate_command() and _cmd_debate()
- `agent/persona_agent.py` — run_debate() calls run_persona_analysis() for each persona
- `agent/schemas.py` — PersonaSignal dataclass
- Wired in `app/repl.py` as `elif command == "debate"` and `elif command == "persona"`

## Tests
- `tests/test_persona_debate.py`
