const api = require('../../utils/request')
const auth = require('../../utils/auth')
const ui = require('../../utils/ui')

Page({
  data: {
    form: { username: '', password: '' },
    submitting: false,
    showPwd: false,
    demos: [
      { label: '组委会管理员', username: 'admin_zhongwang', password: 'admin123' },
      { label: '志愿者（今天有班次）', username: '20260002', password: '260002' }
    ]
  },

  onLoad() {
    const user = auth.getUser()
    if (user) wx.reLaunch({ url: auth.homeOf(user.role) })
  },

  onInput(e) {
    ui.bindInput(this, e)
  },

  togglePwd() {
    this.setData({ showPwd: !this.data.showPwd })
  },

  fillDemo(e) {
    const demo = this.data.demos[e.currentTarget.dataset.index]
    this.setData({ form: { username: demo.username, password: demo.password } })
  },

  async submit() {
    const { username, password } = this.data.form
    if (!username.trim() || !password) {
      ui.toast('请输入账号和密码')
      return
    }
    if (this.data.submitting) return
    this.setData({ submitting: true })
    try {
      const user = await api.post('/api/login', { username: username.trim(), password }, { loading: '登录中' })
      auth.save(user)
      wx.reLaunch({ url: auth.homeOf(user.role) })
    } catch (err) {
      ui.toast(err.message)
    } finally {
      this.setData({ submitting: false })
    }
  }
})
