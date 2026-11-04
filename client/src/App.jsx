
import { useRef, useState, useEffect } from 'react'
import './App.css'
import TracePanel from './TracePanel'

function App() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [steps, setSteps] = useState([])
  const [activeChatId, setActiveChatId] = useState(null)
  const warmedUp = useRef(false)

  const [chatHistory, setChatHistory] = useState(() => {
    try {
      const saved = localStorage.getItem('research-aide-chats')
      const parsed = saved ? JSON.parse(saved) : []
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  })

  useEffect(() => {
    localStorage.setItem(
      'research-aide-chats',
      JSON.stringify(chatHistory)
    )
  }, [chatHistory])

  // Load the model as soon as the user starts typing, so it's ready when they ask.
  function warmUpModel() {
    if (warmedUp.current) return
    warmedUp.current = true
    fetch('/api/warmup', { method: 'POST' }).catch(() => { })
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
      const newChat = {
        id: crypto.randomUUID(),
        question: question.trim(),
        answer: data.answer || 'No answer returned.',
        sources: [...new Set(searched)],
        steps: responseSteps,
        createdAt: new Date().toISOString(),
      }

      setChatHistory(previous => [newChat, ...previous])
      setActiveChatId(newChat.id)
    } catch (err) {
      setError(err.message || 'Unable to contact the agent.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="app-layout">
      <section className="chat-history">
        <h2>Past Chats</h2>
        <button
          type="button"
          onClick={() => {
            setQuestion('')
            setAnswer('')
            setSources([])
            setSteps([])
            setError('')
            setActiveChatId(null)
          }}
        >
          + New Chat
        </button>

        {chatHistory.length === 0 ? (
          <p>No saved chats yet.</p>
        ) : (
          <ul>
            {chatHistory.map(chat => (
              <li key={chat.id}>
                <button
                  type="button"
                  onClick={() => {
                    setQuestion(chat.question)
                    setAnswer(chat.answer)
                    setSources(chat.sources)
                    setSteps(chat.steps)
                    setError('')
                    setActiveChatId(chat.id)
                  }}
                >
                  {chat.question}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setChatHistory(previous =>
                      previous.filter(savedChat => savedChat.id !== chat.id)
                    )
                    if (activeChatId === chat.id) {
                      setQuestion('')
                      setAnswer('')
                      setSources([])
                      setSteps([])
                      setError('')
                      setActiveChatId(null)
                    }
                  }}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
      <div className="app">
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
      </div>
    </main>
  )
}

export default App
