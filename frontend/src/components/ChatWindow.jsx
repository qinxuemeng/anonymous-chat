import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, MoreVertical, Heart, Smile, Paperclip, X } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function ChatWindow() {
  const { userId } = useParams()
  const navigate = useNavigate()
  const { user: currentUser } = useAuth()
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const pollRef = useRef(null)
  const presencePollRef = useRef(null)

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [targetProfile, setTargetProfile] = useState(null)
  const [isTargetOnline, setIsTargetOnline] = useState(false)
  const [sendError, setSendError] = useState('')
  const [recallingId, setRecallingId] = useState('')
  const [user, setUser] = useState({
    id: userId,
    name: '神秘人',
    avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${userId}`,
  })

  const formatTime = (timeStr) => {
    const d = new Date(timeStr)
    if (Number.isNaN(d.getTime())) return ''
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  const loadChatHistory = async () => {
    if (!userId) return
    try {
      const res = await api.get('/chats/history', { params: { user_id: userId, page: 1, page_size: 100 } })
      if (!res.data?.success) return
      const list = res.data.data?.messages || []
      const ordered = [...list].reverse().map((msg) => ({
        id: msg.id,
        type: msg.type || 'text',
        content: msg.content,
        fromMe: msg.from_user_id === currentUser?.id,
        liked: !!msg.liked,
        read: !!msg.read,
        isRecalled: !!msg.is_recalled,
        time: formatTime(msg.created_at),
        isSystem: !!msg.is_system,
      }))
      setMessages(ordered)
    } catch (e) {
      console.error('load chat history failed', e)
    } finally {
      setLoading(false)
    }
  }

  const loadTargetProfile = async () => {
    if (!userId) return
    try {
      const res = await api.get(`/users/discover/${userId}`)
      if (res.data?.success) {
        const data = res.data.data
        setUser({
          id: data.id,
          name: data.nickname || '神秘人',
          avatar: data.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${data.id}`,
        })
        setTargetProfile(data)
      }
    } catch (e) {
      // 不是发现关系时回退到默认昵称
    }
  }

  const loadPresence = async () => {
    if (!userId) return
    try {
      const res = await api.get(`/chats/presence/${userId}`)
      if (res.data?.success) {
        setIsTargetOnline(!!res.data.data?.is_online)
      }
    } catch (e) {
      setIsTargetOnline(false)
    }
  }

  useEffect(() => {
    setLoading(true)
    loadTargetProfile()
    loadChatHistory()
    loadPresence()
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(loadChatHistory, 1000)
    if (presencePollRef.current) clearInterval(presencePollRef.current)
    presencePollRef.current = setInterval(loadPresence, 5000)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (presencePollRef.current) clearInterval(presencePollRef.current)
    }
  }, [userId, currentUser?.id])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (!sendError) return
    const t = setTimeout(() => setSendError(''), 2500)
    return () => clearTimeout(t)
  }, [sendError])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSend = (e) => {
    e.preventDefault()
    if (!input.trim() || sending) return
    sendMessage()
  }

  const sendMessage = async () => {
    const content = input.trim()
    if (!content) return
    setSending(true)
    setSendError('')
    try {
      const res = await api.post('/chats/message', {
        to_user_id: userId,
        type: 'text',
        content,
      })
      if (res.data?.success) {
        setInput('')
        await loadChatHistory()
        inputRef.current?.focus()
      }
    } catch (e) {
      console.error('send message failed', e)
      const status = e?.response?.status
      const rawError = e?.response?.data?.error || ''
      let msg = '消息发送失败，请稍后重试'
      if (status === 403 && rawError.includes('删除')) {
        msg = '已被对方删除，无法发送'
      } else if (rawError) {
        msg = String(rawError)
      }
      setSendError(msg)
    } finally {
      setSending(false)
    }
  }

  const toggleLike = (messageId) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId ? { ...msg, liked: !msg.liked } : msg
      )
    )
  }

  const recallMessage = async (messageId) => {
    if (!messageId || recallingId) return
    setRecallingId(messageId)
    setSendError('')
    try {
      const res = await api.post(`/chats/message/${messageId}/recall`)
      if (res.data?.success) {
        await loadChatHistory()
      }
    } catch (e) {
      const rawError = e?.response?.data?.error
      setSendError(rawError || '撤回失败，请稍后重试')
    } finally {
      setRecallingId('')
    }
  }

  const openProfileModal = async () => {
    try {
      const res = await api.get(`/users/discover/${userId}`)
      if (res.data?.success) {
        setTargetProfile(res.data.data)
      }
    } catch (e) {
      // 保留已有缓存信息
    } finally {
      setShowProfileModal(true)
    }
  }

  return (
    <div className="min-h-screen bg-neutral-100 dark:bg-neutral-900 flex flex-col">
      {sendError && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-red-500 text-white px-4 py-2 rounded-lg shadow">
          {sendError}
        </div>
      )}

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
              <button
                type="button"
                onClick={openProfileModal}
                className="font-medium text-neutral-900 dark:text-neutral-100 hover:text-primary-600"
              >
                {user.name}
              </button>
              <p className={`text-xs ${isTargetOnline ? 'text-green-500' : 'text-neutral-400'}`}>
                {isTargetOnline ? '在线' : '离线'}
              </p>
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
          {loading ? (
            <div className="text-center text-neutral-500">加载中...</div>
          ) : messages.length === 0 ? (
            <div className="text-center text-neutral-500">还没有聊天记录，打个招呼吧</div>
          ) : messages.map((message) => (
            message.isSystem ? (
              <div key={message.id} className="flex justify-center">
                <span className="text-xs px-2.5 py-1 rounded-full bg-neutral-200 text-neutral-500">
                  {message.content}
                </span>
              </div>
            ) : (
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
                  {message.fromMe && !message.isSystem && (
                    <span className="text-xs text-neutral-400">
                      {message.isRecalled ? '已撤回' : (message.read ? '已读' : '未读')}
                    </span>
                  )}
                  <span className="text-xs text-neutral-400">{message.time}</span>
                  {message.liked && <Heart className="w-3 h-3 text-red-500" />}
                  {message.fromMe && !message.isSystem && !message.isRecalled && (
                    <button
                      type="button"
                      disabled={recallingId === message.id}
                      onClick={() => recallMessage(message.id)}
                      className="ml-1 text-xs text-neutral-400 hover:text-red-500 disabled:opacity-60"
                    >
                      {recallingId === message.id ? '撤回中...' : '撤回'}
                    </button>
                  )}
                </div>
              </div>
            </div>
            )
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
              disabled={!input.trim() || sending}
              className="p-2 bg-primary-500 text-white rounded-full hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>
      </div>

      {/* 安全区域 */}
      <div className="h-4 bg-white dark:bg-neutral-800" />

      {showProfileModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md bg-white dark:bg-neutral-800 rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">个人资料</h3>
              <button
                type="button"
                onClick={() => setShowProfileModal(false)}
                className="p-1 rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-700"
              >
                <X className="w-5 h-5 text-neutral-500" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="flex items-center gap-4">
                <img
                  src={targetProfile?.avatar || user.avatar}
                  alt={targetProfile?.nickname || user.name}
                  className="w-16 h-16 rounded-xl object-cover bg-neutral-200 dark:bg-neutral-700"
                />
                <div>
                  <p className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
                    {targetProfile?.nickname || user.name}
                  </p>
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">
                    魅力值 {targetProfile?.charm_value ?? '-'}
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-neutral-100 dark:bg-neutral-700 rounded-lg px-3 py-2">
                  <p className="text-neutral-500">性别</p>
                  <p className="text-neutral-900 dark:text-neutral-100">{targetProfile?.gender || '保密'}</p>
                </div>
                <div className="bg-neutral-100 dark:bg-neutral-700 rounded-lg px-3 py-2">
                  <p className="text-neutral-500">年龄</p>
                  <p className="text-neutral-900 dark:text-neutral-100">{targetProfile?.age ?? '-'}</p>
                </div>
                <div className="bg-neutral-100 dark:bg-neutral-700 rounded-lg px-3 py-2 col-span-2">
                  <p className="text-neutral-500">城市</p>
                  <p className="text-neutral-900 dark:text-neutral-100">{targetProfile?.city || '未填写'}</p>
                </div>
              </div>
              <div>
                <p className="text-sm text-neutral-500 mb-2">标签</p>
                <div className="flex flex-wrap gap-2">
                  {(targetProfile?.tags || []).length === 0 ? (
                    <span className="text-sm text-neutral-400">暂无标签</span>
                  ) : (
                    (targetProfile?.tags || []).map((tag) => (
                      <span key={tag} className="px-2 py-1 rounded-full bg-sky-100 text-sky-600 text-xs">
                        {tag}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
