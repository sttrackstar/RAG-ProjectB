
import { useRef, useState } from 'react'
import './App.css'
import LoadingState from './LoadingState'
import TracePanel from './TracePanel'

function App() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [steps, setSteps] = useState([])
  const warmedUp = useRef(false)

  // Load the model as soon as the user starts typing, so it's ready when they ask.
  function warmUpModel() {
    if (warmedUp.current) return
    warmedUp.current = true
    fetch('/api/warmup', { method: 'POST' }).catch(() => {})
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!question.trim()) return

    setLoading(true)
    setError('')
    setAnswer('')
    setSources([])
    setSteps([])

    try {
      const response = await fetch('/api/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Request failed')
      }

      setAnswer(data.answer || 'No answer returned.')

      const responseSteps = data.steps || []
      setSteps(responseSteps)

      const searched = responseSteps.flatMap(step => [
        ...(step.result?.sources || []),
        ...(step.result?.results || []).map(page => page.title),
      ])
      setSources([...new Set(searched)])
    } catch (err) {
      setError(err.message || 'Unable to contact the agent.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="app">
      <h1>Research Aide</h1>
      <p>Ask questions about your knowledge base.</p>

      <form onSubmit={handleSubmit}>
        <textarea
          value={question}
          onChange={event => setQuestion(event.target.value)}
          onFocus={warmUpModel}
          placeholder="Ask a question..."
          rows={4}
        />

        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? 'Thinking...' : 'Ask Research Aide'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {loading && <LoadingState />}

      {answer && (
        <section className="result">
          <h2>Answer</h2>
          <p>{answer}</p>

          {sources.length > 0 && (
            <>
              <h3>Searched</h3>
              <ul>
                {sources.map(source => (
                  <li key={source}>{source}</li>
                ))}
              </ul>
            </>
          )}

          <TracePanel steps={steps} />
        </section>
      )}
    </main>
  )
}

export default App
