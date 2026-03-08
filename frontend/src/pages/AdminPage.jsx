import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { Shield, Users, ListChecks, FileText, RefreshCw } from 'lucide-react'

export default function AdminPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('dashboard')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')

  const [dashboard, setDashboard] = useState(null)
  const [users, setUsers] = useState([])
  const [orders, setOrders] = useState([])
  const [wordsText, setWordsText] = useState('')

  const [userKeyword, setUserKeyword] = useState('')
  const [userPage, setUserPage] = useState(1)
  const [orderPage, setOrderPage] = useState(1)

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(''), 2500)
    return () => clearTimeout(t)
  }, [toast])

  const loadDashboard = async () => {
    const res = await api.get('/admin/dashboard')
    if (res.data?.success) setDashboard(res.data.data)
  }

  const loadUsers = async (page = userPage, keyword = userKeyword) => {
    const res = await api.get('/admin/users', { params: { page, page_size: 20, keyword } })
    if (res.data?.success) setUsers(res.data.data.rows || [])
  }

  const loadOrders = async (page = orderPage) => {
    const res = await api.get('/admin/orders', { params: { page, page_size: 20 } })
    if (res.data?.success) setOrders(res.data.data.rows || [])
  }

  const loadWords = async () => {
    const res = await api.get('/admin/sensitive-words')
    if (res.data?.success) {
      const rows = res.data.data.words || []
      setWordsText(rows.join('\n'))
    }
  }

  const loadAll = async () => {
    try {
      setLoading(true)
      setError('')
      await api.get('/admin/me')
      await Promise.all([loadDashboard(), loadUsers(1, ''), loadOrders(1), loadWords()])
      setUserPage(1)
      setOrderPage(1)
      setUserKeyword('')
    } catch (e) {
      setError(e?.response?.data?.error || '无管理员权限或加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAll()
  }, [])

  const patchUser = async (id, payload) => {
    try {
      const res = await api.patch(`/admin/users/${id}`, payload)
      if (!res.data?.success) {
        setToast(res.data?.error || '更新失败')
        return
      }
      setToast('更新成功')
      await loadUsers(userPage, userKeyword)
      await loadDashboard()
    } catch (e) {
      setToast(e?.response?.data?.error || '更新失败')
    }
  }

  const saveWords = async () => {
    const words = wordsText.split('\n').map((x) => x.trim()).filter(Boolean)
    try {
      const res = await api.put('/admin/sensitive-words', { words })
      if (res.data?.success) setToast(`已保存 ${res.data.data?.count || words.length} 个敏感词`)
      else setToast(res.data?.error || '保存失败')
    } catch (e) {
      setToast(e?.response?.data?.error || '保存失败')
    }
  }

  if (loading) {
    return <div className="min-h-screen bg-neutral-100 flex items-center justify-center text-neutral-600">后台加载中...</div>
  }

  if (error) {
    return (
      <div className="min-h-screen bg-neutral-100 flex flex-col items-center justify-center px-4">
        <p className="text-red-500 mb-4">{error}</p>
        <button onClick={() => navigate('/discover')} className="px-4 py-2 rounded-lg bg-neutral-900 text-white">返回</button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#e0ecff_0%,#f8fafc_38%,#f5f7fb_100%)] pb-8">
      {toast && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-neutral-900 text-white px-4 py-2 rounded-lg text-sm">{toast}</div>
      )}
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <div className="rounded-3xl p-5 bg-white/90 backdrop-blur border border-white shadow-[0_12px_45px_rgba(15,23,42,0.08)]">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white flex items-center justify-center">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-2xl font-extrabold text-neutral-900">管理员控制台</h1>
                <p className="text-sm text-neutral-500">用户管理 · 绿色模式敏感词 · 订单看板</p>
              </div>
            </div>
            <button onClick={loadAll} className="px-3 py-2 rounded-lg border border-neutral-300 text-neutral-700 flex items-center gap-2 text-sm">
              <RefreshCw className="w-4 h-4" />
              刷新
            </button>
          </div>

          <div className="grid grid-cols-3 gap-2 mt-4">
            <TabBtn active={tab === 'dashboard'} onClick={() => setTab('dashboard')} icon={<ListChecks className="w-4 h-4" />} text="订单看板" />
            <TabBtn active={tab === 'users'} onClick={() => setTab('users')} icon={<Users className="w-4 h-4" />} text="用户管理" />
            <TabBtn active={tab === 'words'} onClick={() => setTab('words')} icon={<FileText className="w-4 h-4" />} text="敏感词配置" />
          </div>
        </div>

        {tab === 'dashboard' && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            <Kpi title="用户总数" value={dashboard?.users?.total ?? 0} />
            <Kpi title="在线人数" value={dashboard?.users?.online ?? 0} />
            <Kpi title="今日订单" value={dashboard?.orders?.today_total ?? 0} />
            <Kpi title="今日收入" value={`¥${dashboard?.orders?.today_paid_amount ?? 0}`} />
            <div className="col-span-2 md:col-span-4 rounded-2xl bg-white border border-neutral-200 p-4">
              <h3 className="font-semibold text-neutral-900 mb-3">近7天支付趋势</h3>
              <div className="space-y-2">
                {(dashboard?.paid_trend_7d || []).map((d) => (
                  <div key={d.day} className="flex items-center justify-between text-sm">
                    <span className="text-neutral-500">{d.day}</span>
                    <span className="text-neutral-800">支付 {d.paid_count} 单 / ¥{d.paid_amount}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === 'users' && (
          <div className="mt-4 rounded-2xl bg-white border border-neutral-200 p-4">
            <div className="flex gap-2 mb-3">
              <input
                value={userKeyword}
                onChange={(e) => setUserKeyword(e.target.value)}
                placeholder="搜索 username / nickname / id"
                className="flex-1 px-3 py-2 rounded-lg border border-neutral-300"
              />
              <button onClick={() => { setUserPage(1); loadUsers(1, userKeyword) }} className="px-4 py-2 rounded-lg bg-blue-600 text-white">查询</button>
            </div>
            <div className="space-y-2">
              {users.map((u) => (
                <div key={u.id} className="rounded-xl border border-neutral-200 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-semibold text-neutral-900 truncate">{u.nickname || '未命名'} <span className="text-xs text-neutral-500">(@{u.username})</span></p>
                      <p className="text-xs text-neutral-500 truncate">{u.id}</p>
                    </div>
                    <div className="text-sm text-neutral-700">魅力值 {u.charm_value}</div>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-3">
                    <button onClick={() => patchUser(u.id, { is_active: !u.is_active })} className={`px-2.5 py-1 rounded border text-xs ${u.is_active ? 'border-emerald-400 text-emerald-700' : 'border-red-400 text-red-700'}`}>
                      {u.is_active ? '停用账号' : '启用账号'}
                    </button>
                    <button onClick={() => patchUser(u.id, { green_mode: !u.green_mode })} className="px-2.5 py-1 rounded border text-xs border-neutral-300 text-neutral-700">
                      绿色模式: {u.green_mode ? '开' : '关'}
                    </button>
                    <button onClick={() => patchUser(u.id, { allow_discovery: !u.allow_discovery })} className="px-2.5 py-1 rounded border text-xs border-neutral-300 text-neutral-700">
                      在线发现: {u.allow_discovery ? '开' : '关'}
                    </button>
                    <button onClick={() => patchUser(u.id, { role: u.role === 'admin' ? 'user' : 'admin' })} className="px-2.5 py-1 rounded border text-xs border-indigo-300 text-indigo-700">
                      角色: {u.role}
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2 mt-3">
              <button disabled={userPage <= 1} onClick={() => { const p = userPage - 1; setUserPage(p); loadUsers(p, userKeyword) }} className="px-3 py-1.5 rounded border border-neutral-300 disabled:opacity-50">上一页</button>
              <button onClick={() => { const p = userPage + 1; setUserPage(p); loadUsers(p, userKeyword) }} className="px-3 py-1.5 rounded border border-neutral-300">下一页</button>
            </div>
          </div>
        )}

        {tab === 'words' && (
          <div className="mt-4 rounded-2xl bg-white border border-neutral-200 p-4">
            <p className="text-sm text-neutral-500 mb-2">绿色模式敏感词（每行一个）</p>
            <textarea
              value={wordsText}
              onChange={(e) => setWordsText(e.target.value)}
              className="w-full h-80 rounded-xl border border-neutral-300 p-3"
              placeholder="例如：诈骗"
            />
            <div className="flex justify-end mt-3">
              <button onClick={saveWords} className="px-4 py-2 rounded-lg bg-blue-600 text-white">保存配置</button>
            </div>
          </div>
        )}

        {tab === 'orders' && (
          <div className="mt-4 rounded-2xl bg-white border border-neutral-200 p-4">订单列表</div>
        )}

        {tab === 'dashboard' ? null : tab === 'words' ? null : (
          <div className="mt-4 rounded-2xl bg-white border border-neutral-200 p-4">
            <h3 className="font-semibold text-neutral-900 mb-3">支付订单</h3>
            <div className="space-y-2">
              {orders.map((o) => (
                <div key={o.order_no} className="flex items-center justify-between text-sm rounded-lg border border-neutral-200 p-2.5">
                  <div className="min-w-0">
                    <p className="truncate text-neutral-900">{o.order_no}</p>
                    <p className="text-neutral-500 truncate">{o.nickname || o.username || o.user_id}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-neutral-900">¥{o.amount_cny}</p>
                    <p className="text-xs text-neutral-500">{o.channel} · {o.status}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2 mt-3">
              <button disabled={orderPage <= 1} onClick={() => { const p = orderPage - 1; setOrderPage(p); loadOrders(p) }} className="px-3 py-1.5 rounded border border-neutral-300 disabled:opacity-50">上一页</button>
              <button onClick={() => { const p = orderPage + 1; setOrderPage(p); loadOrders(p) }} className="px-3 py-1.5 rounded border border-neutral-300">下一页</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Kpi({ title, value }) {
  return (
    <div className="rounded-2xl bg-white border border-neutral-200 p-4">
      <p className="text-sm text-neutral-500">{title}</p>
      <p className="text-2xl font-bold text-neutral-900 mt-1">{value}</p>
    </div>
  )
}

function TabBtn({ active, onClick, icon, text }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`h-11 rounded-xl border text-sm font-medium flex items-center justify-center gap-2 ${
        active ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-neutral-700 border-neutral-300'
      }`}
    >
      {icon}
      {text}
    </button>
  )
}
