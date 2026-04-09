import { useState } from 'react'

export default function TradingSettingsStep({ formData, setFormData, onNext }) {
  const [capital, setCapital] = useState(formData.capital || 200000)
  const [riskPct, setRiskPct] = useState(formData.riskPct || 2)
  const [mode, setMode] = useState(formData.tradingMode || 'PAPER')

  const handleNext = () => {
    setFormData((prev) => ({
      ...prev,
      capital,
      riskPct,
      tradingMode: mode,
    }))
    onNext()
  }

  return (
    <div className="flex flex-col flex-1 gap-6 animate-fade-slide">
      <div className="text-center">
        <h2 className="text-text text-lg font-semibold font-ui">Trading Settings</h2>
        <p className="text-muted text-xs font-ui mt-1">
          Configure your capital and risk parameters
        </p>
      </div>

      <div className="max-w-md mx-auto w-full space-y-5">
        {/* Capital */}
        <div className="space-y-2">
          <label className="text-text text-sm font-ui font-semibold block">
            Trading Capital (INR)
          </label>
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(Number(e.target.value) || 0)}
            min={0}
            step={10000}
            className="w-full bg-elevated border border-border rounded-lg px-3 py-2.5
                       text-text text-sm font-mono
                       focus:outline-none focus:border-amber"
          />
          <p className="text-muted text-[11px] font-ui">
            Total capital allocated for trading. Used for position sizing.
          </p>
        </div>

        {/* Risk */}
        <div className="space-y-2">
          <label className="text-text text-sm font-ui font-semibold block">
            Risk Per Trade (%)
          </label>
          <input
            type="number"
            value={riskPct}
            onChange={(e) => setRiskPct(Number(e.target.value) || 0)}
            min={0.1}
            max={10}
            step={0.5}
            className="w-full bg-elevated border border-border rounded-lg px-3 py-2.5
                       text-text text-sm font-mono
                       focus:outline-none focus:border-amber"
          />
          <p className="text-muted text-[11px] font-ui">
            Maximum percentage of capital risked per trade. 1-2% recommended.
          </p>
        </div>

        {/* Trading Mode */}
        <div className="space-y-2">
          <label className="text-text text-sm font-ui font-semibold block">
            Trading Mode
          </label>
          <div className="flex gap-3">
            <button
              onClick={() => setMode('PAPER')}
              className={`flex-1 py-2.5 rounded-lg border text-sm font-ui font-semibold transition-all
                ${
                  mode === 'PAPER'
                    ? 'border-amber bg-amber/10 text-amber'
                    : 'border-border bg-elevated text-muted hover:border-subtle'
                }`}
            >
              Paper Trading
            </button>
            <button
              onClick={() => setMode('LIVE')}
              className={`flex-1 py-2.5 rounded-lg border text-sm font-ui font-semibold transition-all
                ${
                  mode === 'LIVE'
                    ? 'border-red bg-red/10 text-red'
                    : 'border-border bg-elevated text-muted hover:border-subtle'
                }`}
            >
              Live Trading
            </button>
          </div>
          {mode === 'LIVE' && (
            <p className="text-red text-[11px] font-ui">
              Live mode executes real trades with real money. Make sure your broker is connected and you understand the risks.
            </p>
          )}
          {mode === 'PAPER' && (
            <p className="text-muted text-[11px] font-ui">
              Paper mode simulates trades without real money. Recommended for getting started.
            </p>
          )}
        </div>
      </div>

      <div className="flex justify-end max-w-md mx-auto w-full mt-auto">
        <button
          onClick={handleNext}
          className="px-6 py-2 bg-amber text-surface font-ui font-semibold text-sm rounded-lg
                     hover:brightness-110 transition-all active:scale-95"
        >
          Next
        </button>
      </div>
    </div>
  )
}
