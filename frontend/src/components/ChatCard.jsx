import { useNavigate } from 'react-router-dom'

export default function ChatCard({ id, name, avatar, message, time, unreadCount }) {
  const navigate = useNavigate()

  return (
    <div
      onClick={() => navigate(`/chat/${id}`)}
      className="bg-white dark:bg-neutral-800 rounded-xl p-4 flex items-center gap-3 cursor-pointer hover:shadow-card transition-shadow"
    >
      <div className="relative">
        <img
          src={avatar}
          alt={name}
          className="w-12 h-12 rounded-full object-cover bg-neutral-200 dark:bg-neutral-700"
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
