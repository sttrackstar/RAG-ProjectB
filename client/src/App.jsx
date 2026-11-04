import { useEffect, useRef, useState } from 'react'
import './App.css'
import ConfirmCard from './ConfirmCard'
import LoadingState from './LoadingState'
import Login from './Login'
import Signup from './Signup'
import TracePanel from './TracePanel'

// Documents and web pages the agent looked at, from its steps.
function searchedSources(steps) {
  const searched = steps.flatMap(step => [
    ...(step.result?.sources || []),
    ...(step.result?.results || []).map(page => page.title),
  ])
  return [...new Set(searched)]
}

function App() {
  const [user, setUser] = useState(undefined) // undefined = still checking, null = logged out
  const [authMode, setAuthMode] = useState('login')
  const [history, setHistory] = useState([])
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [steps, setSteps] = useState([])
  const [run, setRun] = useState(null)
  const [pendingAction, setPendingAction] = useState(null)
  const warmedUp = useRef(false)

  // Are we already logged in (session cookie)?
  useEffect(() => {
    fetch('/api/me')
      .then(response => (response.ok ? response.json() : null))
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  // Load this user's saved conversations whenever someone logs in.
  useEffect(() => {
    if (!user) return
    fetch('/api/conversations')
      .then(response => (response.ok ? response.json() : []))
      .then(setHistory)
      .catch(() => setHistory([]))
  }, [user])

  function refreshHistory() {
    fetch('/api/conversations')
      .then(response => (response.ok ? response.json() : []))
      .then(setHistory)
      .catch(() => {})
  }

  function clearAnswer() {
    setError('')
    setAnswer('')
    setSources([])
    setSteps([])
    setRun(null)
    setPendingAction(null)
  }

  async function logout() {
    await fetch('/api/logout', { method: 'POST' }).catch(() => {})
    clearAnswer()
    setHistory([])
    setQuestion('')
    setAuthMode('login')
    setUser(null)
  }

  // Load the model as soon as the user starts typing, so it's ready when they ask.
  function warmUpModel() {
    if (warmedUp.current) return
    warmedUp.current = true
    fetch('/api/warmup', { method: 'POST' }).catch(() => {})
  }

  function showConversation(conversation) {
    clearAnswer()
    setQuestion(conversation.question)
    setAnswer(conversation.answer || 'No answer returned.')
    setSteps(conversation.steps || [])
    setSources(searchedSources(conversation.steps || []))
    if (conversation.run_id) setRun({ id: conversation.run_id, durationMs: conversation.duration_ms })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!question.trim()) return

    setLoading(true)
    clearAnswer()

    try {
      const response = await fetch('/api/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })

      const data = await response.json()

      if (response.status === 401) {
        setUser(null) // the session ended; show the login screen
        return
      }
      if (!response.ok) {
        throw new Error(data.error || 'Request failed')
      }

      setAnswer(data.answer || 'No answer returned.')

      const responseSteps = data.steps || []
      setSteps(responseSteps)
      if (data.run_id) setRun({ id: data.run_id, durationMs: data.duration_ms })
      setPendingAction(data.pending_action || null)
      setSources(searchedSources(responseSteps))
      refreshHistory()
    } catch (err) {
      setError(err.message || 'Unable to contact the agent.')
    } finally {
      setLoading(false)
    }
  }

  if (user === undefined) {
    return <main className="app"><p>Loading...</p></main>
  }

  if (user === null) {
    return authMode === 'login'
      ? <Login onLogin={setUser} onSwitch={() => setAuthMode('signup')} />
      : <Signup onSignup={setUser} onSwitch={() => setAuthMode('login')} />
  }

  return (
    <main className="app">
      <header className="app-header">
        <span>Signed in as <b>{user.username}</b></span>
        <button type="button" className="button-secondary" onClick={logout}>Log out</button>
      </header>

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
          {/* AI-generated answer */}
          <div className="answer-card">
            <div className="section-heading">
              <span className="section-icon">✦</span>
              <h2>AI Answer</h2>
            </div>
            {pendingAction
              ? <ConfirmCard key={pendingAction.id} action={pendingAction} />
              : <p className="answer-text">{answer}</p>}
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

          <TracePanel steps={steps} />

          {run && (
            <p className="run-meta">
              Answered in {(run.durationMs / 1000).toFixed(1)}s ·{' '}
              <a href={`/api/runs/${run.id}`} target="_blank" rel="noreferrer">View full log</a>
            </p>
          )}
        </section>
      )}

      {history.length > 0 && (
        <section className="history">
          <h2>Your recent questions</h2>
          <ul>
            {history.map(conversation => (
              <li key={conversation.id}>
                <button type="button" className="history-item" onClick={() => showConversation(conversation)}>
                  {conversation.question}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  )
}

export default App
