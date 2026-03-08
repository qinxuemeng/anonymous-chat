import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { ChevronLeft } from 'lucide-react'

export default function RechargeRecordsPage() {
  const navigate = useNavigate()
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)

  const formatTime = (timeStr) => {
    if (!timeStr) return '-'
    const d = new Date(timeStr)
    if (Number.isNaN(d.getTime())) return '-'
    return d.toLocaleString('zh-CN', { hour12: false })
  }

  const loadRows = async (p = page) => {
    try {
      setLoading(true)
      const res = await api.get('/charm/recharge-records', { params: { page: p, page_size: 20 } })
      if (res.data?.success) {
        setRows(res.data.data?.rows || [])
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRows(1)
  }, [])

  return (
    <div className="min-h-screen bg-neutral-100 dark:bg-neutral-900 pb-8">
      <div className="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="max-w-md mx-auto px-4 py-3 flex items-center gap-2">
          <button onClick={() => navigate('/settings')} className="p-1 rounded-full hover:bg-neutral-100 dark:hover:bg-neutral-700">
            <ChevronLeft className="w-5 h-5 text-neutral-700 dark:text-neutral-300" />
          </button>
          <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">我的充值记录</h1>
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 py-4">
        {loading ? (
          <div className="text-center text-neutral-500 py-10">加载中...</div>
        ) : rows.length === 0 ? (
          <div className="text-center text-neutral-500 py-10">暂无充值记录</div>
        ) : (
          <div className="space-y-2">
            {rows.map((row) => (
              <div key={row.order_no} className="rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">订单号：{row.order_no}</p>
                  <p className="text-sm text-emerald-600">¥{row.amount_cny ?? 0}</p>
                </div>
                <div className="mt-1 flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400">
                  <span>{row.channel === 'wechat' ? '微信支付' : row.channel === 'alipay' ? '支付宝' : '-'}</span>
                  <span>支付时间：{formatTime(row.paid_at || row.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="flex justify-end gap-2 mt-3">
          <button
            disabled={page <= 1}
            onClick={() => { const p = page - 1; setPage(p); loadRows(p) }}
            className="px-3 py-1.5 rounded border border-neutral-300 disabled:opacity-50"
          >
            上一页
          </button>
          <button
            onClick={() => { const p = page + 1; setPage(p); loadRows(p) }}
            className="px-3 py-1.5 rounded border border-neutral-300"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  )
}
