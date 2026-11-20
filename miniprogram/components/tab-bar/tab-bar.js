/**
 * 自定义底部导航：小程序原生 tabBar 不能按角色动态切换，
 * 所以管理端、志愿者端各用一组入口，用 redirectTo 切换（不堆叠页面栈）
 */
const MENUS = {
  admin: [
    { key: 'dashboard', text: '概览', url: '/pages/admin/dashboard/dashboard' },
    { key: 'shifts', text: '班次调度', url: '/pages/admin/shifts/shifts' },
    { key: 'volunteers', text: '志愿者', url: '/pages/admin/volunteers/volunteers' },
    { key: 'catalog', text: '赛事岗位', url: '/pages/admin/catalog/catalog' }
  ],
  volunteer: [
    { key: 'my-schedule', text: '我的班次', url: '/pages/volunteer/my-schedule/my-schedule' },
    { key: 'positions', text: '报名', url: '/pages/volunteer/positions/positions' },
    { key: 'my-hours', text: '志愿时长', url: '/pages/volunteer/my-hours/my-hours' }
  ]
}

Component({
  properties: {
    role: { type: String, value: 'admin' },
    current: { type: String, value: '' }
  },
  data: { items: [] },
  observers: {
    role(role) {
      this.setData({ items: MENUS[role] || [] })
    }
  },
  lifetimes: {
    attached() {
      this.setData({ items: MENUS[this.data.role] || [] })
    }
  },
  methods: {
    go(e) {
      const { key, url } = e.currentTarget.dataset
      if (key === this.data.current) return
      wx.redirectTo({ url })
    }
  }
})
