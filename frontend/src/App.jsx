import { useState, useRef, useEffect } from 'react'
import ChatWindow from './components/ChatWindow'
import InputBar from './components/InputBar'
import './App.css'

function App() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async (text) => {
    if (!text.trim()) return

    const userMessage = { role: 'user', content: text }
    setMessages(prev => [...prev, userMessage])
    setLoading(true)

    // Add thinking message
    setMessages(prev => [...prev, { role: 'assistant', content: 'Thinking...', isThinking: true }])

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: messages
        })
      })

      if (!response.ok) throw new Error('API error')
      const data = await response.json()

      // Remove thinking message and add actual response
      setMessages(prev => {
        const withoutThinking = prev.filter(m => !m.isThinking)
        return [...withoutThinking, {
          role: 'assistant',
          content: data.response
        }]
      })
    } catch (err) {
      console.error(err)
      setMessages(prev => {
        const withoutThinking = prev.filter(m => !m.isThinking)
        return [...withoutThinking, {
          role: 'assistant',
          content: '❌ Error: Could not connect to the advisor. Is the backend running?'
        }]
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎓 NUSAdvisor+</h1>
        <p>AI-powered academic planning for your career goals</p>
      </header>

      <ChatWindow messages={messages} messagesEndRef={messagesEndRef} />

      {messages.length === 0 && (
        <div className="starter-prompts">
          <h2>Get started with a question:</h2>
          <div className="prompts-grid">
            <button onClick={() => sendMessage("I want to become a Data Scientist. What courses should I take?")}>
              <div className="card-title">Data Scientist</div>
              <div className="card-subtitle">Computing</div>
            </button>
            <button onClick={() => sendMessage("I want to become a Finance Specialist. What courses should I take?")}>
              <div className="card-title">Finance Specialist</div>
              <div className="card-subtitle">Business</div>
            </button>
            <button onClick={() => sendMessage("I want to become a Medical Professional. What courses should I take?")}>
              <div className="card-title">Medical Professional</div>
              <div className="card-subtitle">Health</div>
            </button>
            <button onClick={() => sendMessage("I want to become a Digital Marketing Specialist. What courses should I take?")}>
              <div className="card-title">Digital Marketing Specialist</div>
              <div className="card-subtitle">Marketing</div>
            </button>
          </div>
        </div>
      )}

      <InputBar onSend={sendMessage} disabled={loading} />
    </div>
  )
}

export default App
