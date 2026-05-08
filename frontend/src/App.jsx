import { useState, useRef, useEffect } from 'react'
import ChatWindow from './components/ChatWindow'
import InputBar from './components/InputBar'
import Sidebar from './components/Sidebar'
import './App.css'

function initSessions() {
  try {
    const stored = JSON.parse(localStorage.getItem('nusadvisor_sessions') || '[]')
    if (stored.length > 0) return stored
    // Migrate from old single-session format
    const oldId = localStorage.getItem('nusadvisor_session_id')
    const id = oldId || crypto.randomUUID()
    const session = { id, title: 'New Chat', createdAt: new Date().toISOString() }
    localStorage.setItem('nusadvisor_sessions', JSON.stringify([session]))
    return [session]
  } catch {
    const session = { id: crypto.randomUUID(), title: 'New Chat', createdAt: new Date().toISOString() }
    localStorage.setItem('nusadvisor_sessions', JSON.stringify([session]))
    return [session]
  }
}

function initActiveSession(sessions) {
  const active = localStorage.getItem('nusadvisor_active_session')
  if (active && sessions.find(s => s.id === active)) return active
  localStorage.setItem('nusadvisor_active_session', sessions[0].id)
  return sessions[0].id
}

function App() {
  const [sessions, setSessions] = useState(initSessions)
  const [sessionId, setSessionId] = useState(() => initActiveSession(initSessions()))
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const messagesEndRef = useRef(null)

  const saveSessions = (updated) => {
    setSessions(updated)
    localStorage.setItem('nusadvisor_sessions', JSON.stringify(updated))
  }

  const newChat = () => {
    const id = crypto.randomUUID()
    const session = { id, title: 'New Chat', createdAt: new Date().toISOString() }
    saveSessions([session, ...sessions])
    localStorage.setItem('nusadvisor_active_session', id)
    setSessionId(id)
    setMessages([])
    setHistoryLoaded(true)
  }

  const switchSession = (id) => {
    if (id === sessionId) return
    localStorage.setItem('nusadvisor_active_session', id)
    setSessionId(id)
    setMessages([])
    setHistoryLoaded(false)
  }

  useEffect(() => {
    setHistoryLoaded(false)
    fetch(`/api/history?session_id=${sessionId}`)
      .then(r => r.json())
      .then(data => { if (data.messages?.length) setMessages(data.messages) })
      .catch(() => {})
      .finally(() => setHistoryLoaded(true))
  }, [sessionId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    if (!text.trim()) return

    const isFirstMessage = messages.length === 0
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)
    setMessages(prev => [...prev, { role: 'assistant', content: 'Thinking...', isThinking: true }])

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId, is_first_message: isFirstMessage })
      })

      if (!response.ok) throw new Error('API error')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let firstToken = true

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const lines = decoder.decode(value).split('\n\n')
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6)
          if (raw === '[DONE]') break
          let data
          try { data = JSON.parse(raw) } catch { continue }
          if (data.title) {
            setSessions(prev => {
              const updated = prev.map(s => s.id === sessionId ? { ...s, title: data.title } : s)
              localStorage.setItem('nusadvisor_sessions', JSON.stringify(updated))
              return updated
            })
          } else if (data.token) {
            if (firstToken) {
              setMessages(prev => [...prev.filter(m => !m.isThinking), { role: 'assistant', content: data.token }])
              firstToken = false
            } else {
              setMessages(prev => {
                const msgs = [...prev]
                msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: msgs[msgs.length - 1].content + data.token }
                return msgs
              })
            }
          }
        }
      }
    } catch (err) {
      console.error(err)
      setMessages(prev => [...prev.filter(m => !m.isThinking), {
        role: 'assistant',
        content: '❌ Error: Could not connect to the advisor. Is the backend running?'
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        activeSessionId={sessionId}
        onNewChat={newChat}
        onSwitchSession={switchSession}
      />
      <div className="chat-area">
        <ChatWindow messages={messages} messagesEndRef={messagesEndRef} />

        {historyLoaded && messages.length === 0 && (
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
    </div>
  )
}

export default App
