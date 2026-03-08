import { useLocation, Link } from 'react-router-dom'
import { Compass, UserRound, MessageSquare, Settings } from 'lucide-react'

const navItems = [
  {
    id: 'discover',
    path: '/discover',
    label: '发现',
    icon: Compass,
  },
  {
    id: 'home',
    path: '/',
    label: '遇见',
    icon: UserRound,
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

  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }

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
              <Icon
                className={`w-6 h-6 transition-colors ${
                  active
                    ? 'text-primary-500'
                    : 'text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300'
                }`}
                strokeWidth={active ? 2.5 : 2}
              />
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
