const api = require('../../../utils/request')
const auth = require('../../../utils/auth')
const fmt = require('../../../utils/format')

Page({
  data: { summary: null, details: [], loading: true, error: '' },

  onShow() {
    if (!auth.guard('volunteer')) return
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  async load() {
    try {
      const d = await api.get('/api/volunteer/my-hours')
      this.setData({
        summary: { hours: d.total_hours, text: fmt.hoursText(d.total_minutes), count: d.completed_count },
        details: d.details.map((x) => Object.assign({}, x, {
          date: x.start_time.slice(0, 10),
          shiftHours: `${fmt.hm(x.start_time)}–${fmt.hm(x.end_time)}`,
          actual: `${fmt.hm(x.check_in_at)} 签到，${fmt.hm(x.check_out_at)} 签退`,
          durationText: fmt.hoursText(x.minutes)
        })),
        loading: false,
        error: ''
      })
    } catch (err) {
      this.setData({ loading: false, error: err.message })
    }
  }
})
