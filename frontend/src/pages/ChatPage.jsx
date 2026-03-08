import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import BottomNav from '../components/BottomNav'
import ChatCard from '../components/ChatCard'
import { Search } from 'lucide-react'

export default function ChatPage() {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [chats, setChats] = useState([])

  // 模拟数据
  const mockChats = [
    {
      id: '1',
      name: '神秘人',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=1',
      message: '你好！很高兴认识你',
      time: '5分钟前',
      unreadCount: 2,
    },
    {
      id: '2',
      name: '匿名用户',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=2',
      message: '今天天气真不错呢',
      time: '1小时前',
      unreadCount: 0,
    },
    {
      id: '3',
      name: '过客',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=3',
      message: '好的，下次再聊',
      time: '昨天',
      unreadCount: 0,
    },
  ]

  useEffect(() => {
    // 这里应该从API获取聊天列表
    setChats(mockChats)
  }, [])

  const filteredChats = chats.filter((chat) =>
    chat.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

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
        {filteredChats.length === 0 ? (
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
