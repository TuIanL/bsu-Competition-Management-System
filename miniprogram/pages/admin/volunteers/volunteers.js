const api = require('../../../utils/request')
const auth = require('../../../utils/auth')

const FILTERS = [
  { key: '', text: '全部' },
  { key: 'ACTIVE', text: '正常' },
  { key: 'INACTIVE', text: '已停用' }
]

Page({
  data: { filters: FILTERS, status: '', keyword: '', list: [], loading: true, error: '' },

  onShow() {
    if (!auth.guard('admin')) return
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  async load() {
    const query = {}
    if (this.data.keyword) query.keyword = this.data.keyword
    if (this.data.status) query.status = this.data.status
    try {
      const list = await api.get('/api/volunteers', query)
      this.setData({ list, loading: false, error: '' })
    } catch (err) {
      this.setData({ loading: false, error: err.message })
    }
  },

  onKeyword(e) {
    this.setData({ keyword: e.detail.value.trim() })
  },

  switchFilter(e) {
    this.setData({ status: e.currentTarget.dataset.key })
    this.load()
  },

  open(e) {
    wx.navigateTo({ url: `/pages/admin/volunteer-edit/volunteer-edit?id=${e.currentTarget.dataset.id}` })
  },

  create() {
    wx.navigateTo({ url: '/pages/admin/volunteer-edit/volunteer-edit' })
  }
})
