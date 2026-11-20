/**
 * 调度页：当前班次信息 → 已安排名单 → 报名意向 → 候选志愿者 → 调度反馈
 * 冲突 / 满员 / 重复 / 停用 的判断全部以后端返回为准，前端只负责清楚地展示原因
 */
const api = require('../../../utils/request')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')
const ui = require('../../../utils/ui')

function rosterView(p) {
  let status = { text: '待签到', cls: '' }
  if (p.status === 'COMPLETED') status = { text: `已完成 ${fmt.hm(p.check_in_at)}–${fmt.hm(p.check_out_at)}`, cls: 'chip-grass' }
  else if (p.check_in_at) status = { text: `${fmt.hm(p.check_in_at)} 已签到`, cls: 'chip-ball' }
  return Object.assign({}, p, { statusText: status.text, statusCls: status.cls, canCancel: p.status === 'ASSIGNED' && !p.check_in_at })
}

function candidateView(c) {
  const tags = []
  if (c.status !== 'ACTIVE') tags.push({ text: '已停用', cls: 'chip-grey' })
  if (c.conflict) tags.push({ text: `时间冲突：${c.conflict}`, cls: 'chip-clay' })
  if (c.applied) tags.push({ text: '已报名', cls: '' })
  if (c.skill_match) tags.push({ text: '技能匹配', cls: 'chip-grass' })
  return Object.assign({}, c, { tags })
}

Page({
  data: {
    id: null,
    shift: null,
    time: null,
    roster: [],
    applications: [],
    candidates: [],
    keyword: '',
    loading: true,
    error: '',
    busy: false
  },

  onLoad(options) {
    this.setData({ id: +options.id })
  },

  onShow() {
    if (!auth.guard('admin')) return
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  async load() {
    const id = this.data.id
    try {
      const [cand, roster, applications] = await Promise.all([
        api.get(`/api/shifts/${id}/candidates`, this.data.keyword ? { keyword: this.data.keyword } : {}),
        api.get(`/api/shifts/${id}/roster`),
        api.get(`/api/shifts/${id}/applications`)
      ])
      const shift = cand.shift
      this.setData({
        shift,
        time: fmt.shiftTime(shift.start_time, shift.end_time),
        phaseText: fmt.label('phase', shift.phase),
        roster: roster.map(rosterView),
        applications: applications.map((a) => Object.assign({}, a, { statusText: fmt.label('application', a.status) })),
        candidates: cand.candidates.map(candidateView),
        loading: false,
        error: ''
      })
    } catch (err) {
      this.setData({ loading: false, error: err.message })
    }
  },

  onKeyword(e) {
    this.setData({ keyword: e.detail.value })
  },

  search() {
    this.load()
  },

  async assign(e) {
    const { id, name } = e.currentTarget.dataset
    if (this.data.busy) return
    this.setData({ busy: true })
    try {
      const r = await api.post('/api/assignments', { volunteer_id: id, shift_id: this.data.id }, { loading: '安排中' })
      ui.success(`已安排 ${r.volunteer_name}`)
      await this.load()
    } catch (err) {
      ui.alert(`无法安排 ${name}`, err.message)
    } finally {
      this.setData({ busy: false })
    }
  },

  async cancel(e) {
    const { id, name } = e.currentTarget.dataset
    if (!(await ui.confirm('取消安排', `确定取消 ${name} 在本班次的安排吗？记录会保留为“已取消”。`, '取消安排'))) return
    try {
      await api.del(`/api/assignments/${id}`, { loading: '处理中' })
      ui.success('已取消')
      await this.load()
    } catch (err) {
      ui.alert('无法取消', err.message)
    }
  },

  async reject(e) {
    const { id, name } = e.currentTarget.dataset
    if (!(await ui.confirm('拒绝报名', `拒绝后 ${name} 不能再报名这个班次。确定拒绝？`, '拒绝'))) return
    try {
      await api.post(`/api/applications/${id}/reject`, {}, { loading: '处理中' })
      ui.success('已拒绝')
      await this.load()
    } catch (err) {
      ui.alert('无法拒绝', err.message)
    }
  },

  edit() {
    wx.navigateTo({ url: `/pages/admin/shift-edit/shift-edit?id=${this.data.id}` })
  }
})
