const api = require('../../../utils/request')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')

const SCOPES = [
  { key: 'active', text: '未结束' },
  { key: 'ended', text: '已结束' },
  { key: 'all', text: '全部' }
]

Page({
  data: {
    scopes: SCOPES,
    scope: 'active',
    events: [{ id: 0, name: '全部赛事' }],
    eventIndex: 0,
    shifts: [],
    loading: true,
    error: ''
  },

  onShow() {
    if (!auth.guard('admin')) return
    this.loadEvents()
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  async loadEvents() {
    try {
      const events = await api.get('/api/events')
      this.setData({ events: [{ id: 0, name: '全部赛事' }].concat(events) })
    } catch (e) { /* 筛选项加载失败不影响列表 */ }
  },

  async load() {
    const event = this.data.events[this.data.eventIndex]
    const query = { scope: this.data.scope }
    if (event && event.id) query.event_id = event.id
    try {
      const list = await api.get('/api/shifts', query)
      const shifts = list.map((s) => Object.assign({}, s, {
        time: fmt.shiftTime(s.start_time, s.end_time),
        phaseText: fmt.label('phase', s.phase)
      }))
      this.setData({ shifts, loading: false, error: '' })
    } catch (err) {
      this.setData({ loading: false, error: err.message })
    }
  },

  switchScope(e) {
    this.setData({ scope: e.currentTarget.dataset.key, loading: true })
    this.load()
  },

  pickEvent(e) {
    this.setData({ eventIndex: +e.detail.value, loading: true })
    this.load()
  },

  open(e) {
    wx.navigateTo({ url: `/pages/admin/schedule/schedule?id=${e.currentTarget.dataset.id}` })
  },

  create() {
    wx.navigateTo({ url: '/pages/admin/shift-edit/shift-edit' })
  }
})
