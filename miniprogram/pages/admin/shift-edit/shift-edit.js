const api = require('../../../utils/request')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')
const ui = require('../../../utils/ui')

function addHours(date, time, hours) {
  const d = new Date(+date.slice(0, 4), +date.slice(5, 7) - 1, +date.slice(8, 10), +time.slice(0, 2), +time.slice(3, 5))
  d.setHours(d.getHours() + hours)
  return {
    date: `${d.getFullYear()}-${fmt.pad(d.getMonth() + 1)}-${fmt.pad(d.getDate())}`,
    time: `${fmt.pad(d.getHours())}:${fmt.pad(d.getMinutes())}`
  }
}

Page({
  data: {
    id: null,
    events: [],
    roles: [],
    eventIndex: -1,
    roleIndex: -1,
    form: { start_date: '', start_time: '09:00', end_date: '', end_time: '13:00', required_count: '3', note: '' },
    assignedCount: 0,
    submitting: false
  },

  async onLoad(options) {
    if (!auth.guard('admin')) return
    const id = options.id ? +options.id : null
    wx.setNavigationBarTitle({ title: id ? '编辑班次' : '新建班次' })
    const today = fmt.todayStr()
    this.setData({ id, 'form.start_date': today, 'form.end_date': today })
    try {
      const [events, roles] = await Promise.all([api.get('/api/events'), api.get('/api/roles')])
      const usable = events.filter((e) => e.status !== 'FINISHED' || id)
      this.setData({ events: usable, roles })
      if (id) await this.loadShift(id)
      else if (options.event_id) this.setData({ eventIndex: usable.findIndex((e) => e.id === +options.event_id) })
    } catch (err) {
      ui.toast(err.message)
    }
  },

  async loadShift(id) {
    const s = await api.get(`/api/shifts/${id}`)
    this.setData({
      eventIndex: this.data.events.findIndex((e) => e.id === s.event_id),
      roleIndex: this.data.roles.findIndex((r) => r.id === s.role_id),
      assignedCount: s.assigned_count,
      form: {
        start_date: s.start_time.slice(0, 10),
        start_time: s.start_time.slice(11, 16),
        end_date: s.end_time.slice(0, 10),
        end_time: s.end_time.slice(11, 16),
        required_count: String(s.required_count),
        note: s.note || ''
      }
    })
  },

  onInput(e) {
    ui.bindInput(this, e)
  },

  pickEvent(e) {
    this.setData({ eventIndex: +e.detail.value })
  },

  pickRole(e) {
    this.setData({ roleIndex: +e.detail.value })
  },

  pickTime(e) {
    const field = e.currentTarget.dataset.field
    const update = { ['form.' + field]: e.detail.value }
    // 改开始时间后，结束时间若不晚于开始，自动顺延 4 小时，减少来回改
    if (field === 'start_date' || field === 'start_time') {
      const f = Object.assign({}, this.data.form, { [field]: e.detail.value })
      if (`${f.end_date} ${f.end_time}` <= `${f.start_date} ${f.start_time}`) {
        const end = addHours(f.start_date, f.start_time, 4)
        update['form.end_date'] = end.date
        update['form.end_time'] = end.time
      }
    }
    this.setData(update)
  },

  async submit() {
    const { form, events, roles, eventIndex, roleIndex, id } = this.data
    if (eventIndex < 0) return ui.toast('请选择赛事')
    if (roleIndex < 0) return ui.toast('请选择岗位')
    const start = `${form.start_date} ${form.start_time}`
    const end = `${form.end_date} ${form.end_time}`
    if (end <= start) return ui.toast('结束时间必须晚于开始时间')
    const count = parseInt(form.required_count, 10)
    if (!(count > 0)) return ui.toast('需求人数必须大于 0')
    const payload = {
      event_id: events[eventIndex].id,
      role_id: roles[roleIndex].id,
      start_time: start,
      end_time: end,
      required_count: count,
      note: form.note
    }
    if (this.data.submitting) return
    this.setData({ submitting: true })
    try {
      if (id) await api.put(`/api/shifts/${id}`, payload, { loading: '保存中' })
      else await api.post('/api/shifts', payload, { loading: '保存中' })
      ui.success(id ? '已保存' : '班次已创建')
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (err) {
      ui.alert('无法保存', err.message)
    } finally {
      this.setData({ submitting: false })
    }
  },

  async remove() {
    if (!(await ui.confirm('删除班次', '只有没有任何排班和报名记录的班次才能删除。确定删除？', '删除'))) return
    try {
      await api.del(`/api/shifts/${this.data.id}`, { loading: '删除中' })
      ui.success('已删除')
      setTimeout(() => wx.navigateBack({ delta: 2 }), 1000)
    } catch (err) {
      ui.alert('无法删除', err.message)
    }
  }
})
