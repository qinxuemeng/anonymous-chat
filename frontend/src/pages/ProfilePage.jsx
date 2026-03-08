import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import BottomNav from '../components/BottomNav'
import { useAuth } from '../context/AuthContext'
import { Upload, Camera, X } from 'lucide-react'

export default function ProfilePage() {
  const navigate = useNavigate()
  const { user, updateProfile, uploadAvatar } = useAuth()

  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [avatarPreview, setAvatarPreview] = useState(null)
  const [formData, setFormData] = useState({
    nickname: '',
    gender: 'secret',
    age: '',
    tags: []
  })

  const fileInputRef = useRef(null)

  const genderOptions = [
    { value: 'male', label: '男' },
    { value: 'female', label: '女' },
    { value: 'secret', label: '保密' }
  ]

  const tagOptions = ['幽默', '开朗', '内向', '话痨', '文艺', '技术控']

  // 初始化表单数据
  if (user && !formData.nickname) {
    setFormData({
      nickname: user.nickname || '',
      gender: user.gender || 'secret',
      age: user.age || '',
      tags: user.tags || []
    })
  }

  const handleFileChange = (event) => {
    const file = event.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setAvatarPreview(reader.result)
      }
      reader.readAsDataURL(file)

      // 上传头像
      handleUpload(file)
    }
  }

  const handleUpload = async (file) => {
    setLoading(true)
    const result = await uploadAvatar(file)
    if (result.success) {
      setSuccess('头像上传成功')
      setTimeout(() => setSuccess(''), 3000)
    } else {
      alert(result.error)
    }
    setLoading(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setSuccess('')

    const result = await updateProfile({
      nickname: formData.nickname,
      gender: formData.gender,
      age: parseInt(formData.age) || null,
      tags: formData.tags
    })

    if (result.success) {
      setSuccess('资料更新成功')
      setTimeout(() => navigate('/settings'), 2000)
    } else {
      alert(result.error)
    }

    setLoading(false)
  }

  const toggleTag = (tag) => {
    setFormData(prev => {
      return {
        ...prev,
        tags: prev.tags.includes(tag)
          ? prev.tags.filter(t => t !== tag)
          : [...prev.tags, tag]
      }
    })
  }

  return (
    <div className="min-h-screen bg-neutral-100 dark:bg-neutral-900 pb-20">
      {/* 顶部导航 */}
      <div className="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="max-w-md mx-auto px-4 py-3">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/settings')}
              className="p-2 -ml-2 rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-700"
            >
              <X className="w-6 h-6 text-neutral-900 dark:text-neutral-100" />
            </button>
            <h1 className="text-lg font-medium text-neutral-900 dark:text-neutral-100">
              编辑个人资料
            </h1>
          </div>
        </div>
      </div>

      <div className="px-4 py-6 max-w-md mx-auto">
        {/* 头像上传 */}
        <div className="text-center mb-8">
          <div className="relative inline-block mb-4">
            <div className="w-24 h-24 rounded-full overflow-hidden border-4 border-white dark:border-neutral-800 shadow-lg bg-neutral-200 dark:bg-neutral-700 mx-auto">
              {avatarPreview ? (
                <img
                  src={avatarPreview}
                  alt="头像预览"
                  className="w-full h-full object-cover"
                />
              ) : user?.avatar ? (
                <img
                  src={user.avatar}
                  alt="头像"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-neutral-400">
                  <Camera className="w-12 h-12" />
                </div>
              )}
            </div>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
              className="absolute bottom-1 right-1 bg-primary-500 text-white p-2 rounded-full hover:bg-primary-600 transition-colors disabled:opacity-50"
            >
              <Upload className="w-4 h-4" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              hidden
              onChange={handleFileChange}
            />
          </div>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            点击相机图标上传头像
          </p>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {success && (
            <div className="bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-4 py-2 rounded-lg text-sm">
              {success}
            </div>
          )}

          {/* 昵称 */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              昵称
            </label>
            <input
              type="text"
              value={formData.nickname}
              onChange={(e) => setFormData(prev => ({ ...prev, nickname: e.target.value }))}
              className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="请输入昵称"
              maxLength={20}
            />
          </div>

          {/* 性别 */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              性别
            </label>
            <div className="grid grid-cols-3 gap-2">
              {genderOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setFormData(prev => ({ ...prev, gender: option.value }))}
                  className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                    formData.gender === option.value
                      ? 'bg-primary-500 border-primary-500 text-white'
                      : 'bg-white dark:bg-neutral-800 border-neutral-300 dark:border-neutral-600 text-neutral-900 dark:text-neutral-100 hover:border-primary-400'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* 年龄 */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              年龄
            </label>
            <input
              type="number"
              value={formData.age}
              onChange={(e) => setFormData(prev => ({ ...prev, age: e.target.value }))}
              className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="请输入年龄"
              min="0"
              max="120"
            />
          </div>

          {/* 标签 */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              标签
            </label>
            <div className="flex flex-wrap gap-2">
              {tagOptions.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTag(tag)}
                  className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                    formData.tags.includes(tag)
                      ? 'bg-primary-500 border-primary-500 text-white'
                      : 'bg-white dark:bg-neutral-800 border-neutral-300 dark:border-neutral-600 text-neutral-900 dark:text-neutral-100 hover:border-primary-400'
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          {/* 保存按钮 */}
          <div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-600 transition-colors disabled:opacity-50"
            >
              {loading ? '保存中...' : '保存更改'}
            </button>
          </div>
        </form>

        {/* 账号信息 */}
        <div className="mt-8 p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-neutral-500 dark:text-neutral-400">账号</span>
            <span className="text-sm text-neutral-900 dark:text-neutral-100">{user?.username}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-neutral-500 dark:text-neutral-400">注册时间</span>
            <span className="text-sm text-neutral-900 dark:text-neutral-100">
              {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '未知'}
            </span>
          </div>
        </div>
      </div>

      <BottomNav />
    </div>
  )
}
