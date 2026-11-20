/**
 * 座位格：每个格子是一个名额，蓝色=已安排，空心=缺口。
 * 人数超过 12 时改为比例条，避免一行放不下。
 */
const MAX_SEATS = 12

Component({
  properties: {
    required: { type: Number, value: 0 },
    assigned: { type: Number, value: 0 },
    compact: { type: Boolean, value: false }
  },
  data: { seats: [], percent: 0, gap: 0, asBar: false },
  observers: {
    'required, assigned'(required, assigned) {
      const gap = Math.max(0, required - assigned)
      const asBar = required > MAX_SEATS
      const seats = []
      if (!asBar) {
        for (let i = 0; i < required; i++) seats.push(i < assigned)
      }
      this.setData({
        seats,
        asBar,
        gap,
        percent: required ? Math.min(100, Math.round((assigned / required) * 100)) : 0
      })
    }
  }
})
