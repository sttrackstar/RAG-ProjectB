function ToolResult({ result }) {
  if (!result) return null

  if (result.error) {
    return <p className="step-error">Error: {result.error}</p>
  }

  if (result.results) {
    if (result.results.length === 0) return <p>No web pages found.</p>
    return (
      <ul className="step-links">
        {result.results.map(page => (
          <li key={page.url}>
            <a href={page.url} target="_blank" rel="noreferrer">{page.title}</a>
          </li>
        ))}
      </ul>
    )
  }

  if (result.sources) {
    return (
      <>
        <p>{result.answer}</p>
        <p className="step-meta">Documents: {result.sources.join(', ') || 'none'}</p>
      </>
    )
  }

  return <pre>{JSON.stringify(result, null, 2)}</pre>
}

function TracePanel({ steps }) {
  if (!steps.length) return null

  return (
    <section className="trace">
      <h2>Agent trace</h2>
      <ol>
        {steps.map((step, index) => (
          <li key={index} className={`step step-${step.type}`}>
            <p className="step-title">
              Step {index + 1} · {step.tool || 'Agent'}
              {step.type === 'needs_confirmation' && ' · waiting for your confirmation'}
            </p>

            {step.arguments && (
              <code className="step-args">{JSON.stringify(step.arguments)}</code>
            )}

            {step.type === 'tool_call' && <ToolResult result={step.result} />}
            {step.type === 'error' && <p className="step-error">Error: {step.error}</p>}
          </li>
        ))}
      </ol>
    </section>
  )
}

export default TracePanel
