import Message from './Message'
import './ChatWindow.css'

export default function ChatWindow({ messages, messagesEndRef }) {
  return (
    <div className="chat-window">
      {messages.length === 0 && (
        <div className="empty-state">
          <h2>Welcome to NUSAdvisor+</h2>
          <p>Ask me anything about your academic path</p>
        </div>
      )}
      {messages.map((msg, idx) => (
        <Message key={idx} message={msg} />
      ))}
      <div ref={messagesEndRef} />
    </div>
  )
}
