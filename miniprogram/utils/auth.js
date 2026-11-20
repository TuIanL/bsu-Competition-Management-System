/** 登录态的本地存储（token + 角色 + 名字），所有页面通过这里读取 */
const KEY = 'auth'

function getUser() {
  try {
    return wx.getStorageSync(KEY) || null
  } catch (e) {
    return null
  }
}

function getToken() {
  const user = getUser()
  return user ? user.token : ''
}

function save(user) {
  wx.setStorageSync(KEY, user)
  getApp().globalData.user = user
}

function clear() {
  wx.removeStorageSync(KEY)
  getApp().globalData.user = null
}

function homeOf(role) {
  return role === 'admin' ? '/pages/admin/dashboard/dashboard' : '/pages/volunteer/my-schedule/my-schedule'
}

/** 页面守卫：未登录或角色不符时回到登录页，返回 false */
function guard(role) {
  const user = getUser()
  if (!user || (role && user.role !== role)) {
    wx.reLaunch({ url: '/pages/login/login' })
    return false
  }
  return true
}

module.exports = { getUser, getToken, save, clear, homeOf, guard }
