/** 交互反馈的统一写法 */
function toast(title, icon) {
  wx.showToast({ title, icon: icon || 'none', duration: 2000 })
}

function success(title) {
  wx.showToast({ title, icon: 'success', duration: 1500 })
}

/** 业务被拒绝时用弹窗，原因完整可读（截图演示也清楚） */
function alert(title, content) {
  return new Promise((resolve) => {
    wx.showModal({ title, content, showCancel: false, confirmText: '知道了', success: () => resolve() })
  })
}

/** 高风险操作二次确认，返回 Promise<boolean> */
function confirm(title, content, confirmText) {
  return new Promise((resolve) => {
    wx.showModal({
      title,
      content,
      confirmText: confirmText || '确定',
      confirmColor: '#C2452D',
      success: (res) => resolve(!!res.confirm),
      fail: () => resolve(false)
    })
  })
}

/** 表单输入通用处理：<input data-field="name" bindinput="onInput"> */
function bindInput(page, e) {
  page.setData({ ['form.' + e.currentTarget.dataset.field]: e.detail.value })
}

module.exports = { toast, success, alert, confirm, bindInput }
