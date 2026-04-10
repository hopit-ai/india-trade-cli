import { useState } from 'react'
import { getBaseUrl } from '../../store/chatStore'
import StepIndicator from './StepIndicator'
import WelcomeStep from './WelcomeStep'
import ProviderStep from './ProviderStep'
import MarketDataStep from './MarketDataStep'
import TradingSettingsStep from './TradingSettingsStep'
import CompletionStep from './CompletionStep'

const TOTAL_STEPS = 5

export default function OnboardingWizard({ port, onComplete }) {
  const [step, setStep] = useState(0)
  const [completing, setCompleting] = useState(false)
  const [formData, setFormData] = useState({
    aiProvider: '',
    newsApiSet: false,
    brokerName: '',
    capital: 200000,
    riskPct: 2,
    tradingMode: 'PAPER',
  })

  const base = getBaseUrl(port)

  const handleComplete = async () => {
    setCompleting(true)
    try {
      await fetch(`${base}/api/onboarding/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          capital: formData.capital || 200000,
          risk_pct: formData.riskPct || 2,
          trading_mode: formData.tradingMode || 'PAPER',
        }),
      })
      onComplete()
    } catch (err) {
      console.error('Failed to complete onboarding:', err)
      setCompleting(false)
    }
  }

  const next = () => setStep((s) => Math.min(s + 1, TOTAL_STEPS - 1))

  const renderStep = () => {
    switch (step) {
      case 0:
        return <WelcomeStep onNext={next} />
      case 1:
        return (
          <ProviderStep
            formData={formData}
            setFormData={setFormData}
            onNext={next}
            port={port}
          />
        )
      case 2:
        return (
          <MarketDataStep
            formData={formData}
            setFormData={setFormData}
            onNext={next}
            port={port}
          />
        )
      case 3:
        return (
          <TradingSettingsStep
            formData={formData}
            setFormData={setFormData}
            onNext={next}
          />
        )
      case 4:
        return (
          <CompletionStep
            formData={formData}
            onComplete={handleComplete}
            completing={completing}
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="flex flex-col h-full bg-surface">
      {/* Draggable title bar */}
      <div className="drag h-[52px] flex items-center justify-center flex-shrink-0 bg-panel border-b border-border">
        <div className="w-[76px] flex-shrink-0" />
        <div className="flex-1 flex items-center justify-center gap-2 pointer-events-none">
          <span className="text-amber text-[15px]">&#9670;</span>
          <span className="text-text text-[13px] font-semibold tracking-wide font-ui">
            India Trade
          </span>
        </div>
        <div className="w-[76px] flex-shrink-0" />
      </div>

      {/* Step indicator */}
      <StepIndicator current={step} total={TOTAL_STEPS} />

      {/* Step content */}
      <div className="flex-1 flex flex-col px-8 pb-8 overflow-y-auto">
        {renderStep()}
      </div>
    </div>
  )
}
