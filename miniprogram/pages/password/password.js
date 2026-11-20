const api = require('../../utils/request')
const auth = require('../../utils/auth')
const ui = require('../../utils/ui')

Page({
  data: { form: { old_password: '', new_password: '', confirm: '' }, submitting: false },

  onLoad() {
    auth.guard()
  },

  onInput(e) {
    ui.bindInput(this, e)
  },

  async submit() {
    const f = this.data.form
    if (!f.old_password || !f.new_password) return ui.toast('请填写原密码和新密码')
    if (f.new_password.length < 6) return ui.toast('新密码至少 6 位')
    if (f.new_password !== f.confirm) return ui.toast('两次输入的新密码不一致')
    if (this.data.submitting) return
    this.setData({ submitting: true })
    try {
      await api.post('/api/password', { old_password: f.old_password, new_password: f.new_password }, { loading: '保存中' })
      const user = auth.getUser()
      if (user) auth.save(Object.assign({}, user, { must_change_password: false }))
      ui.success('密码已修改')
      setTimeout(() => wx.navigateBack(), 1200)
    } catch (err) {
      ui.toast(err.message)
    } finally {
      this.setData({ submitting: false })
    }
  }
})
