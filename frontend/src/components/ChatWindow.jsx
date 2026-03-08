import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import BottomNav from '../components/BottomNav'
import { ArrowLeft, Send, MoreVertical, Heart, Smile, Paperclip } from 'lucide-react'

export default function ChatWindow() {
  const { userId } = useParams()
  const navigate = useNavigate()
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [user, setUser] = useState({
    id: userId,
    name: '神秘人',
    avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${userId}`,
  })

  // 模拟数据
  const mockMessages = [
    {
      id: '1',
      type: 'text',
      content: '你好！很高兴认识你',
      fromMe: false,
      liked: false,
      time: '14:30',
    },
    {
      id: '2',
      type: 'text',
      content: '你好！我也很高兴认识你',
      fromMe: true,
      liked: false,
      time: '14:31',
    },
  ]

  useEffect(() => {
    setMessages(mockMessages)
    scrollToBottom()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSend = (e) => {
    e.preventDefault()
    if (!input.trim()) return

    const newMessage = {
      id: String(messages.length + 1),
      type: 'text',
      content: input,
      fromMe: true,
      liked: false,
      time: new Date().toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      }),
    }

    setMessages((prev) => [...prev, newMessage])
    setInput('')
    inputRef.current?.focus()
  }

  const toggleLike = (messageId) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId ? { ...msg, liked: !msg.liked } : msg
      )
    )
  }

  return (
    <div className="min-h-screen bg-neutral-100 dark:bg-neutral-900 flex flex-col">
      {/* 顶部导航 */}
      <div className="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/chat')}
              className="p-1.5 -ml-1.5 rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-700"
            >
              <ArrowLeft className="w-6 h-6 text-neutral-700 dark:text-neutral-300" />
            </button>
            <img
              src={user.avatar}
              alt={user.name}
              className="w-10 h-10 rounded-full"
            />
            <div>
              <h2 className="font-medium text-neutral-900 dark:text-neutral-100">{user.name}</h2>
              <p className="text-xs text-green-500">在线</p>
            </div>
          </div>
          <button className="p-2 rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-700">
            <MoreVertical className="w-5 h-5 text-neutral-500 dark:text-neutral-400" />
          </button>
        </div>
      </div>

      {/* 聊天内容 */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-md mx-auto space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.fromMe ? 'justify-end' : 'justify-start'}`}
            >
              {!message.fromMe && (
                <img
                  src={user.avatar}
                  alt=""
                  className="w-8 h-8 rounded-full self-end mr-2"
                />
              )}
              <div
                className="max-w-[75%] relative group"
              >
                <div
                  className={`px-4 py-2.5 rounded-2xl ${
                    message.fromMe
                      ? 'bg-primary-500 text-white rounded-br-sm'
                      : 'bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 rounded-bl-sm'
                  }`}
                >
                  {message.type === 'text' && (
                    <p className="text-sm">{message.content}</p>
                  )}
                </div>
                <div
                  className={`flex items-center gap-1 mt-1 ${message.fromMe ? 'justify-end' : 'justify-start'} px-1`}
                >
                  <span className="text-xs text-neutral-400">{message.time}</span>
                  {message.liked && <Heart className="w-3 h-3 text-red-500" />}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 底部输入栏 */}
      <div className="bg-white dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700 px-4 py-3">
        <form onSubmit={handleSend} className="max-w-md mx-auto">
          <div className="flex items-end gap-2">
            <button
              type="button"
              className="p-2 rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-700"
            >
              <Paperclip className="w-6 h-6 text-neutral-500 dark:text-neutral-400" />
            </button>
            <div className="flex-1 bg-neutral-100 dark:bg-neutral-700 rounded-full px-4 py-2.5 flex items-center">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="输入消息..."
                className="flex-1 bg-transparent border-0 outline-none text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400"
              />
              <button
                type="button"
                className="p-1 rounded-full hover:bg-neutral-200 dark:hover:bg-neutral-600"
              >
                <Smile className="w-5 h-5 text-neutral-500 dark:text-neutral-400" />
              </button>
            </div>
            <button
              type="submit"
              disabled={!input.trim()}
              className="p-2 bg-primary-500 text-white rounded-full hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>
      </div>

      {/* 安全区域 */}
      <div className="h-4 bg-white dark:bg-neutral-800" />
    </div>
  )
}
