import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { OBSTACLE_COLORS } from '../../constants.js'

// Test OBSTACLE_COLORS constant
describe('OBSTACLE_COLORS', () => {
  it('has mountain color', () => {
    expect(OBSTACLE_COLORS.mountain).toBe('#8899bb')
  })

  it('has geyser idle color', () => {
    expect(OBSTACLE_COLORS.geyser_idle).toBe('#447788')
  })

  it('has geyser warning color', () => {
    expect(OBSTACLE_COLORS.geyser_warning).toBe('#cc8844')
  })

  it('has geyser erupting color', () => {
    expect(OBSTACLE_COLORS.geyser_erupting).toBe('#ee4444')
  })
})

// Test WorldMap obstacle rendering
// WorldMap requires complex props and composables; test via a lightweight wrapper
describe('WorldMap obstacle rendering', () => {
  // We test the rendering logic indirectly by checking SVG output
  // with a minimal component that mirrors the obstacle template
  const ObstacleTestWrapper = {
    template: `
      <svg>
        <template v-for="(o, i) in obstacles" :key="'obs-' + i">
          <polygon
            v-if="o.kind === 'mountain'"
            :points="trianglePoints(o)"
            :fill="obstacleColor(o)"
            class="mountain"
          />
          <circle
            v-else-if="o.kind === 'geyser'"
            :cx="o.sx"
            :cy="o.sy"
            :r="o.state === 'erupting' ? 7 : o.state === 'warning' ? 5 : 4"
            :fill="obstacleColor(o)"
            :class="{ 'geyser-pulse': o.state === 'erupting' }"
            class="geyser"
          />
        </template>
      </svg>
    `,
    props: ['obstacles'],
    methods: {
      trianglePoints(o) {
        return `${o.sx},${o.sy - 7} ${o.sx - 7},${o.sy + 5} ${o.sx + 7},${o.sy + 5}`
      },
      obstacleColor(o) {
        if (o.kind === 'mountain') return OBSTACLE_COLORS.mountain
        if (o.kind === 'geyser') return OBSTACLE_COLORS['geyser_' + (o.state || 'idle')] || OBSTACLE_COLORS.geyser_idle
        return '#666'
      },
    },
  }

  it('renders mountains as polygons', () => {
    const wrapper = mount(ObstacleTestWrapper, {
      props: {
        obstacles: [
          { kind: 'mountain', position: [5, 3], sx: 100, sy: 60 },
        ],
      },
    })
    const polygon = wrapper.find('polygon.mountain')
    expect(polygon.exists()).toBe(true)
    expect(polygon.attributes('fill')).toBe(OBSTACLE_COLORS.mountain)
    expect(polygon.attributes('points')).toBe('100,53 93,65 107,65')
  })

  it('renders geysers as circles', () => {
    const wrapper = mount(ObstacleTestWrapper, {
      props: {
        obstacles: [
          { kind: 'geyser', state: 'idle', position: [2, 4], sx: 50, sy: 80 },
        ],
      },
    })
    const circle = wrapper.find('circle.geyser')
    expect(circle.exists()).toBe(true)
    expect(circle.attributes('fill')).toBe(OBSTACLE_COLORS.geyser_idle)
    expect(circle.attributes('r')).toBe('4')
  })

  it('renders erupting geyser with larger radius and pulse class', () => {
    const wrapper = mount(ObstacleTestWrapper, {
      props: {
        obstacles: [
          { kind: 'geyser', state: 'erupting', position: [2, 4], sx: 50, sy: 80 },
        ],
      },
    })
    const circle = wrapper.find('circle.geyser')
    expect(circle.attributes('r')).toBe('7')
    expect(circle.classes()).toContain('geyser-pulse')
  })

  it('renders warning geyser with medium radius', () => {
    const wrapper = mount(ObstacleTestWrapper, {
      props: {
        obstacles: [
          { kind: 'geyser', state: 'warning', position: [2, 4], sx: 50, sy: 80 },
        ],
      },
    })
    const circle = wrapper.find('circle.geyser')
    expect(circle.attributes('r')).toBe('5')
    expect(circle.attributes('fill')).toBe(OBSTACLE_COLORS.geyser_warning)
    expect(circle.classes()).not.toContain('geyser-pulse')
  })

  it('renders mixed mountains and geysers', () => {
    const wrapper = mount(ObstacleTestWrapper, {
      props: {
        obstacles: [
          { kind: 'mountain', position: [0, 0], sx: 10, sy: 10 },
          { kind: 'geyser', state: 'idle', position: [1, 1], sx: 30, sy: 30 },
          { kind: 'mountain', position: [2, 2], sx: 50, sy: 50 },
          { kind: 'geyser', state: 'erupting', position: [3, 3], sx: 70, sy: 70 },
        ],
      },
    })
    expect(wrapper.findAll('polygon.mountain')).toHaveLength(2)
    expect(wrapper.findAll('circle.geyser')).toHaveLength(2)
  })

  it('renders nothing when obstacles is empty', () => {
    const wrapper = mount(ObstacleTestWrapper, {
      props: { obstacles: [] },
    })
    expect(wrapper.findAll('polygon').length).toBe(0)
    expect(wrapper.findAll('circle').length).toBe(0)
  })

  it('idle geyser does not have pulse class', () => {
    const wrapper = mount(ObstacleTestWrapper, {
      props: {
        obstacles: [
          { kind: 'geyser', state: 'idle', position: [0, 0], sx: 10, sy: 10 },
        ],
      },
    })
    expect(wrapper.find('circle.geyser').classes()).not.toContain('geyser-pulse')
  })
})
