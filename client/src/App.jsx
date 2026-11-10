
import { useEffect, useRef, useState } from 'react'
import './App.css'
import ConfirmCard from './ConfirmCard'
import LoadingState from './LoadingState'
import Login from './Login'
import Signup from './Signup'
import TracePanel from './TracePanel'

// Extract the documents and web pages used by the agent.
function searchedSources(steps) {
  const searched = steps.flatMap(step => [
    ...(step.result?.sources || []),
    ...(step.result?.results || []).map(page => page.title),
  ])

  return [...new Set(searched)]
}

function App() {
  // Authentication
  const [user, setUser] = useState(undefined)
  const [authMode, setAuthMode] = useState('login')

  // Database-backed conversation history
  const [history, setHistory] = useState([])
  const [historyError, setHistoryError] = useState('')
  const [activeChatId, setActiveChatId] = useState(null)

  // Current conversation
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [steps, setSteps] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Agent features
  const [run, setRun] = useState(null)
  const [pendingAction, setPendingAction] = useState(null)
  const warmedUp = useRef(false)

  // Restore an existing login session.
  useEffect(() => {
    fetch('/api/me')
      .then(response =>
        response.ok ? response.json() : null
      )
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  // Retrieve conversations belonging to the logged-in user.
  async function refreshHistory() {
    try {
      const response = await fetch('/api/conversations')

      if (!response.ok) {
        throw new Error('Failed to load conversations')
      }

      const conversations = await response.json()
      setHistory(conversations)
      setHistoryError('')
    } catch {
      setHistoryError("Couldn't load your recent questions.")
    }
  }

  // Load history after login.
  useEffect(() => {
    if (user) {
      refreshHistory()
    }
  }, [user])

  // Clear the displayed answer and its associated data.
  function clearAnswer() {
    setError('')
    setAnswer('')
    setSources([])
    setSteps([])
    setRun(null)
    setPendingAction(null)
  }

  // Start a new conversation.
  function newChat() {
    setQuestion('')
    clearAnswer()
    setActiveChatId(null)
  }

  // Open a conversation saved in SQLite.
  function showConversation(conversation) {
    clearAnswer()

    setActiveChatId(conversation.id)
    setQuestion(conversation.question)
    setAnswer(conversation.answer || 'No answer returned.')
    setSteps(conversation.steps || [])
    setSources(searchedSources(conversation.steps || []))

    if (conversation.run_id) {
      setRun({
        id: conversation.run_id,
        durationMs: conversation.duration_ms,
      })
    }
  }

  // Delete a conversation through the Flask API.
  async function deleteChat(chatId) {
    try {
      const response = await fetch(
        `/api/conversations/${chatId}`,
        { method: 'DELETE' }
      )

      if (!response.ok) {
        throw new Error('Unable to delete conversation')
      }

      setHistory(previous =>
        previous.filter(chat => chat.id !== chatId)
      )

      if (activeChatId === chatId) {
        newChat()
      }

      setHistoryError('')
    } catch {
      setHistoryError(
        "Couldn't delete this conversation. Please try again."
      )
    }
  }

  // Log out without clearing the screen if the request fails.
  async function logout() {
    const response = await fetch('/api/logout', {
      method: 'POST',
    }).catch(() => null)

    if (!response?.ok) {
      setError("Couldn't log out. Please try again.")
      return
    }

    newChat()
    setHistory([])
    setHistoryError('')
    setAuthMode('login')
    setUser(null)
    warmedUp.current = false
  }

  // Warm up the model when the user begins interacting.
  function warmUpModel() {
    if (warmedUp.current) return

    warmedUp.current = true

    fetch('/api/warmup', {
      method: 'POST',
    }).catch(() => {})
  }

  // Submit a question to the agent.
  async function handleSubmit(event) {
    event.preventDefault()

    if (!question.trim() || loading) return

    setLoading(true)
    clearAnswer()
    setActiveChatId(null)

    try {
      const response = await fetch('/api/agent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question.trim(),
        }),
      })

      const data = await response.json()

      if (response.status === 401) {
        setUser(null)
        setHistory([])
        setActiveChatId(null)
        return
      }

      if (!response.ok) {
        throw new Error(data.error || 'Request failed')
      }

      setAnswer(data.answer || 'No answer returned.')

      const responseSteps = data.steps || []
      setSteps(responseSteps)
      setSources(searchedSources(responseSteps))

      if (data.run_id) {
        setRun({
          id: data.run_id,
          durationMs: data.duration_ms,
        })
      }

      setPendingAction(data.pending_action || null)

      // Flask saves completed conversations to SQLite.
      if (data.conversation_id) {
        setActiveChatId(data.conversation_id)
      }

      await refreshHistory()
    } catch (err) {
      setError(err.message || 'Unable to contact the agent.')
    } finally {
      setLoading(false)
    }
  }

  // Wait while checking the login session.
  if (user === undefined) {
    return (
      <main className="app">
        <p>Loading...</p>
      </main>
    )
  }

  // Display authentication screens when logged out.
  if (user === null) {
    return authMode === 'login'
      ? (
        <Login
          onLogin={setUser}
          onSwitch={() => setAuthMode('signup')}
        />
      )
      : (
        <Signup
          onSignup={setUser}
          onSwitch={() => setAuthMode('login')}
        />
      )
  }

  return (
    <main className="app-layout">
      {/* Past Chats sidebar */}
      <aside className="chat-history">
        <h2>Past Chats</h2>

        <button
          type="button"
          onClick={newChat}
          className="new-chat-button"
        >
          + New Chat
        </button>

        {historyError && (
          <p className="error">{historyError}</p>
        )}

        {history.length === 0 ? (
          !historyError && <p>No saved chats yet.</p>
        ) : (
          <ul>
            {history.map(chat => (
              <li
                key={chat.id}
                className={
                  activeChatId === chat.id
                    ? 'active-chat'
                    : ''
                }
              >
                <button
                  type="button"
                  className="history-chat-button"
                  onClick={() => showConversation(chat)}
                >
                  {chat.question}
                </button>

                <button
                  type="button"
                  className="delete-chat-button"
                  onClick={() => deleteChat(chat.id)}
                  aria-label={`Delete ${chat.question}`}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* Main application */}
      <div className="app">
        <header className="app-header">
          <span>
            Signed in as <b>{user.username}</b>
          </span>

          <button
            type="button"
            className="button-secondary"
            onClick={logout}
          >
            Log out
          </button>
        </header>

        <h1>Research Aide</h1>
        <p>Ask questions about your knowledge base.</p>

        {/* Question form */}
        <form onSubmit={handleSubmit}>
          <textarea
            value={question}
            onChange={event => setQuestion(event.target.value)}
            onFocus={warmUpModel}
            placeholder="Ask a question..."
            rows={4}
          />

          <button
            type="submit"
            disabled={loading || !question.trim()}
          >
            {loading ? 'Thinking...' : 'Ask Research Aide'}
          </button>
        </form>

        {error && (
          <p className="error">{error}</p>
        )}

        {/* Loading animation */}
        {loading && <LoadingState />}

        {/* Answer and sources */}
        {answer && (
          <section className="result">
            <div className="answer-card">
              <div className="section-heading">
                <span className="section-icon">✦</span>
                <h2>AI Answer</h2>
              </div>

              {pendingAction ? (
                <ConfirmCard
                  key={pendingAction.id}
                  action={pendingAction}
                />
              ) : (
                <p className="answer-text">{answer}</p>
              )}
            </div>

            {sources.length > 0 && (
              <div className="sources-card">
                <div className="section-heading">
                  <span className="section-icon">📚</span>
                  <h2>Sources Searched</h2>
                  <span className="source-count">
                    {sources.length}
                  </span>
                </div>

                <ul className="sources-list">
                  {sources.map(source => (
                    <li
                      className="source-item"
                      key={source}
                    >
                      <span className="source-icon">
                        📄
                      </span>
                      <span>{source}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Agent execution trace */}
            <TracePanel steps={steps} />

            {/* Observability */}
            {run && (
              <p className="run-meta">
                Answered in{' '}
                {(run.durationMs / 1000).toFixed(1)}s
                {' · '}
                <a
                  href={`/api/runs/${run.id}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  View full log
                </a>
              </p>
            )}
          </section>
        )}
      </div>
    </main>
  )
}

export default App
