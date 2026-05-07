import './Sidebar.css'

export default function Sidebar({ sessions, activeSessionId, onNewChat, onSwitchSession }) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-logo">🎓 NUSAdvisor+</span>
        <button className="new-chat-btn" onClick={onNewChat}>+ New Chat</button>
      </div>
      <div className="session-list">
        {sessions.map(session => (
          <div
            key={session.id}
            className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}
            onClick={() => onSwitchSession(session.id)}
          >
            <div className="session-title">{session.title}</div>
            <div className="session-date">
              {new Date(session.createdAt).toLocaleDateString('en-SG', { month: 'short', day: 'numeric' })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
