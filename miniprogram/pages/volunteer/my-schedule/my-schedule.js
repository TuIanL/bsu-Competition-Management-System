const api = require('../../../utils/request')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')
const ui = require('../../../utils/ui')

function view(s) {
  let status = { text: '待签到', cls: '' }
  if (s.status === 'COMPLETED') status = { text: `已完成，计 ${fmt.hoursText(s.minutes || 0)}`, cls: 'chip-grass' }
  else if (s.check_in_at) status = { text: `${fmt.hm(s.check_in_at)} 已签到`, cls: 'chip-ball' }
  else if (s.no_show) status = { text: '未签到', cls: 'chip-clay' }
  else if (s.phase === 'upcoming') status = { text: '未开始', cls: 'chip-grey' }
  return Object.assign({}, s, { time: fmt.shiftTime(s.start_time, s.end_time), statusText: status.text, statusCls: status.cls })
}

Page({
  data: {
    user: null,
    groups: [],
    total: 0,
    pendingCount: 0,
    loading: true,
    error: '',
    busy: false
  },

  onShow() {
    if (!auth.guard('volunteer')) return
    this.setData({ user: auth.getUser() })
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  async load() {
    try {
      const [shifts, apps] = await Promise.all([
        api.get('/api/volunteer/my-shifts'),
        api.get('/api/volunteer/my-applications')
      ])
      const items = shifts.map(view)
      const groups = [
        { key: 'ongoing', title: '进行中', items: items.filter((s) => s.phase === 'ongoing') },
        { key: 'upcoming', title: '即将开始', items: items.filter((s) => s.phase === 'upcoming') },
        { key: 'ended', title: '已结束', items: items.filter((s) => s.phase === 'ended').reverse() }
      ].filter((g) => g.items.length)
      this.setData({
        groups,
        total: items.length,
        pendingCount: apps.filter((a) => a.status === 'PENDING').length,
        loading: false,
        error: ''
      })
    } catch (err) {
      this.setData({ loading: false, error: err.message })
    }
  },

  async checkin(e) {
    if (this.data.busy) return
    this.setData({ busy: true })
    try {
      const r = await api.post(`/api/assignments/${e.currentTarget.dataset.id}/checkin`, {}, { loading: '签到中' })
      ui.success(`${fmt.hm(r.check_in_at)} 签到成功`)
      await this.load()
    } catch (err) {
      ui.alert('签到失败', err.message)
    } finally {
      this.setData({ busy: false })
    }
  },

  async checkout(e) {
    const ok = await ui.confirm('签退', '签退后本班次记为已完成，志愿时长按班次时间内的实际在岗时间计算。确定签退？', '签退')
    if (!ok || this.data.busy) return
    this.setData({ busy: true })
    try {
      await api.post(`/api/assignments/${e.currentTarget.dataset.id}/checkout`, {}, { loading: '签退中' })
      ui.success('签退成功')
      await this.load()
    } catch (err) {
      ui.alert('签退失败', err.message)
    } finally {
      this.setData({ busy: false })
    }
  },

  goPositions() {
    wx.redirectTo({ url: '/pages/volunteer/positions/positions' })
  },

  goPassword() {
    wx.navigateTo({ url: '/pages/password/password' })
  },

  async logout() {
    if (!(await ui.confirm('退出登录', '确定要退出当前账号吗？', '退出'))) return
    auth.clear()
    wx.reLaunch({ url: '/pages/login/login' })
  }
})
