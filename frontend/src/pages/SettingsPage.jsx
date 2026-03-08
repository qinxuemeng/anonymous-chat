import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import BottomNav from '../components/BottomNav'
import { useAuth } from '../context/AuthContext'
import { Moon, Bell, Shield, Lock, Eye, Globe, User, ChevronRight, LogOut, X } from 'lucide-react'

export default function SettingsPage() {
  const { user, logout, updateSettings } = useAuth()
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState('')
  const [showCharmGuide, setShowCharmGuide] = useState(false)

  const [settings, setSettings] = useState({
    allowDiscovery: true,
    greenMode: false,
    nightMode: false,
    notificationSound: true,
    keepLoggedIn: false,
    englishMode: false,
    showLocation: false
  })

  useEffect(() => {
    if (user) {
      setSettings({
        allowDiscovery: user.allow_discovery ?? true,
        greenMode: user.green_mode ?? false,
        nightMode: user.night_mode ?? false,
        notificationSound: user.notification_sound ?? true,
        keepLoggedIn: user.keep_logged_in ?? false,
        englishMode: user.english_mode ?? false,
        showLocation: user.show_location ?? false
      })

      // 应用深色模式
      if (user.night_mode) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    }
  }, [user])

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(''), 3000)
    return () => clearTimeout(timer)
  }, [toast])

  const handleSettingChange = async (key, value) => {
    if (loading) return

    if ((user?.charm_value || 0) < 200 && key === 'allowDiscovery') {
      setToast('魅力值需大于200才可修改陌生人设置')
      return
    }
    if ((user?.charm_value || 0) < 20 && key === 'greenMode') {
      setToast('魅力值小于20时强制开启绿色模式')
      return
    }

    setLoading(true)
    const prevSettings = settings
    setSettings(prev => ({ ...prev, [key]: value }))

    if (key === 'nightMode') {
      if (value) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    }

    const keyMap = {
      allowDiscovery: 'allow_discovery',
      greenMode: 'green_mode',
      nightMode: 'night_mode',
      notificationSound: 'notification_sound',
      keepLoggedIn: 'keep_logged_in',
      englishMode: 'english_mode',
      showLocation: 'show_location'
    }

    const result = await updateSettings({ [keyMap[key] || key]: value })
    if (!result.success) {
      setSettings(prevSettings)
      setToast(result.error || '设置更新失败')
    }
    setLoading(false)
  }

  const toggleSetting = (key) => {
    handleSettingChange(key, !settings[key])
  }

  const getCharmLevel = (value) => {
    if (value < 20) return '受限'
    if (value < 35) return '观察'
    if (value < 50) return '进阶'
    if (value < 100) return '活跃'
    if (value < 200) return '优质'
    return '核心'
  }

  return (
    <div className="min-h-screen bg-neutral-100 dark:bg-neutral-900 pb-24">
      {toast && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-neutral-900 text-white px-4 py-2 rounded-lg text-sm">
          {toast}
        </div>
      )}

      {/* 顶部标题 */}
      <div className="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="max-w-md mx-auto px-4 py-3">
          <h1 className="text-xl font-semibold text-center text-neutral-900 dark:text-neutral-100">
            设置
          </h1>
        </div>
      </div>

      {/* 用户信息卡片 */}
      <div className="px-4 py-4">
        <div className="bg-white dark:bg-neutral-800 rounded-xl p-4 shadow-card">
          <Link to="/profile" className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
              {user?.avatar ? (
                <img src={user.avatar} alt="头像" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-neutral-500">
                  <User className="w-8 h-8" />
                </div>
              )}
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-medium text-neutral-900 dark:text-neutral-100">
                {user?.nickname || '未设置昵称'}
              </h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                {user?.username}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-sm text-primary-500 font-medium">
                  {user?.charm_value || 0} 魅力值
                </span>
                <span className="px-2 py-0.5 bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 text-xs rounded-full">
                  {getCharmLevel(user?.charm_value || 0)}
                </span>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-neutral-400" />
          </Link>
        </div>
      </div>

      {/* 隐私与功能设置 */}
      <div className="px-4 py-2">
        <h3 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-3 px-1">
          隐私与功能设置
        </h3>
        <div className="bg-white dark:bg-neutral-800 rounded-xl overflow-hidden shadow-card">
          <SettingItem
            icon={<Eye className="w-5 h-5" />}
            label='允许被"捞个在线"发现'
            description={(user?.charm_value || 0) < 200 ? '魅力值需大于200' : ''}
            value={settings.allowDiscovery}
            onChange={() => toggleSetting('allowDiscovery')}
            disabled={user?.charm_value < 200}
          />
          <SettingItem
            icon={<Shield className="w-5 h-5" />}
            label="绿色模式"
            description={(user?.charm_value || 0) < 20 ? '魅力值小于20时强制开启' : '私聊屏蔽所有敏感词'}
            value={(user?.charm_value || 0) < 20 ? true : settings.greenMode}
            onChange={() => toggleSetting('greenMode')}
            disabled={(user?.charm_value || 0) < 20}
          />
          <SettingItem
            icon={<Moon className="w-5 h-5" />}
            label="夜间模式"
            description="深色主题，呵护您的双眼"
            value={settings.nightMode}
            onChange={() => toggleSetting('nightMode')}
          />
          <SettingItem
            icon={<Bell className="w-5 h-5" />}
            label="通知声音"
            description=""
            value={settings.notificationSound}
            onChange={() => toggleSetting('notificationSound')}
          />
          <SettingItem
            icon={<Lock className="w-5 h-5" />}
            label="关闭浏览器自动退出账号"
            description=""
            value={settings.keepLoggedIn}
            onChange={() => toggleSetting('keepLoggedIn')}
          />
          <SettingItem
            icon={<Globe className="w-5 h-5" />}
            label="英语模式"
            description="私聊只能用字母交流"
            value={settings.englishMode}
            onChange={() => toggleSetting('englishMode')}
          />
        </div>
      </div>

      {/* 个人资料设置 */}
      <div className="px-4 py-2">
        <h3 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-3 px-1">
          个人资料设置
        </h3>
        <div className="bg-white dark:bg-neutral-800 rounded-xl overflow-hidden shadow-card">
          <ProfileItem label="账号" value={user?.username || '未注册'} to="/profile" />
          <ProfileItem label="绑定激活" value="" to="/profile" />
          <ProfileItem label="头像" value="" to="/profile" />
          <ProfileItem label="昵称" value={user?.nickname || '-'} to="/profile" />
          <ProfileItem label="性别" value={user?.gender || '保密'} to="/profile" />
          <ProfileItem label="年龄" value={user?.age || '0'} to="/profile" />
          <SettingItem
            icon={<Eye className="w-5 h-5" />}
            label="显示位置"
            description=""
            value={settings.showLocation}
            onChange={() => toggleSetting('showLocation')}
          />
          <ProfileItem label="标签" value="查看" to="/profile" />
          <div className="px-4 py-3 flex items-center justify-between border-t border-neutral-200 dark:border-neutral-700">
            <span className="text-neutral-900 dark:text-neutral-100">
              魅力值
            </span>
            <div className="flex items-center gap-2">
              <span className="text-primary-500 font-medium">{user?.charm_value || 0}</span>
              <button
                className="text-sm text-primary-500"
                onClick={() => setShowCharmGuide(true)}
              >
                魅力值说明
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 其他设置 */}
      <div className="px-4 py-2">
        <h3 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-3 px-1">
          其他设置
        </h3>
        <div className="bg-white dark:bg-neutral-800 rounded-xl overflow-hidden shadow-card">
          <ProfileItem label="伪装魅力值" value="" to="/profile" />
          <div className="px-4 py-3 flex items-center justify-between border-t border-neutral-200 dark:border-neutral-700">
            <span className="text-neutral-900 dark:text-neutral-100">
              帮助信息
            </span>
            <a href="#" className="text-sm text-primary-500">服务条款</a>
          </div>
          <ProfileItem label="注销账号" value="" to="/profile" danger />
        </div>
      </div>

      {/* 退出登录 */}
      <div className="px-4 py-4">
        <button
          onClick={logout}
          className="w-full py-3 bg-white dark:bg-neutral-800 text-red-500 rounded-xl font-medium shadow-card flex items-center justify-center gap-2"
        >
          <LogOut className="w-5 h-5" />
          退出登录
        </button>
      </div>

      <BottomNav />

      {showCharmGuide && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-white dark:bg-neutral-800 rounded-2xl max-h-[85vh] overflow-y-auto">
            <div className="sticky top-0 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 px-5 py-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">魅力值说明</h2>
              <button onClick={() => setShowCharmGuide(false)} className="text-neutral-500">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-5 space-y-4 text-sm text-neutral-700 dark:text-neutral-300">
              <p>为维护良好的聊天环境，鼓励文明和谐友善的行为。</p>
              <div>
                <h3 className="font-semibold mb-2 text-neutral-900 dark:text-neutral-100">魅力值作用</h3>
                <ol className="list-decimal pl-5 space-y-1">
                  <li>小于20，强制绿色模式，每日随机匹配最多200次，捞瓶子和捞在线最多2次。</li>
                  <li>大于35，可发文件，可修改昵称，初始值是30。</li>
                  <li>大于50，可上传自定义头像，可扔瓶子，可捞瓶子。</li>
                  <li>大于100，可发布寻人公告，女性用户“捞个在线”会优先捞大于100的用户。</li>
                  <li>大于200，可修改陌生人设置。</li>
                  <li>大于200后，每50魅力值增加1次所有功能每天的使用次数。</li>
                  <li>魅力值越高，所有功能的优先级越高。</li>
                  <li>魅力值越高，每日与虚拟人物对话的次数越多。</li>
                </ol>
              </div>
              <div>
                <h3 className="font-semibold mb-2 text-neutral-900 dark:text-neutral-100">魅力值获取</h3>
                <ol className="list-decimal pl-5 space-y-1">
                  <li>积极文明和谐的发言，系统实时给予相应的魅力值。</li>
                  <li>系统智能判断行为良好的，给予一定的魅力值。</li>
                  <li>得到对方点赞将获得对应的魅力值。</li>
                  <li>每日进入平台自动获取5魅力值。</li>
                  <li>购买会员，一次获得30魅力值。</li>
                </ol>
              </div>
              <div>
                <h3 className="font-semibold mb-2 text-neutral-900 dark:text-neutral-100">魅力值扣除</h3>
                <ol className="list-decimal pl-5 space-y-1">
                  <li>发送违规内容引起别人反感，根据违规内容扣相应的魅力值。</li>
                  <li>聊天被举报或拉黑，经人工核实有违规行为，一次最少扣5魅力值。</li>
                  <li>过多无意义发言，刷魅力值等行为，清空魅力值。</li>
                  <li>上传头像人工审核不通过，一次扣30。</li>
                  <li>修改昵称人工审核不通过，一次扣20。</li>
                  <li>扔瓶子人工审核不通过，一次扣5。</li>
                  <li>上传头像自动审核不通过，一次扣5。</li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function SettingItem({ icon, label, description, value, onChange, disabled = false }) {
  return (
    <div className="px-4 py-3 flex items-center justify-between border-b border-neutral-200 dark:border-neutral-700 last:border-0">
      <div className="flex items-start gap-3">
        <div className="text-neutral-500 dark:text-neutral-400 mt-0.5">
          {icon}
        </div>
        <div>
          <span className={`text-neutral-900 dark:text-neutral-100 ${disabled ? 'opacity-50' : ''}`}>
            {label}
          </span>
          {description && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
              {description}
            </p>
          )}
        </div>
      </div>
      <button
        onClick={onChange}
        disabled={disabled}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
          value ? 'bg-primary-500' : 'bg-neutral-300 dark:bg-neutral-600'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
            value ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  )
}

function ProfileItem({ label, value, to, danger = false }) {
  return (
    <div className="px-4 py-3 flex items-center justify-between border-b border-neutral-200 dark:border-neutral-700 last:border-0">
      <span className={`${danger ? 'text-red-500' : 'text-neutral-900 dark:text-neutral-100'}`}>
        {label}
      </span>
      <div className="flex items-center gap-2">
        <span className="text-sm text-neutral-500 dark:text-neutral-400">
          {value}
        </span>
        <ChevronRight className="w-4 h-4 text-neutral-400" />
      </div>
    </div>
  )
}
