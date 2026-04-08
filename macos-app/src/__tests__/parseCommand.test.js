import { describe, it, expect } from 'vitest'

// Copied verbatim from src/renderer/src/components/Input/InputBar.jsx
// so we can test it as a pure function without importing the React component.
function parseCommand(input) {
  const parts = input.trim().split(/\s+/)
  const cmd   = parts[0].toLowerCase()
  const args  = parts.slice(1)

  switch (cmd) {
    case 'quote': case 'q':
      if (!args[0]) return { error: 'Usage: quote SYMBOL' }
      return { endpoint: '/skills/quote', body: { symbol: args[0].toUpperCase() }, cardType: 'quote' }

    case 'analyze': case 'analyse': case 'a':
      if (!args[0]) return { error: 'Usage: analyze SYMBOL' }
      return { stream: true, symbol: args[0].toUpperCase(), exchange: args[1]?.toUpperCase() ?? 'NSE' }

    case 'morning-brief': case 'brief': case 'mb':
      return { endpoint: '/skills/morning_brief', body: {}, cardType: 'morning_brief' }

    case 'flows': case 'flow':
      return { endpoint: '/skills/flows', body: {}, cardType: 'flows' }

    case 'holdings': case 'h':
      return { endpoint: '/skills/holdings', body: {}, cardType: 'holdings' }

    case 'positions': case 'pos':
      return { endpoint: '/skills/positions', body: {}, cardType: 'holdings' }

    case 'backtest': case 'bt':
      if (args.length < 2) return { error: 'Usage: backtest SYMBOL STRATEGY  (e.g. backtest RELIANCE rsi)' }
      return {
        endpoint: '/skills/backtest',
        body: { symbol: args[0].toUpperCase(), strategy: args[1] },
        cardType: 'backtest',
      }

    case 'macro':
      return { endpoint: '/skills/macro', body: {}, cardType: 'markdown' }

    case 'earnings':
      return { endpoint: '/skills/earnings', body: { symbols: args }, cardType: 'markdown' }

    // ── High-value additions ──────────────────────────────────

    case 'deep-analyze': case 'deep-analyse': case 'da':
      if (!args[0]) return { error: 'Usage: deep-analyze SYMBOL [EXCHANGE]' }
      return {
        endpoint: '/skills/deep_analyze',
        body: { symbol: args[0].toUpperCase(), exchange: args[1]?.toUpperCase() ?? 'NSE' },
        cardType: 'markdown',
      }

    case 'funds': case 'fund':
      return { endpoint: '/skills/funds', body: {}, cardType: 'funds', method: 'GET' }

    case 'profile':
      return { endpoint: '/skills/profile', body: {}, cardType: 'profile', method: 'GET' }

    case 'orders': case 'order':
      return { endpoint: '/skills/orders', body: {}, cardType: 'orders', method: 'GET' }

    case 'alerts': case 'al':
      return { endpoint: '/skills/alerts/list', body: {}, cardType: 'alerts' }

    case 'alert':
      // alert SYMBOL above/below PRICE
      // alert remove ID
      if (args[0] === 'remove' || args[0] === 'rm') {
        if (!args[1]) return { error: 'Usage: alert remove ALERT_ID' }
        return { endpoint: '/skills/alerts/remove', body: { alert_id: args[1] }, cardType: 'markdown' }
      }
      if (args.length < 3) return { error: 'Usage: alert SYMBOL above|below PRICE' }
      return {
        endpoint: '/skills/alerts/add',
        body: {
          symbol:    args[0].toUpperCase(),
          condition: args[1].toLowerCase(),   // above / below / crosses
          threshold: Number(args[2]),
        },
        cardType: 'markdown',
      }

    case 'oi':
      if (!args[0]) return { error: 'Usage: oi SYMBOL [EXCHANGE]' }
      return {
        endpoint: '/skills/oi_profile',
        body: { symbol: args[0].toUpperCase(), exchange: args[1]?.toUpperCase() ?? 'NSE' },
        cardType: 'oi',
      }

    case 'patterns': case 'pat':
      return { endpoint: '/skills/patterns', body: {}, cardType: 'patterns' }

    case 'greeks': case 'greek':
      return { endpoint: '/skills/greeks', body: {}, cardType: 'greeks' }

    case 'scan':
      return {
        endpoint: '/skills/scan',
        body: { scan_type: args[0] ?? 'options', filters: {} },
        cardType: 'scan',
      }

    case 'deals': case 'bulk-deals':
      return {
        endpoint: '/skills/deals',
        body: { symbol: args[0]?.toUpperCase() ?? null, days: 5 },
        cardType: 'deals',
      }

    case 'iv-smile': case 'smile': case 'ivsmile': {
      const sym = args[0]?.toUpperCase() ?? 'NIFTY'
      return { endpoint: '/skills/iv_smile', body: { symbol: sym, expiry: args[1] ?? null }, cardType: 'iv_smile' }
    }
    case 'gex': {
      const sym = args[0]?.toUpperCase() ?? 'NIFTY'
      return { endpoint: '/skills/gex', body: { symbol: sym, expiry: args[1] ?? null }, cardType: 'gex' }
    }
    case 'delta-hedge': case 'dh': case 'deltahedge':
      return { endpoint: '/skills/delta_hedge', body: null, cardType: 'delta_hedge', method: 'GET' }
    case 'risk-report': case 'risk': case 'var':
      return { endpoint: '/skills/risk_report', body: null, cardType: 'risk_report', method: 'GET' }
    case 'walkforward': case 'wf': case 'walk-forward': {
      const sym = args[0]?.toUpperCase() ?? 'NIFTY'
      const strat = args[1] ?? 'rsi'
      return { endpoint: '/skills/walkforward', body: { symbol: sym, strategy: strat, window_months: 6 }, cardType: 'walkforward' }
    }
    case 'whatif': case 'what-if': case 'scenario': {
      // whatif nifty -5   → market move
      // whatif RELIANCE +10 → stock move
      // whatif             → 3-scenario sweep
      const sym = args[0]?.toUpperCase()
      const chg = parseFloat(args[1])
      if (sym && (sym === 'NIFTY' || sym === 'MARKET') && !isNaN(chg)) {
        return { endpoint: '/skills/whatif', body: { scenario: 'market', nifty_change: chg }, cardType: 'whatif' }
      } else if (sym && !isNaN(chg)) {
        return { endpoint: '/skills/whatif', body: { scenario: 'stock', symbol: sym, stock_change: chg }, cardType: 'whatif' }
      }
      return { endpoint: '/skills/whatif', body: { scenario: 'market' }, cardType: 'whatif' }
    }
    case 'strategy': case 'strat': {
      const sym = args[0]?.toUpperCase() ?? 'NIFTY'
      const view = (args[1] ?? 'bullish').toUpperCase()
      const dte = parseInt(args[2]) || 30
      return { endpoint: '/skills/strategy', body: { symbol: sym, view, dte }, cardType: 'strategy' }
    }
    case 'drift':
      return { endpoint: '/skills/drift', body: null, cardType: 'drift', method: 'GET' }
    case 'memory': case 'mem':
      return { endpoint: '/skills/memory', body: null, cardType: 'memory', method: 'GET' }
    case 'audit': {
      const trade_id = args[0]
      if (!trade_id) return { endpoint: '/skills/memory', body: null, cardType: 'memory', method: 'GET' }
      return { endpoint: '/skills/audit', body: { trade_id }, cardType: 'audit' }
    }
    case 'telegram': case 'tg':
      return { endpoint: '/skills/telegram/status', body: null, cardType: 'telegram', method: 'GET' }
    case 'provider': {
      if (args[0]) {
        return { endpoint: '/skills/provider', body: { provider: args[0], model: args[1] ?? null }, cardType: 'provider' }
      }
      return { endpoint: '/skills/provider', body: null, cardType: 'provider', method: 'GET' }
    }
    case 'pairs': {
      const symA = args[0]?.toUpperCase() ?? 'RELIANCE'
      const symB = args[1]?.toUpperCase() ?? 'TCS'
      return { endpoint: '/skills/pairs', body: { stock_a: symA, stock_b: symB }, cardType: 'pairs' }
    }

    default:
      // Fall through to AI chat
      return { endpoint: '/skills/chat', body: { message: input }, cardType: 'markdown' }
  }
}

// ─────────────────────────────────────────────────────────────────────────────

describe('parseCommand', () => {
  // ── quote ─────────────────────────────────────────────────────────────────
  it('parses quote command', () => {
    const result = parseCommand('quote RELIANCE')
    expect(result.endpoint).toBe('/skills/quote')
    expect(result.body).toEqual({ symbol: 'RELIANCE' })
    expect(result.cardType).toBe('quote')
  })

  it('quote alias q works', () => {
    const result = parseCommand('q INFY')
    expect(result.endpoint).toBe('/skills/quote')
    expect(result.body.symbol).toBe('INFY')
  })

  it('quote without symbol returns error', () => {
    const result = parseCommand('quote')
    expect(result.error).toBe('Usage: quote SYMBOL')
  })

  // ── analyze ───────────────────────────────────────────────────────────────
  it('parses analyze command with stream flag', () => {
    const result = parseCommand('analyze NIFTY')
    expect(result.stream).toBe(true)
    expect(result.symbol).toBe('NIFTY')
    expect(result.exchange).toBe('NSE')
  })

  it('analyze with explicit exchange uppercases it', () => {
    const result = parseCommand('analyze BANKNIFTY bse')
    expect(result.symbol).toBe('BANKNIFTY')
    expect(result.exchange).toBe('BSE')
  })

  it('analyze aliases: analyse and a', () => {
    const r1 = parseCommand('analyse TCS')
    const r2 = parseCommand('a TCS')
    expect(r1.stream).toBe(true)
    expect(r1.symbol).toBe('TCS')
    expect(r2.stream).toBe(true)
    expect(r2.symbol).toBe('TCS')
  })

  it('analyze without symbol returns error', () => {
    const result = parseCommand('analyze')
    expect(result.error).toBe('Usage: analyze SYMBOL')
  })

  // ── holdings / positions ──────────────────────────────────────────────────
  it('parses holdings', () => {
    const result = parseCommand('holdings')
    expect(result.endpoint).toBe('/skills/holdings')
    expect(result.cardType).toBe('holdings')
  })

  it('positions alias pos maps to holdings cardType', () => {
    const result = parseCommand('pos')
    expect(result.endpoint).toBe('/skills/positions')
    expect(result.cardType).toBe('holdings')
  })

  // ── funds / profile / orders (GET method) ─────────────────────────────────
  it('funds uses GET method', () => {
    const result = parseCommand('funds')
    expect(result.endpoint).toBe('/skills/funds')
    expect(result.method).toBe('GET')
    expect(result.cardType).toBe('funds')
  })

  it('profile uses GET method', () => {
    const result = parseCommand('profile')
    expect(result.endpoint).toBe('/skills/profile')
    expect(result.method).toBe('GET')
    expect(result.cardType).toBe('profile')
  })

  it('orders uses GET method', () => {
    const result = parseCommand('orders')
    expect(result.endpoint).toBe('/skills/orders')
    expect(result.method).toBe('GET')
    expect(result.cardType).toBe('orders')
  })

  // ── iv-smile ──────────────────────────────────────────────────────────────
  it('iv-smile returns iv_smile cardType', () => {
    const result = parseCommand('iv-smile NIFTY')
    expect(result.endpoint).toBe('/skills/iv_smile')
    expect(result.cardType).toBe('iv_smile')
    expect(result.body.symbol).toBe('NIFTY')
    expect(result.body.expiry).toBeNull()
  })

  it('iv-smile defaults symbol to NIFTY when omitted', () => {
    const result = parseCommand('iv-smile')
    expect(result.body.symbol).toBe('NIFTY')
  })

  // ── gex ───────────────────────────────────────────────────────────────────
  it('gex returns gex cardType', () => {
    const result = parseCommand('gex BANKNIFTY')
    expect(result.endpoint).toBe('/skills/gex')
    expect(result.cardType).toBe('gex')
    expect(result.body.symbol).toBe('BANKNIFTY')
  })

  it('gex defaults symbol to NIFTY when omitted', () => {
    const result = parseCommand('gex')
    expect(result.body.symbol).toBe('NIFTY')
  })

  // ── delta-hedge ───────────────────────────────────────────────────────────
  it('delta-hedge alias dh returns delta_hedge cardType GET', () => {
    const r1 = parseCommand('delta-hedge')
    const r2 = parseCommand('dh')
    expect(r1.endpoint).toBe('/skills/delta_hedge')
    expect(r1.cardType).toBe('delta_hedge')
    expect(r1.method).toBe('GET')
    expect(r2.endpoint).toBe('/skills/delta_hedge')
    expect(r2.method).toBe('GET')
  })

  // ── risk-report ───────────────────────────────────────────────────────────
  it('risk-report alias risk returns risk_report cardType GET', () => {
    const r1 = parseCommand('risk-report')
    const r2 = parseCommand('risk')
    expect(r1.endpoint).toBe('/skills/risk_report')
    expect(r1.cardType).toBe('risk_report')
    expect(r1.method).toBe('GET')
    expect(r2.endpoint).toBe('/skills/risk_report')
    expect(r2.method).toBe('GET')
  })

  // ── walkforward ───────────────────────────────────────────────────────────
  it('walkforward parses symbol and strategy', () => {
    const result = parseCommand('walkforward RELIANCE momentum')
    expect(result.endpoint).toBe('/skills/walkforward')
    expect(result.cardType).toBe('walkforward')
    expect(result.body.symbol).toBe('RELIANCE')
    expect(result.body.strategy).toBe('momentum')
    expect(result.body.window_months).toBe(6)
  })

  it('walkforward defaults to NIFTY/rsi when args omitted', () => {
    const result = parseCommand('walkforward')
    expect(result.body.symbol).toBe('NIFTY')
    expect(result.body.strategy).toBe('rsi')
  })

  // ── whatif ────────────────────────────────────────────────────────────────
  it('whatif nifty -5 parses as market move', () => {
    const result = parseCommand('whatif nifty -5')
    expect(result.endpoint).toBe('/skills/whatif')
    expect(result.cardType).toBe('whatif')
    expect(result.body.scenario).toBe('market')
    expect(result.body.nifty_change).toBe(-5)
  })

  it('whatif RELIANCE +10 parses as stock move', () => {
    const result = parseCommand('whatif RELIANCE +10')
    expect(result.endpoint).toBe('/skills/whatif')
    expect(result.body.scenario).toBe('stock')
    expect(result.body.symbol).toBe('RELIANCE')
    expect(result.body.stock_change).toBe(10)
  })

  it('whatif with no args returns market sweep', () => {
    const result = parseCommand('whatif')
    expect(result.endpoint).toBe('/skills/whatif')
    expect(result.body.scenario).toBe('market')
    expect(result.body.nifty_change).toBeUndefined()
  })

  // ── strategy ──────────────────────────────────────────────────────────────
  it('strategy parses symbol view and dte', () => {
    const result = parseCommand('strategy NIFTY bullish 21')
    expect(result.endpoint).toBe('/skills/strategy')
    expect(result.cardType).toBe('strategy')
    expect(result.body.symbol).toBe('NIFTY')
    expect(result.body.view).toBe('BULLISH')
    expect(result.body.dte).toBe(21)
  })

  it('strategy defaults to NIFTY/bullish/30 when args omitted', () => {
    const result = parseCommand('strategy')
    expect(result.body.symbol).toBe('NIFTY')
    expect(result.body.view).toBe('BULLISH')
    expect(result.body.dte).toBe(30)
  })

  // ── drift ─────────────────────────────────────────────────────────────────
  it('drift is GET', () => {
    const result = parseCommand('drift')
    expect(result.endpoint).toBe('/skills/drift')
    expect(result.method).toBe('GET')
    expect(result.cardType).toBe('drift')
  })

  // ── memory ────────────────────────────────────────────────────────────────
  it('memory alias mem is GET', () => {
    const r1 = parseCommand('memory')
    const r2 = parseCommand('mem')
    expect(r1.endpoint).toBe('/skills/memory')
    expect(r1.method).toBe('GET')
    expect(r1.cardType).toBe('memory')
    expect(r2.endpoint).toBe('/skills/memory')
    expect(r2.method).toBe('GET')
  })

  // ── audit ─────────────────────────────────────────────────────────────────
  it('audit with id returns audit endpoint', () => {
    const result = parseCommand('audit trade-42')
    expect(result.endpoint).toBe('/skills/audit')
    expect(result.cardType).toBe('audit')
    expect(result.body).toEqual({ trade_id: 'trade-42' })
  })

  it('audit without id falls back to memory', () => {
    const result = parseCommand('audit')
    expect(result.endpoint).toBe('/skills/memory')
    expect(result.cardType).toBe('memory')
    expect(result.method).toBe('GET')
  })

  // ── telegram ──────────────────────────────────────────────────────────────
  it('telegram alias tg returns telegram status GET', () => {
    const r1 = parseCommand('telegram')
    const r2 = parseCommand('tg')
    expect(r1.endpoint).toBe('/skills/telegram/status')
    expect(r1.cardType).toBe('telegram')
    expect(r1.method).toBe('GET')
    expect(r2.endpoint).toBe('/skills/telegram/status')
    expect(r2.method).toBe('GET')
  })

  // ── provider ──────────────────────────────────────────────────────────────
  it('provider with arg sends POST body', () => {
    const result = parseCommand('provider openai gpt-4o')
    expect(result.endpoint).toBe('/skills/provider')
    expect(result.cardType).toBe('provider')
    expect(result.body).toEqual({ provider: 'openai', model: 'gpt-4o' })
    expect(result.method).toBeUndefined()
  })

  it('provider with only provider name sets model to null', () => {
    const result = parseCommand('provider anthropic')
    expect(result.body.provider).toBe('anthropic')
    expect(result.body.model).toBeNull()
  })

  it('provider without arg is GET', () => {
    const result = parseCommand('provider')
    expect(result.endpoint).toBe('/skills/provider')
    expect(result.method).toBe('GET')
    expect(result.body).toBeNull()
  })

  // ── pairs ─────────────────────────────────────────────────────────────────
  it('pairs parses two symbols', () => {
    const result = parseCommand('pairs RELIANCE TCS')
    expect(result.endpoint).toBe('/skills/pairs')
    expect(result.cardType).toBe('pairs')
    expect(result.body).toEqual({ stock_a: 'RELIANCE', stock_b: 'TCS' })
  })

  it('pairs defaults to RELIANCE/TCS when args omitted', () => {
    const result = parseCommand('pairs')
    expect(result.body.stock_a).toBe('RELIANCE')
    expect(result.body.stock_b).toBe('TCS')
  })

  // ── default / chat fallthrough ────────────────────────────────────────────
  it('unknown command routes to chat endpoint', () => {
    const input = 'what is the best stock to buy today'
    const result = parseCommand(input)
    expect(result.endpoint).toBe('/skills/chat')
    expect(result.cardType).toBe('markdown')
    expect(result.body).toEqual({ message: input })
  })

  it('unknown single-word command routes to chat endpoint', () => {
    const result = parseCommand('foobar')
    expect(result.endpoint).toBe('/skills/chat')
    expect(result.body.message).toBe('foobar')
  })
})
