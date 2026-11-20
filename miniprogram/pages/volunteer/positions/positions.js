const api = require('../../../utils/request')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')
const ui = require('../../../utils/ui')

function view(p) {
  // 按钮状态：报名 / 已报名，待安排 / 已安排 / 时间冲突
  let action = { text: '报名', cls: '', tap: 'apply' }
  if (p.application_status === 'PENDING') action = { text: '已报名，待安排', cls: 'btn-off', tap: '' }
  else if (p.application_status === 'APPROVED') action = { text: '已安排', cls: 'btn-off', tap: '' }
  else if (p.conflict) action = { text: '时间冲突', cls: 'btn-off', tap: '' }
  return Object.assign({}, p, {
    time: fmt.shiftTime(p.start_time, p.end_time),
    action,
    canWithdraw: p.application_status === 'PENDING',
    reapply: p.application_status === 'WITHDRAWN'
  })
}

Page({
  data: { list: [], loading: true, error: '', busy: false },

  onShow() {
    if (!auth.guard('volunteer')) return
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  async load() {
    try {
      const list = await api.get('/api/volunteer/positions')
      this.setData({ list: list.map(view), loading: false, error: '' })
    } catch (err) {
      this.setData({ loading: false, error: err.message })
    }
  },

  updateItem(shiftId, patch) {
    const index = this.data.list.findIndex((p) => p.shift_id === shiftId)
    if (index < 0) return
    this.setData({ [`list[${index}]`]: view(Object.assign({}, this.data.list[index], patch)) })
  },

  onAction(e) {
    if (e.currentTarget.dataset.tap === 'apply') this.apply(e)
  },

  async apply(e) {
    const shiftId = e.currentTarget.dataset.id
    if (this.data.busy) return
    this.setData({ busy: true })
    try {
      const r = await api.post('/api/applications', { shift_id: shiftId }, { loading: '提交中' })
      // 成功后按钮立即变灰为"已报名，待安排"
      this.updateItem(shiftId, { application_status: 'PENDING', application_id: r.id })
      ui.success('报名成功')
    } catch (err) {
      ui.alert('报名失败', err.message)
      this.load()
    } finally {
      this.setData({ busy: false })
    }
  },

  async withdraw(e) {
    const { id, shift } = e.currentTarget.dataset
    if (!(await ui.confirm('撤回报名', '撤回后可以再次报名。确定撤回？', '撤回'))) return
    try {
      await api.del(`/api/applications/${id}`, { loading: '处理中' })
      this.updateItem(shift, { application_status: 'WITHDRAWN' })
      ui.success('已撤回')
    } catch (err) {
      ui.alert('无法撤回', err.message)
      this.load()
    }
  }
})
