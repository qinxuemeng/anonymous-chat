import { useState, useEffect } from 'react'
import BottomNav from '../components/BottomNav'
import ChatCard from '../components/ChatCard'
import { Search } from 'lucide-react'
import { api } from '../services/api'

export default function ChatPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [chats, setChats] = useState([])
  const [loading, setLoading] = useState(true)

  const formatTime = (timeStr) => {
    if (!timeStr) return ''
    const d = new Date(timeStr)
    if (Number.isNaN(d.getTime())) return ''
    const now = new Date()
    const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000)
    if (diffSec < 60) return '刚刚'
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}分钟前`
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}小时前`
    return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  }

  const loadConversations = async () => {
    try {
      const response = await api.get('/chats/conversations')
      if (response.data?.success) {
        const list = response.data.data?.conversations || []
        setChats(list.map((item) => ({
          id: item.user_id,
          name: item.nickname || '神秘人',
          avatar: item.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${item.user_id}`,
          message: item.last_message || '',
          time: formatTime(item.last_message_at),
          unreadCount: item.unread_count || 0,
          isOnline: !!item.is_online,
        })))
      }
    } catch (error) {
      console.error('获取会话列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConversations()
    const timer = setInterval(loadConversations, 5000)
    return () => clearInterval(timer)
  }, [])

  const filteredChats = chats.filter((chat) =>
    chat.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleDeleteConversation = async (targetUserId, name) => {
    const ok = window.confirm(`确定删除与 ${name || '该用户'} 的会话吗？`)
    if (!ok) return
    try {
      await api.delete(`/chats/conversation/${targetUserId}`)
      setChats((prev) => prev.filter((chat) => chat.id !== targetUserId))
    } catch (error) {
      console.error('删除会话失败:', error)
      window.alert('删除会话失败，请稍后重试')
    }
  }

  return (
    <div className="min-h-screen bg-neutral-100 dark:bg-neutral-900 pb-20">
      {/* 顶部标题 */}
      <div className="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="max-w-md mx-auto px-4 py-3">
          <h1 className="text-xl font-semibold text-center text-neutral-900 dark:text-neutral-100">
            对话
          </h1>
        </div>
      </div>

      {/* 搜索栏 */}
      <div className="px-4 py-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
          <input
            type="text"
            placeholder="搜索对话..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {/* 聊天列表 */}
      <div className="px-4">
        {loading ? (
          <div className="text-center py-16 text-neutral-500 dark:text-neutral-400">
            加载中...
          </div>
        ) : filteredChats.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-neutral-400 mb-2">
              <svg className="w-16 h-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-neutral-500 dark:text-neutral-400">
              {searchQuery ? '未找到匹配的对话' : '还没有对话记录'}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredChats.map((chat) => (
              <ChatCard
                key={chat.id}
                id={chat.id}
                name={chat.name}
                avatar={chat.avatar}
                message={chat.message}
                time={chat.time}
                unreadCount={chat.unreadCount}
                onDelete={handleDeleteConversation}
                isOnline={chat.isOnline}
              />
            ))}
          </div>
        )}
      </div>

      {/* 底部导航 */}
      <BottomNav />
    </div>
  )
}
