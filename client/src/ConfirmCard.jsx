import { useState } from 'react'

// Shown when the agent pauses before a consequential action (like saving a note).
// Nothing runs until the user clicks Confirm; Cancel discards the action.
function ConfirmCard({ action }) {
  const [status, setStatus] = useState('waiting')
  const [message, setMessage] = useState('')

  async function respond(choice) {
    setStatus('working')
    try {
      const response = await fetch(`/api/actions/${action.id}/${choice}`, { method: 'POST' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Request failed')

      if (choice === 'cancel') {
        setStatus('cancelled')
        setMessage('Cancelled. Nothing was saved.')
      } else if (data.result?.error) {
        setStatus('error')
        setMessage(data.result.error)
      } else {
        setStatus('confirmed')
        setMessage(data.result?.title ? `Saved note "${data.result.title}".` : 'Done.')
      }
    } catch (err) {
      setStatus('error')
      setMessage(err.message || 'Unable to contact the agent.')
    }
  }

  return (
    <div className={`confirm-card confirm-${status}`}>
      <h3>Needs your confirmation</h3>
      <p>The agent wants to run <code>{action.tool}</code> with:</p>

      <dl className="confirm-args">
        {Object.entries(action.arguments || {}).map(([name, value]) => (
          <div key={name}>
            <dt>{name}</dt>
            <dd>{String(value)}</dd>
          </div>
        ))}
      </dl>

      {status === 'waiting' || status === 'working' ? (
        <div className="confirm-buttons">
          <button type="button" onClick={() => respond('confirm')} disabled={status === 'working'}>
            Confirm
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => respond('cancel')}
            disabled={status === 'working'}
          >
            Cancel
          </button>
        </div>
      ) : (
        <p className="confirm-outcome" role="status">{message}</p>
      )}
    </div>
  )
}

export default ConfirmCard
