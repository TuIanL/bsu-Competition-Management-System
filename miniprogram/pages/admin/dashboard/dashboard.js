const api = require('../../../utils/request')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')
const ui = require('../../../utils/ui')

Page({
  data: { name: '', stats: null, gaps: [], loading: true, error: '' },

  onShow() {
    if (!auth.guard('admin')) return
    this.setData({ name: auth.getUser().name })
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  async load() {
    try {
      const stats = await api.get('/api/dashboard/stats')
      const gaps = stats.gap_shifts.map((s) => Object.assign({}, s, {
        time: fmt.shiftTime(s.start_time, s.end_time).full,
        live: s.phase === 'ongoing'
      }))
      this.setData({ stats, gaps, loading: false, error: '' })
    } catch (err) {
      this.setData({ loading: false, error: err.message })
    }
  },

  openShift(e) {
    wx.navigateTo({ url: `/pages/admin/schedule/schedule?id=${e.currentTarget.dataset.id}` })
  },

  goShifts() {
    wx.redirectTo({ url: '/pages/admin/shifts/shifts' })
  },

  goPassword() {
    wx.navigateTo({ url: '/pages/password/password' })
  },

  async logout() {
    if (!(await ui.confirm('退出登录', '确定要退出当前账号吗？', '退出'))) return
    try { await api.post('/api/logout') } catch (e) { /* 无状态 token，忽略 */ }
    auth.clear()
    wx.reLaunch({ url: '/pages/login/login' })
  }
})
