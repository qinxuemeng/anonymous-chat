import { useLocation, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Compass, MessageSquare, Settings } from 'lucide-react'
import { api } from '../services/api'

const navItems = [
  {
    id: 'discover',
    path: '/discover',
    label: '发现',
    icon: Compass,
  },
  {
    id: 'chat',
    path: '/chat',
    label: '对话',
    icon: MessageSquare,
  },
  {
    id: 'settings',
    path: '/settings',
    label: '设置',
    icon: Settings,
  },
]

export default function BottomNav() {
  const location = useLocation()
  const [unreadCount, setUnreadCount] = useState(0)

  const isActive = (path) => location.pathname.startsWith(path)

  const loadUnreadCount = async () => {
    try {
      const res = await api.get('/chats/unread/count')
      if (res.data?.success) {
        setUnreadCount(Number(res.data.data?.unread_count || 0))
      }
    } catch (e) {
      // 忽略失败，避免影响导航渲染
    }
  }

  useEffect(() => {
    loadUnreadCount()
    const timer = setInterval(loadUnreadCount, 5000)
    return () => clearInterval(timer)
  }, [])

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700 z-50">
      <div className="flex justify-around items-center h-16">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.path)
          return (
            <Link
              key={item.id}
              to={item.path}
              className="flex flex-col items-center justify-center w-full h-full transition-all"
            >
              <div className="relative">
                <Icon
                  className={`w-6 h-6 transition-colors ${
                    active
                      ? 'text-primary-500'
                      : 'text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300'
                  }`}
                  strokeWidth={active ? 2.5 : 2}
                />
                {item.id === 'chat' && unreadCount > 0 && (
                  <span className="absolute -top-2 -right-2 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] leading-[18px] text-center font-semibold">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </div>
              <span
                className={`text-xs mt-1 transition-colors ${
                  active
                    ? 'text-primary-500 font-medium'
                    : 'text-neutral-400'
                }`}
              >
                {item.label}
              </span>
            </Link>
          )
        })}
      </div>
      {/* 安全区域 (iPhone) */}
      <div className="h-0 bg-white dark:bg-neutral-800" />
    </nav>
  )
}
