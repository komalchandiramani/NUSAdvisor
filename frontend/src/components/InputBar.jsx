import { useState } from 'react'
import './InputBar.css'

export default function InputBar({ onSend, disabled }) {
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (input.trim()) {
      onSend(input)
      setInput('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="input-bar">
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask me about your academic path... (Enter to send, Shift+Enter for newline)"
        disabled={disabled}
        rows="2"
      />
      <button onClick={handleSend} disabled={disabled || !input.trim()}>
        {disabled ? '⏳' : '→'}
      </button>
    </div>
  )
}
