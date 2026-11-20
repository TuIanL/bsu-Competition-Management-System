/** 时间与状态的展示格式（WXML 里不能调用函数，所以在 JS 中预先算好） */
const WEEK = '日一二三四五六'

function toDate(dateStr) {
  // 不用 new Date('YYYY-MM-DD HH:MM:SS')：iOS 不支持带空格的格式
  return new Date(+dateStr.slice(0, 4), +dateStr.slice(5, 7) - 1, +dateStr.slice(8, 10))
}

function pad(n) {
  return n < 10 ? '0' + n : '' + n
}

function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function nowStr() {
  const d = new Date()
  return `${todayStr()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/** 2026-11-20 → 今天 / 明天 / 昨天 / 11月20日 周五 */
function dayLabel(dateStr) {
  const target = toDate(dateStr)
  const diff = Math.round((target - toDate(todayStr())) / 86400000)
  const names = { '-1': '昨天', 0: '今天', 1: '明天', 2: '后天' }
  if (names[diff] !== undefined) return names[diff]
  return `${target.getMonth() + 1}月${target.getDate()}日 周${WEEK[target.getDay()]}`
}

function hm(dt) {
  return dt ? dt.slice(11, 16) : ''
}

/** 班次时间：{ day: '明天', hours: '09:00–13:00', full: '明天 09:00–13:00' }，跨天自动标注 */
function shiftTime(start, end) {
  const sameDay = start.slice(0, 10) === end.slice(0, 10)
  const day = dayLabel(start)
  const hours = sameDay ? `${hm(start)}–${hm(end)}` : `${hm(start)}–次日${hm(end)}`
  return { day, hours, full: `${day} ${hours}` }
}

const LABELS = {
  assignment: { ASSIGNED: '待签到', COMPLETED: '已完成', CANCELLED: '已取消' },
  application: { PENDING: '已报名，待安排', APPROVED: '已安排', REJECTED: '未通过', WITHDRAWN: '已撤回' },
  volunteer: { ACTIVE: '正常', INACTIVE: '已停用' },
  event: { PLANNED: '未开始', ONGOING: '进行中', FINISHED: '已结束' },
  phase: { upcoming: '未开始', ongoing: '进行中', ended: '已结束' }
}

function label(kind, value) {
  return (LABELS[kind] && LABELS[kind][value]) || value || ''
}

function hoursText(minutes) {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (!h) return `${m} 分钟`
  return m ? `${h} 小时 ${m} 分` : `${h} 小时`
}

module.exports = { todayStr, nowStr, dayLabel, hm, shiftTime, label, LABELS, hoursText, pad }
