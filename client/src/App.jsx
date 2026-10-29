
import { useState } from 'react'
import './App.css'
import TracePanel from './TracePanel'

function App() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [steps, setSteps] = useState([])

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
          placeholder="Ask a question..."
          rows={4}
        />

        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? 'Thinking...' : 'Ask Research Aide'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {answer && (
        <section className="result">

          {/* AI-generated answer */}
        <div className="answer-card">
        <div className="section-heading">
        <span className="section-icon">✦</span>
        <h2>AI Answer</h2>
        </div>

        <p className="answer-text">{answer}</p>
        </div>

      {/* Documents and pages searched */}
      {sources.length > 0 && (
      <div className="sources-card">
        <div className="section-heading">
          <span className="section-icon">📚</span>
          <h2>Sources Searched</h2>
          <span className="source-count">{sources.length}</span>
        </div>

        <ul className="sources-list">
          {sources.map(source => (
            <li className="source-item" key={source}>
              <span className="source-icon">📄</span>
              <span>{source}</span>
            </li>
          ))}
        </ul>
      </div>
    )}

    {/* Existing agent trace */}
    <TracePanel steps={steps} />

  </section>
)}


      
    </main>
  )
}

export default App
