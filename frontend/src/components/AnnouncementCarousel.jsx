import { useState, useEffect } from 'react'

export default function AnnouncementCarousel({ announcements, autoPlay = true, interval = 5000 }) {
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    if (!autoPlay || announcements.length <= 1) return

    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % announcements.length)
    }, interval)

    return () => clearInterval(timer)
  }, [autoPlay, interval, announcements.length])

  const goToSlide = (index) => {
    setCurrentIndex(index)
  }

  if (announcements.length === 0) return null

  return (
    <div className="relative bg-white dark:bg-neutral-800 rounded-xl overflow-hidden shadow-card">
      {/* 轮播内容 */}
      <div className="relative h-24">
        {announcements.map((announcement, index) => (
          <div
            key={announcement.id}
            className={`absolute inset-0 transition-opacity duration-300 ${
              index === currentIndex ? 'opacity-100' : 'opacity-0 pointer-events-none'
            }`}
          >
            <div className="p-4">
              <h3 className="font-medium text-neutral-900 dark:text-neutral-100 line-clamp-1">
                {announcement.nickname}
              </h3>
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1 line-clamp-2">
                {announcement.content}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* 轮播指示器 */}
      {announcements.length > 1 && (
        <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2 flex gap-1.5">
          {announcements.map((_, index) => (
            <button
              key={index}
              onClick={() => goToSlide(index)}
              className={`w-2 h-2 rounded-full transition-all ${
                index === currentIndex
                  ? 'bg-primary-500 w-6'
                  : 'bg-neutral-300 dark:bg-neutral-600'
              }`}
              aria-label={`跳转到第 ${index + 1} 页`}
            />
          ))}
        </div>
      )}

      {/* 操作按钮 */}
      <div className="absolute right-2 bottom-2 flex gap-2">
        <button
          className="px-2 py-1 text-xs bg-white/80 dark:bg-neutral-700/80 rounded border border-neutral-200 dark:border-neutral-600"
          onClick={() => {
            // 认领功能
            console.log('认领', announcements[currentIndex])
          }}
        >
          认领
        </button>
        <button
          className="px-2 py-1 text-xs bg-orange-500 text-white rounded"
          onClick={() => {
            // 发布公告
            console.log('发布公告')
          }}
        >
          发布
        </button>
      </div>
    </div>
  )
}
