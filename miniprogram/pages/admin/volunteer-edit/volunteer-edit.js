const api = require('../../../utils/request')
const auth = require('../../../utils/auth')
const ui = require('../../../utils/ui')

Page({
  data: {
    id: null,
    form: { student_no: '', name: '', phone: '', skill: '', status: 'ACTIVE' },
    stats: null,
    submitting: false
  },

  async onLoad(options) {
    if (!auth.guard('admin')) return
    const id = options.id ? +options.id : null
    this.setData({ id })
    wx.setNavigationBarTitle({ title: id ? '编辑志愿者' : '新增志愿者' })
    if (id) {
      try {
        const v = await api.get(`/api/volunteers/${id}`)
        this.setData({
          form: { student_no: v.student_no, name: v.name, phone: v.phone || '', skill: v.skill || '', status: v.status },
          stats: { assignment: v.assignment_count, completed: v.completed_count }
        })
      } catch (err) {
        ui.toast(err.message)
      }
    }
  },

  onInput(e) {
    ui.bindInput(this, e)
  },

  toggleStatus(e) {
    this.setData({ 'form.status': e.detail.value ? 'ACTIVE' : 'INACTIVE' })
  },

  async submit() {
    const f = this.data.form
    if (!f.student_no.trim()) return ui.toast('请填写学号')
    if (!/^[A-Za-z0-9]{6,20}$/.test(f.student_no.trim())) return ui.toast('学号应为 6–20 位字母或数字')
    if (!f.name.trim()) return ui.toast('请填写姓名')
    if (this.data.submitting) return
    this.setData({ submitting: true })
    const payload = {
      student_no: f.student_no.trim(), name: f.name.trim(), phone: f.phone.trim(), skill: f.skill.trim(), status: f.status
    }
    try {
      if (this.data.id) {
        const r = await api.put(`/api/volunteers/${this.data.id}`, payload, { loading: '保存中' })
        if (r.status === 'INACTIVE' && r.future_assignment_count > 0) {
          await ui.alert('已停用', `该志愿者还有 ${r.future_assignment_count} 个未结束的班次，请到对应班次的调度页取消安排。`)
        } else {
          ui.success('已保存')
        }
      } else {
        await api.post('/api/volunteers', payload, { loading: '保存中' })
        await ui.alert('已新增', `初始密码为学号后六位：${payload.student_no.slice(-6)}`)
      }
      wx.navigateBack()
    } catch (err) {
      ui.alert('无法保存', err.message)
    } finally {
      this.setData({ submitting: false })
    }
  },

  async resetPassword() {
    if (!(await ui.confirm('重置密码', '密码将恢复为学号后六位。确定重置？', '重置'))) return
    try {
      const r = await api.post(`/api/volunteers/${this.data.id}/reset-password`, {}, { loading: '处理中' })
      ui.alert('已重置', r.message)
    } catch (err) {
      ui.toast(err.message)
    }
  }
})
