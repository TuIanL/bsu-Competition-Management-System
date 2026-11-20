const api = require('../../../utils/request')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')
const ui = require('../../../utils/ui')

const STATUSES = [
  { value: 'PLANNED', text: '未开始' },
  { value: 'ONGOING', text: '进行中' },
  { value: 'FINISHED', text: '已结束' }
]

Page({
  data: {
    id: null,
    statuses: STATUSES,
    statusIndex: 0,
    shiftCount: 0,
    form: { name: '', event_date: '', venue: '' },
    submitting: false
  },

  async onLoad(options) {
    if (!auth.guard('admin')) return
    const id = options.id ? +options.id : null
    wx.setNavigationBarTitle({ title: id ? '编辑赛事' : '新建赛事' })
    this.setData({ id, 'form.event_date': fmt.todayStr() })
    if (!id) return
    try {
      const e = await api.get(`/api/events/${id}`)
      this.setData({
        form: { name: e.name, event_date: e.event_date, venue: e.venue || '' },
        statusIndex: STATUSES.findIndex((s) => s.value === e.status),
        shiftCount: e.shift_count
      })
    } catch (err) {
      ui.toast(err.message)
    }
  },

  onInput(e) {
    ui.bindInput(this, e)
  },

  pickDate(e) {
    this.setData({ 'form.event_date': e.detail.value })
  },

  pickStatus(e) {
    this.setData({ statusIndex: +e.detail.value })
  },

  async submit() {
    const f = this.data.form
    if (!f.name.trim()) return ui.toast('请填写赛事名称')
    if (this.data.submitting) return
    this.setData({ submitting: true })
    const payload = { name: f.name.trim(), event_date: f.event_date, venue: f.venue.trim(), status: STATUSES[this.data.statusIndex].value }
    try {
      if (this.data.id) await api.put(`/api/events/${this.data.id}`, payload, { loading: '保存中' })
      else await api.post('/api/events', payload, { loading: '保存中' })
      ui.success('已保存')
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (err) {
      ui.alert('无法保存', err.message)
    } finally {
      this.setData({ submitting: false })
    }
  },

  newShift() {
    wx.navigateTo({ url: `/pages/admin/shift-edit/shift-edit?event_id=${this.data.id}` })
  },

  async remove() {
    if (!(await ui.confirm('删除赛事', '只有还没有班次的赛事才能删除。确定删除？', '删除'))) return
    try {
      await api.del(`/api/events/${this.data.id}`, { loading: '删除中' })
      ui.success('已删除')
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (err) {
      ui.alert('无法删除', err.message)
    }
  }
})
