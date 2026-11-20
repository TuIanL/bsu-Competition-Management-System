const api = require('../../../utils/request')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')

Page({
  data: { tab: 'events', events: [], roles: [], loading: true, error: '' },

  onShow() {
    if (!auth.guard('admin')) return
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  async load() {
    try {
      const [events, roles] = await Promise.all([api.get('/api/events'), api.get('/api/roles')])
      this.setData({
        events: events.map((e) => Object.assign({}, e, {
          statusText: fmt.label('event', e.status),
          statusCls: e.status === 'ONGOING' ? 'chip-ball' : e.status === 'FINISHED' ? 'chip-grey' : ''
        })),
        roles,
        loading: false,
        error: ''
      })
    } catch (err) {
      this.setData({ loading: false, error: err.message })
    }
  },

  switchTab(e) {
    this.setData({ tab: e.currentTarget.dataset.key })
  },

  openEvent(e) {
    wx.navigateTo({ url: `/pages/admin/event-edit/event-edit?id=${e.currentTarget.dataset.id}` })
  },

  openRole(e) {
    wx.navigateTo({ url: `/pages/admin/role-edit/role-edit?id=${e.currentTarget.dataset.id}` })
  },

  create() {
    const page = this.data.tab === 'events' ? 'event-edit' : 'role-edit'
    wx.navigateTo({ url: `/pages/admin/${page}/${page}` })
  }
})
