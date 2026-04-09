export default function StepIndicator({ current, total = 5 }) {
  return (
    <div className="flex items-center gap-2 justify-center py-4">
      {Array.from({ length: total }, (_, i) => {
        let cls = 'w-2 h-2 rounded-full transition-all duration-300'
        if (i < current) {
          cls += ' bg-green'
        } else if (i === current) {
          cls += ' bg-amber w-3 h-3'
        } else {
          cls += ' bg-subtle'
        }
        return <span key={i} className={cls} />
      })}
    </div>
  )
}
