import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AgentDetailModal from '../AgentDetailModal.vue'

function mountModal(agent, agentId = 'rover-mistral') {
  return mount(AgentDetailModal, {
    props: { agent, agentId },
  })
}

function without(obj, ...keys) {
  return Object.fromEntries(Object.entries(obj).filter(([k]) => !keys.includes(k)))
}

const fullAgent = {
  type: 'rover',
  mission: { objective: 'Collect samples' },
  position: [3, 7],
  battery: 0.85,
  visited: [[0, 0], [1, 1]],
  tools: [{ name: 'drill', description: 'Drill rock' }],
  inventory: [{ grade: 'high', quantity: 2 }],
  tasks: ['Move to zone B'],
  memory: ['Found basalt at (2,3)'],
  strategic_memory: [{ tick: 5, insight: 'Zone A depleted' }],
}

describe('AgentDetailModal', () => {
  it('renders fully populated agent without errors', () => {
    const w = mountModal(fullAgent)
    expect(w.text()).toContain('Collect samples')
    expect(w.text()).toContain('(3, 7)')
    expect(w.text()).toContain('85%')
    expect(w.text()).toContain('2')
  })

  it('renders safely when agent.mission is null', () => {
    const w = mountModal({ ...fullAgent, mission: null })
    expect(w.text()).toContain('None')
  })

  it('renders safely when agent.mission is undefined', () => {
    const w = mountModal(without(fullAgent, 'mission'))
    expect(w.text()).toContain('None')
  })

  it('renders safely when agent.visited is undefined', () => {
    const w = mountModal(without(fullAgent, 'visited'))
    expect(w.text()).toContain('Tiles visited')
    expect(w.text()).toContain('0')
  })

  it('renders safely when agent.visited is null', () => {
    const w = mountModal({ ...fullAgent, visited: null })
    expect(w.text()).toContain('0')
  })

  it('renders safely when agent.position is undefined', () => {
    const w = mountModal(without(fullAgent, 'position'))
    expect(w.text()).toContain('?')
  })

  it('renders safely when agent.position is null', () => {
    const w = mountModal({ ...fullAgent, position: null })
    expect(w.text()).toContain('?')
  })

  it('renders safely when agent.battery is undefined', () => {
    const w = mountModal(without(fullAgent, 'battery'))
    expect(w.text()).toContain('?')
  })

  it('renders safely when agent.battery is null', () => {
    const w = mountModal({ ...fullAgent, battery: null })
    expect(w.text()).toContain('?')
  })

  it('renders safely with minimal agent (empty object)', () => {
    const w = mountModal({})
    expect(w.text()).toContain('None')
    expect(w.text()).toContain('?')
  })

  it('renders safely when agent.tools is undefined', () => {
    const w = mountModal(without(fullAgent, 'tools'))
    expect(w.text()).toContain('No tools')
  })

  it('renders safely when agent.inventory is undefined', () => {
    const w = mountModal(without(fullAgent, 'inventory'))
    expect(w.text()).not.toContain('Inventory')
  })

  it('renders nothing inside modal when agent prop is null', () => {
    const w = mountModal(null)
    expect(w.find('.modal').exists()).toBe(false)
  })

  it('emits close on overlay click', async () => {
    const w = mountModal(fullAgent)
    await w.find('.modal-overlay').trigger('click')
    expect(w.emitted('close')).toBeTruthy()
  })

  it('emits close on button click', async () => {
    const w = mountModal(fullAgent)
    await w.find('.modal-close').trigger('click')
    expect(w.emitted('close')).toBeTruthy()
  })
})
