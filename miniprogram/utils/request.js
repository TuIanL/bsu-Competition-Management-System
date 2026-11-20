/**
 * 统一请求封装（双端共用，不为志愿者端另写一套）
 * - 自动拼接 BASE_URL、携带 Authorization: Bearer <token>
 * - 后端统一返回 {success, data} / {success:false, message}
 * - 成功 resolve(data)；失败 reject(Error)，error.message 为可直接展示的中文提示
 * - 401（未登录/过期）统一清除登录态并回到登录页
 */
const { BASE_URL } = require('../config')
const auth = require('./auth')

let redirecting = false

function makeError(message, status) {
  const err = new Error(message)
  err.status = status
  return err
}

function handleUnauthorized(message) {
  if (redirecting) return
  redirecting = true
  auth.clear()
  wx.showToast({ title: message || '请先登录', icon: 'none' })
  setTimeout(() => {
    redirecting = false
    wx.reLaunch({ url: '/pages/login/login' })
  }, 800)
}

function request(method, url, data, options) {
  const opts = options || {}
  if (opts.loading) wx.showLoading({ title: opts.loading, mask: true })
  return new Promise((resolve, reject) => {
    const header = { 'Content-Type': 'application/json' }
    const token = auth.getToken()
    if (token) header.Authorization = 'Bearer ' + token
    wx.request({
      url: BASE_URL + url,
      method,
      data,
      header,
      timeout: 10000,
      success(res) {
        const body = res.data && typeof res.data === 'object' ? res.data : {}
        if (res.statusCode === 401 && url !== '/api/login') {
          handleUnauthorized(body.message)
          reject(makeError(body.message || '请先登录', 401))
        } else if (body.success) {
          resolve(body.data)
        } else {
          reject(makeError(body.message || `请求失败（${res.statusCode}）`, res.statusCode))
        }
      },
      fail() {
        reject(makeError('连不上服务器：请确认后端已启动，且 config.js 中的地址正确', 0))
      },
      complete() {
        if (opts.loading) wx.hideLoading()
      }
    })
  })
}

module.exports = {
  get: (url, data, opts) => request('GET', url, data, opts),
  post: (url, data, opts) => request('POST', url, data || {}, opts),
  put: (url, data, opts) => request('PUT', url, data, opts),
  del: (url, opts) => request('DELETE', url, undefined, opts)
}
