import { useEffect, useState } from 'react'

// Rough stages of an answer. These are timed estimates, not live steps.
const STAGES = [
  'Choosing which tool to use...',
  'Searching our documents and the web...',
  'Reading the results...',
  'Writing the answer...',
]
const STAGE_MS = 2500

function LoadingState() {
  const [stage, setStage] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      // Advance through the stages, then stay on the last one.
      setStage(current => Math.min(current + 1, STAGES.length - 1))
    }, STAGE_MS)
    return () => clearInterval(timer)
  }, [])

  return (
    <section className="result loading" aria-busy="true">
      <p className="loading-status" role="status" aria-live="polite">{STAGES[stage]}</p>
      <div className="skeleton skeleton-heading" />
      <div className="skeleton skeleton-line" />
      <div className="skeleton skeleton-line skeleton-line-short" />
      <div className="skeleton skeleton-step" />
      <div className="skeleton skeleton-step" />
    </section>
  )
}

export default LoadingState
