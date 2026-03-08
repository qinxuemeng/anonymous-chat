import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import BottomNav from '../components/BottomNav'
import AnnouncementCarousel from '../components/AnnouncementCarousel'
import MatchCard from '../components/MatchCard'
import { Users, Settings, X, Loader2, Clock, User, MessageCircle } from 'lucide-react'
import { api } from '../services/api'

export default function DiscoverPage() {
  const navigate = useNavigate()
  const [announcements, setAnnouncements] = useState([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [modalType, setModalType] = useState(null)
  const [bottleContent, setBottleContent] = useState('')
  const [pickedBottle, setPickedBottle] = useState(null)
  const [onlineUser, setOnlineUser] = useState(null)
  const [isLoadingAction, setIsLoadingAction] = useState(false)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('info')

  // 匹配相关状态
  const [isMatching, setIsMatching] = useState(false)
  const [matchingTime, setMatchingTime] = useState(0)
  const [matchedUser, setMatchedUser] = useState(null)
  const [showMatchResult, setShowMatchResult] = useState(false)
  const matchingTimerRef = useRef(null)
  const pollTimerRef = useRef(null)
  const currentMatchIdRef = useRef(null)

  useEffect(() => {
    const fetchAnnouncements = async () => {
      try {
        const response = await api.get('/announcements', {
          params: { page: 1, page_size: 5 }
        })
        if (response.data.success) {
          setAnnouncements(response.data.data.announcements || [])
        }
      } catch (error) {
        console.error('获取公告失败:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAnnouncements()
  }, [])

  // 清理定时器
  useEffect(() => {
    return () => {
      if (matchingTimerRef.current) {
        clearInterval(matchingTimerRef.current)
      }
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [])

  const showMessage = (msg, type = 'info') => {
    setMessage(msg)
    setMessageType(type)
    setTimeout(() => setMessage(''), 3000)
  }

  // 开始匹配
  const startMatching = async () => {
    try {
      if (matchingTimerRef.current) {
        clearInterval(matchingTimerRef.current)
      }
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
      setIsMatching(true)
      setMatchingTime(0)
      setMatchedUser(null)
      setShowMatchResult(false)
      setIsLoadingAction(true)

      const response = await api.post('/match/random', { type: 'random' })
      if (response.data.success) {
        const data = response.data.data
        currentMatchIdRef.current = data.match_id

        if (data.status === 'matched') {
          // 直接匹配成功
          await fetchMatchedUser(data.matched_user_id)
        } else {
          setIsLoadingAction(false)
          // 开始等待匹配
          startMatchingTimer()
          startPolling(data.match_id)
        }
      }
    } catch (error) {
      setIsMatching(false)
      setIsLoadingAction(false)
      showMessage(error.response?.data?.error || '匹配失败，请稍后重试', 'error')
    }
  }

  // 匹配计时器
  const startMatchingTimer = () => {
    matchingTimerRef.current = setInterval(() => {
      setMatchingTime(prev => {
        if (prev >= 30) {
          stopMatching()
          return prev
        }
        return prev + 1
      })
    }, 1000)
  }

  // 轮询匹配状态
  const startPolling = (matchId) => {
    pollTimerRef.current = setInterval(async () => {
      try {
        const response = await api.get(`/match/status/${matchId}`)
        if (response.data.success) {
          const data = response.data.data
          if (data.status === 'matched' && data.matched_user_id) {
            await fetchMatchedUser(data.matched_user_id)
          }
        }
      } catch (error) {
        console.error('Polling error:', error)
      }
    }, 2000)
  }

  // 获取匹配用户信息
  const fetchMatchedUser = async (userId) => {
    try {
      await stopMatching(false)
      setIsLoadingAction(true)
      const response = await api.get(`/users/discover/${userId}`)
      if (!response.data.success) {
        throw new Error('获取用户信息失败')
      }
      const data = response.data.data
      setMatchedUser({
        id: data.id,
        nickname: data.nickname || '匿名用户',
        avatar: data.avatar || '',
        charm_value: data.charm_value ?? 0,
        gender: data.gender || '保密',
        age: data.age ?? '-',
        city: data.city || '',
        tags: Array.isArray(data.tags) ? data.tags : []
      })
      setShowMatchResult(true)
      setIsLoadingAction(false)
    } catch (error) {
      await stopMatching(false)
      setIsLoadingAction(false)
      showMessage(error.response?.data?.error || '获取用户信息失败', 'error')
    }
  }

  // 停止匹配
  const stopMatching = async (shouldCancel = true) => {
    if (matchingTimerRef.current) {
      clearInterval(matchingTimerRef.current)
      matchingTimerRef.current = null
    }
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }

    if (shouldCancel && currentMatchIdRef.current && isMatching && !matchedUser) {
      try {
        await api.post('/match/cancel', { match_id: currentMatchIdRef.current })
      } catch (error) {
        console.error('Cancel match error:', error)
      }
    }

    setIsMatching(false)
    setMatchingTime(0)
    currentMatchIdRef.current = null
  }

  // 开始聊天
  const startChat = () => {
    if (matchedUser) {
      navigate(`/chat/${matchedUser.id}`)
    }
  }

  // 关闭匹配结果
  const closeMatchResult = () => {
    setShowMatchResult(false)
    setMatchedUser(null)
  }

  const handleRandomMatch = async () => {
    await startMatching()
  }

  const handlePickOnline = async () => {
    try {
      setIsLoadingAction(true)
      const response = await api.post('/match/online', { type: 'online' })
      if (response.data.success) {
        const data = response.data.data
        const detailResp = await api.get(`/users/discover/${data.user_id}`)
        const detail = detailResp.data?.data || {}
        setOnlineUser({
          id: data.user_id,
          nickname: detail.nickname || data.nickname || '匿名用户',
          avatar: detail.avatar || data.avatar || '',
          charm_value: detail.charm_value ?? data.charm_value ?? 0,
          gender: detail.gender || '保密',
          age: detail.age ?? '-',
          city: detail.city || '',
          tags: Array.isArray(detail.tags) ? detail.tags : []
        })
        setModalType('online')
        setIsModalOpen(true)
      }
    } catch (error) {
      showMessage(error.response?.data?.error || '捞取失败，请稍后重试', 'error')
    } finally {
      setIsLoadingAction(false)
    }
  }

  const openThrowBottleModal = () => {
    setModalType('throw')
    setBottleContent('')
    setIsModalOpen(true)
  }

  const handleThrowBottle = async () => {
    if (!bottleContent.trim()) {
      showMessage('请输入瓶子内容', 'error')
      return
    }
    try {
      setIsLoadingAction(true)
      const response = await api.post('/bottles/throw', {
        content: bottleContent,
        images: []
      })
      if (response.data.success) {
        showMessage('瓶子已投入大海！', 'success')
        setIsModalOpen(false)
      }
    } catch (error) {
      showMessage(error.response?.data?.error || '扔瓶子失败，请稍后重试', 'error')
    } finally {
      setIsLoadingAction(false)
    }
  }

  const handlePickBottle = async () => {
    try {
      setIsLoadingAction(true)
      const response = await api.post('/bottles/pick')
      if (response.data.success) {
        const data = response.data.data
        const genderMap = { male: '男', female: '女', secret: '保密' }
        setPickedBottle({
          bottle_id: data.bottle_id,
          content: data.content,
          author_id: data.author_id || null,
          author_nickname: data.author_nickname || '匿名',
          author_gender: genderMap[data.author_gender] || '保密',
          created_at: data.created_at
        })
        setModalType('pickedBottle')
        setIsModalOpen(true)
      }
    } catch (error) {
      showMessage(error.response?.data?.error || '捞瓶子失败，请稍后重试', 'error')
    } finally {
      setIsLoadingAction(false)
    }
  }

  const handleChatPickedBottle = () => {
    if (!pickedBottle?.author_id) {
      showMessage('该瓶子暂不支持发起聊天', 'error')
      return
    }
    setIsModalOpen(false)
    navigate(`/chat/${pickedBottle.author_id}`)
  }

  const handleReportBottle = () => {
    showMessage('举报已受理，我们会尽快审核', 'success')
    setIsModalOpen(false)
  }

  const handleChatOnlineUser = () => {
    if (!onlineUser?.id) {
      return
    }
    setIsModalOpen(false)
    navigate(`/chat/${onlineUser.id}`)
  }

  const handleNextOnlineUser = async () => {
    await handlePickOnline()
  }

  const formatBottleTime = (timeStr) => {
    if (!timeStr) return ''
    const d = new Date(timeStr)
    if (Number.isNaN(d.getTime())) return ''
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const hour = String(d.getHours()).padStart(2, '0')
    const minute = String(d.getMinutes()).padStart(2, '0')
    return `${month}月${day}日 ${hour}:${minute}`
  }

  return (
    <div className="min-h-screen bg-neutral-100 dark:bg-neutral-900 pb-20">
      {/* 消息提示 */}
      {message && (
        <div className={`fixed top-4 left-1/2 transform -translate-x-1/2 z-50 px-4 py-3 rounded-lg shadow-lg ${
          messageType === 'success' ? 'bg-green-500 text-white' :
          messageType === 'error' ? 'bg-red-500 text-white' :
          'bg-blue-500 text-white'
        }`}>
          {message}
        </div>
      )}

      {/* 匹配中遮罩 */}
      {isMatching && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-40">
          <div className="bg-white dark:bg-neutral-800 rounded-2xl w-full max-w-sm p-6 mx-4">
            <div className="text-center">
              <div className="flex justify-center mb-4">
                <div className="relative">
                  <Loader2 className="w-16 h-16 text-gray-500 animate-spin" />
                </div>
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                匹配中
              </h3>
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
                清空私聊，将删除所有未收藏的私聊，已收藏的私聊需要手动删除
              </p>
              <div className="flex items-center justify-center gap-2 text-neutral-600 dark:text-neutral-400">
                <Clock className="w-4 h-4" />
                <span>{matchingTime} / 30 秒</span>
              </div>
              <div className="mt-4 h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gray-500 transition-all duration-300"
                  style={{ width: `${(matchingTime / 30) * 100}%` }}
                />
              </div>
              <button
                onClick={stopMatching}
                className="mt-6 w-full px-4 py-2 border border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-300 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
              >
                取消匹配
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 匹配结果 */}
      {showMatchResult && matchedUser && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-40">
          <div className="bg-white dark:bg-neutral-800 rounded-2xl w-full max-w-sm p-6 mx-4">
            <div className="text-center">
              {/* 头像和昵称 */}
              <div className="flex flex-col items-center mb-4">
                {matchedUser.avatar ? (
                  <img
                    src={matchedUser.avatar}
                    alt={matchedUser.nickname}
                    className="w-24 h-24 rounded-full border-4 border-neutral-200 dark:border-neutral-700 mb-3"
                  />
                ) : (
                  <div className="w-24 h-24 rounded-full bg-neutral-200 dark:bg-neutral-700 flex items-center justify-center border-4 border-neutral-200 dark:border-neutral-700 mb-3">
                    <User className="w-12 h-12 text-neutral-500" />
                  </div>
                )}
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                  {matchedUser.nickname}
                </h3>
              </div>

              {/* 标签区 */}
              <div className="flex flex-wrap justify-center gap-2 mb-5">
                {matchedUser.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-sm rounded-full"
                  >
                    {tag}
                  </span>
                ))}
              </div>

              {/* 信息列表 */}
              <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-neutral-600 dark:text-neutral-400">性别</span>
                  <span className="text-pink-500 font-medium">{matchedUser.gender}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-neutral-600 dark:text-neutral-400">年龄</span>
                  <span className="text-neutral-900 dark:text-neutral-100">{matchedUser.age}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-neutral-600 dark:text-neutral-400">城市</span>
                  <span className="text-neutral-900 dark:text-neutral-100">{matchedUser.city || '-'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-neutral-600 dark:text-neutral-400">魅力值</span>
                  <span className="text-neutral-900 dark:text-neutral-100">{matchedUser.charm_value}</span>
                </div>
              </div>

              {/* 底部操作区 */}
              <div className="flex gap-3">
                <button
                  onClick={closeMatchResult}
                  className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  重新匹配
                </button>
                <button
                  onClick={startChat}
                  className="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center justify-center gap-2"
                >
                  <MessageCircle className="w-4 h-4" />
                  开始聊天
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 顶部标题栏 */}
      <div className="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="max-w-md mx-auto px-4 py-3">
          <div className="flex justify-between items-center">
            <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
              遇见陌生人
            </h1>
            <div className="flex gap-2">
              <button
                onClick={() => navigate('/settings')}
                className="px-3 py-1 bg-white dark:bg-neutral-800 border border-blue-500 text-blue-500 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors flex items-center gap-2 text-sm"
              >
                <Settings className="w-4 h-4" />
                陌生人设置
              </button>
              <button className="px-3 py-1 bg-white dark:bg-neutral-800 border border-green-500 text-green-500 rounded-lg hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors flex items-center gap-2 text-sm">
                <Users className="w-4 h-4" />
                畅聊分区
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 匹配功能 */}
      <div className="px-4 py-6">
        {!loading && announcements.length > 0 && (
          <div className="mb-5">
            <AnnouncementCarousel announcements={announcements} autoPlay interval={4000} />
          </div>
        )}
        <div className="grid grid-cols-2 gap-4">
          <MatchCard
            title="扔瓶子"
            description="发送漂流瓶"
            color="bg-gradient-to-br from-purple-500 to-purple-600"
            icon={Users}
            onClick={openThrowBottleModal}
            disabled={isLoadingAction || isMatching}
          />
          <MatchCard
            title="捞个在线"
            description="随机捞一个在线的用户"
            color="bg-gradient-to-br from-pink-400 to-orange-500"
            icon={Users}
            onClick={handlePickOnline}
            disabled={isLoadingAction || isMatching}
          />
          <MatchCard
            title="捞瓶子"
            description="捞取漂流瓶"
            color="bg-gradient-to-br from-teal-400 to-blue-500"
            icon={Users}
            onClick={handlePickBottle}
            disabled={isLoadingAction || isMatching}
          />
          <MatchCard
            title="随机匹配"
            description="匹配一个正在匹配中的用户"
            color="bg-gradient-to-br from-blue-600 to-indigo-600"
            icon={Users}
            onClick={handleRandomMatch}
            disabled={isLoadingAction || isMatching}
          />
        </div>
      </div>

      {/* 模态框 */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className={`bg-white dark:bg-neutral-800 rounded-2xl w-full p-6 ${
            modalType === 'online' ? 'max-w-lg' : 'max-w-md'
          }`}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                {modalType === 'throw'
                  ? '扔瓶子'
                  : modalType === 'pickedBottle'
                  ? '捞瓶子'
                  : modalType === 'online'
                  ? '捞个在线'
                  : '捞到瓶子'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {modalType === 'throw' ? (
              <>
                <textarea
                  value={bottleContent}
                  onChange={(e) => setBottleContent(e.target.value)}
                  placeholder="写下你想说的话..."
                  className="w-full h-40 p-3 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-neutral-50 dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100 resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
                  maxLength={500}
                />
                <div className="flex justify-between items-center mt-3">
                  <span className="text-sm text-neutral-500 dark:text-neutral-400">
                    {bottleContent.length}/500
                  </span>
                  <button
                    onClick={handleThrowBottle}
                    disabled={isLoadingAction || !bottleContent.trim()}
                    className="px-6 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                  >
                    {isLoadingAction ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : null}
                    投入大海
                  </button>
                </div>
              </>
            ) : modalType === 'pickedBottle' && pickedBottle ? (
              <>
                <div className="border border-neutral-200 bg-white p-3 min-h-[300px]">
                  <p className="text-2xl leading-relaxed text-neutral-800 whitespace-pre-wrap break-words">
                    {pickedBottle.content}
                  </p>
                </div>
                <div className="text-right text-neutral-500 text-xl leading-snug py-4">
                  <div>
                    {pickedBottle.author_nickname}
                    <span className="ml-4">{pickedBottle.author_gender}</span>
                  </div>
                  <div>{formatBottleTime(pickedBottle.created_at)}</div>
                </div>
                <div className="-mx-6 -mb-6 grid grid-cols-2 border-t border-neutral-200">
                  <button
                    onClick={handleChatPickedBottle}
                    className="py-4 text-3xl font-semibold text-blue-500 border-r border-neutral-200"
                  >
                    聊聊看
                  </button>
                  <button
                    onClick={handleReportBottle}
                    className="py-4 text-3xl font-semibold text-red-500"
                  >
                    举报
                  </button>
                </div>
              </>
            ) : modalType === 'online' && onlineUser ? (
              <>
                <div className="flex items-center gap-4 mb-4">
                  {onlineUser.avatar ? (
                    <img src={onlineUser.avatar} alt={onlineUser.nickname} className="w-24 h-24 rounded-xl object-cover bg-neutral-100" />
                  ) : (
                    <div className="w-24 h-24 rounded-xl bg-neutral-100 flex items-center justify-center">
                      <User className="w-10 h-10 text-neutral-500" />
                    </div>
                  )}
                  <div>
                    <h3 className="text-4xl font-bold text-neutral-700 mb-2">{onlineUser.nickname}</h3>
                    {onlineUser.tags.slice(0, 1).map((tag) => (
                      <span key={tag} className="inline-block px-4 py-1 rounded-full bg-sky-500 text-white text-xl">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="border-t border-neutral-200 mb-4">
                  {[
                    ['性别', onlineUser.gender],
                    ['年龄', onlineUser.age],
                    ['城市', onlineUser.city || ''],
                    ['魅力值', onlineUser.charm_value]
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between items-center py-3 border-b border-neutral-200">
                      <span className="text-2xl font-medium text-neutral-600">{label}</span>
                      <span className={`text-2xl ${label === '性别' ? 'text-sky-500' : 'text-neutral-400'} font-semibold`}>{value}</span>
                    </div>
                  ))}
                </div>

                <div className="-mx-6 -mb-6 grid grid-cols-2 border-t border-neutral-200">
                  <button
                    onClick={handleNextOnlineUser}
                    className="py-4 text-3xl font-semibold text-orange-500 border-r border-neutral-200"
                  >
                    下一个
                  </button>
                  <button
                    onClick={handleChatOnlineUser}
                    className="py-4 text-3xl font-semibold text-blue-500"
                  >
                    聊聊看
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="bg-neutral-50 dark:bg-neutral-700 p-4 rounded-lg min-h-[100px]">
                  <p className="text-neutral-900 dark:text-neutral-100 whitespace-pre-wrap">
                    {bottleContent}
                  </p>
                </div>
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="w-full mt-4 px-6 py-2 bg-teal-500 text-white rounded-lg hover:bg-teal-600 transition-colors"
                >
                  关闭
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* 底部导航 */}
      <BottomNav />
    </div>
  )
}
