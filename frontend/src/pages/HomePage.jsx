import { useState, useEffect } from 'react'
import BottomNav from '../components/BottomNav'
import ChatCard from '../components/ChatCard'
import MatchCard from '../components/MatchCard'
import AnnouncementCarousel from '../components/AnnouncementCarousel'
import { Button } from '../components/ui/button'
import { Plus, Settings, Users, MessageSquare } from 'lucide-react'

export default function HomePage() {
  const [announcements, setAnnouncements] = useState([])
  const [currentMatch, setCurrentMatch] = useState(null)

  useEffect(() => {
    // 获取公告
    fetchAnnouncements()
  }, [])

  const fetchAnnouncements = async () => {
    try {
      const response = await fetch('/api/announcements')
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setAnnouncements(data.data.announcements.slice(0, 5))
        }
      }
    } catch (error) {
      console.error('获取公告失败:', error)
    }
  }

  const handlePickOnline = async () => {
    try {
      const response = await fetch('/api/match/online', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ type: 'online' })
      })
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setCurrentMatch(data.data)
        }
      }
    } catch (error) {
      console.error('捞个在线失败:', error)
    }
  }

  const handleRandomMatch = async () => {
    try {
      const response = await fetch('/api/match/random', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ type: 'random' })
      })
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setCurrentMatch(data.data)
        }
      }
    } catch (error) {
      console.error('随机匹配失败:', error)
    }
  }

  const handleThrowBottle = async () => {
    // 这里会导航到扔瓶子页面
  }

  const handlePickBottle = async () => {
    // 这里会导航到捞瓶子页面
  }

  return (
    <div className="min-h-screen bg-neutral-100 dark:bg-neutral-900 pb-20">
      {/* 顶部标题 */}
      <div className="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="max-w-md mx-auto px-4 py-3">
          <h1 className="text-xl font-semibold text-center text-neutral-900 dark:text-neutral-100">
            随便聊
          </h1>
        </div>
      </div>

      {/* 公告轮播区 */}
      {announcements.length > 0 && (
        <div className="px-4 py-4">
          <AnnouncementCarousel announcements={announcements} autoPlay interval={4000} />
        </div>
      )}

      {/* 快捷入口区 */}
      <div className="px-4 py-3">
        <div className="flex justify-between items-center">
          <div className="flex gap-3">
            <Button variant="outline" className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              陌生人设置
            </Button>
            <Button variant="outline" className="flex items-center gap-2">
              <Users className="w-4 h-4" />
              畅聊分区
            </Button>
          </div>
          <Button variant="outline" size="icon">
            <Plus className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* 核心功能卡片区 */}
      <div className="px-4 py-4">
        <h2 className="text-lg font-semibold mb-4 text-neutral-900 dark:text-neutral-100">
          遇见陌生人
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <MatchCard
            title="扔瓶子"
            description="发送漂流瓶"
            color="bg-gradient-to-br from-purple-400 to-purple-600"
            icon={Plus}
            onClick={handleThrowBottle}
          />
          <MatchCard
            title="捞个在线"
            description="随机捞一个在线的用户"
            color="bg-gradient-to-br from-orange-400 to-orange-600"
            icon={Users}
            onClick={handlePickOnline}
          />
          <MatchCard
            title="捞瓶子"
            description="捞取漂流瓶"
            color="bg-gradient-to-br from-teal-400 to-teal-600"
            icon={MessageSquare}
            onClick={handlePickBottle}
          />
          <MatchCard
            title="随机匹配"
            description="匹配一个正在匹配中的用户"
            color="bg-gradient-to-br from-blue-400 to-blue-600"
            icon={Users}
            onClick={handleRandomMatch}
          />
        </div>
      </div>

      {/* 最近聊天区 */}
      <div className="px-4 py-4">
        <h2 className="text-lg font-semibold mb-4 text-neutral-900 dark:text-neutral-100">
          最近聊天
        </h2>
        <div className="space-y-2">
          <ChatCard
            id="1"
            name="匿名用户"
            avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=1"
            message="你好，很高兴认识你！"
            time="2分钟前"
            unreadCount={2}
          />
          <ChatCard
            id="2"
            name="神秘人"
            avatar="https://api.dicebear.com/7.x/avataaars/svg?seed=2"
            message="今天天气不错..."
            time="1小时前"
          />
        </div>
      </div>

      {/* 底部导航 */}
      <BottomNav />
    </div>
  )
}
