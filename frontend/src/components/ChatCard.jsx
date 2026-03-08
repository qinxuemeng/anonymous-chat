import { useNavigate } from 'react-router-dom'
import { Trash2 } from 'lucide-react'

export default function ChatCard({ id, name, avatar, message, time, unreadCount, onDelete, isOnline }) {
  const navigate = useNavigate()

  return (
    <div
      onClick={() => navigate(`/chat/${id}`)}
      className={`rounded-xl p-4 flex items-center gap-3 cursor-pointer hover:shadow-card transition-all ${
        isOnline
          ? 'bg-white dark:bg-neutral-800 ring-1 ring-emerald-200/70'
          : 'bg-white/70 dark:bg-neutral-800/70 opacity-70'
      }`}
    >
      <div className="relative">
        <img
          src={avatar}
          alt={name}
          className="w-12 h-12 rounded-full object-cover bg-neutral-200 dark:bg-neutral-700"
        />
        <span
          className={`absolute -right-0.5 -bottom-0.5 w-3 h-3 rounded-full border-2 border-white dark:border-neutral-800 ${
            isOnline ? 'bg-emerald-500' : 'bg-neutral-400'
          }`}
        />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-start">
          <h3 className="font-medium text-neutral-900 dark:text-neutral-100 truncate">
            {name}
          </h3>
          <span className="text-xs text-neutral-500 dark:text-neutral-400 ml-2 whitespace-nowrap">
            {time}
          </span>
        </div>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 truncate mt-1">
          {message}
        </p>
      </div>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          onDelete?.(id, name)
        }}
        className="p-2 rounded-full text-neutral-400 hover:text-red-500 hover:bg-neutral-100 dark:hover:bg-neutral-700"
        title="删除会话"
      >
        <Trash2 className="w-4 h-4" />
      </button>
      {unreadCount > 0 && (
        <div className="flex-shrink-0">
          <span className="inline-flex items-center justify-center w-5 h-5 bg-red-500 text-white text-xs font-medium rounded-full">
            {unreadCount}
          </span>
        </div>
      )}
    </div>
  )
}
