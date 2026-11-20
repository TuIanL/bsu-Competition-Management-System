const api = require('../../../utils/request')
const auth = require('../../../utils/auth')
const ui = require('../../../utils/ui')

Page({
  data: { id: null, shiftCount: 0, form: { name: '', required_skill: '', description: '' }, submitting: false },

  async onLoad(options) {
    if (!auth.guard('admin')) return
    const id = options.id ? +options.id : null
    wx.setNavigationBarTitle({ title: id ? '编辑岗位' : '新建岗位' })
    this.setData({ id })
    if (!id) return
    try {
      const r = await api.get(`/api/roles/${id}`)
      this.setData({
        form: { name: r.name, required_skill: r.required_skill || '', description: r.description || '' },
        shiftCount: r.shift_count
      })
    } catch (err) {
      ui.toast(err.message)
    }
  },

  onInput(e) {
    ui.bindInput(this, e)
  },

  async submit() {
    const f = this.data.form
    if (!f.name.trim()) return ui.toast('请填写岗位名称')
    if (this.data.submitting) return
    this.setData({ submitting: true })
    const payload = { name: f.name.trim(), required_skill: f.required_skill.trim(), description: f.description.trim() }
    try {
      if (this.data.id) await api.put(`/api/roles/${this.data.id}`, payload, { loading: '保存中' })
      else await api.post('/api/roles', payload, { loading: '保存中' })
      ui.success('已保存')
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (err) {
      ui.alert('无法保存', err.message)
    } finally {
      this.setData({ submitting: false })
    }
  },

  async remove() {
    if (!(await ui.confirm('删除岗位', '只有还没被班次使用的岗位才能删除。确定删除？', '删除'))) return
    try {
      await api.del(`/api/roles/${this.data.id}`, { loading: '删除中' })
      ui.success('已删除')
      setTimeout(() => wx.navigateBack(), 1000)
    } catch (err) {
      ui.alert('无法删除', err.message)
    }
  }
})
