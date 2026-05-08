import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './Message.css'

export default function Message({ message }) {
  const isUser = message.role === 'user'
  const isThinking = message.isThinking

  return (
    <div className={`message ${isUser ? 'user-message' : 'assistant-message'}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🎓'}
      </div>
      <div className={`message-content ${isThinking ? 'thinking' : ''}`}>
        {isUser ? (
          <p>{message.content}</p>
        ) : isThinking ? (
          <span className="thinking-dots">Thinking<span></span><span></span><span></span></span>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        )}
      </div>
    </div>
  )
}
