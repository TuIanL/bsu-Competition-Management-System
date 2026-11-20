const auth = require('./utils/auth')

App({
  onLaunch() {
    // 已登录则直接进入对应端首页（登录页本身也会再判断一次）
    this.globalData.user = auth.getUser()
  },
  globalData: {
    user: null
  }
})
