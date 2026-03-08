import { Heart, Clock, MessageCircle, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function AnnouncementCard({ announcement }) {
  const navigate = useNavigate()

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 60) return `${diffMins}分钟前`
    if (diffHours < 24) return `${diffHours}小时前`
    if (diffDays < 7) return `${diffDays}天前`
    return date.toLocaleDateString('zh-CN')
  }

  return (
    <div className="bg-white dark:bg-neutral-800 rounded-xl overflow-hidden shadow-card">
      <div className="p-4">
        {/* 用户信息 */}
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-full overflow-hidden bg-neutral-200 dark:bg-neutral-700">
            {announcement.user.avatar ? (
              <img
                src={announcement.user.avatar}
                alt={announcement.user.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <User className="w-5 h-5 text-neutral-500" />
              </div>
            )}
          </div>
          <div className="flex-1">
            <h3 className="font-medium text-neutral-900 dark:text-neutral-100">
              {announcement.user.name}
            </h3>
            <div className="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
              <Clock className="w-3 h-3" />
              {formatDate(announcement.createdAt)}
            </div>
          </div>
        </div>

        {/* 内容 */}
        <p className="text-neutral-700 dark:text-neutral-300 text-sm mb-3 line-clamp-3">
          {announcement.content}
        </p>

        {/* 标签 */}
        {announcement.tags && announcement.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {announcement.tags.map((tag) => (
              <span
                key={tag}
                className="px-2 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-xs rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* 底部操作 */}
        <div className="flex items-center justify-between pt-3 border-t border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 text-neutral-500 dark:text-neutral-400">
              <Heart className="w-4 h-4" />
              <span className="text-sm">{announcement.views}</span>
            </div>
            <div className="flex items-center gap-1 text-neutral-500 dark:text-neutral-400">
              <MessageCircle className="w-4 h-4" />
              <span className="text-sm">0</span>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              className="px-4 py-1.5 text-sm border border-orange-500 text-orange-500 rounded-lg hover:bg-orange-50 dark:hover:bg-orange-900/20 transition-colors"
              onClick={() => console.log('认领', announcement.id)}
            >
              认领
            </button>
            <button
              className="px-4 py-1.5 text-sm bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
              onClick={() => console.log('发布', announcement.id)}
            >
              发布
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
