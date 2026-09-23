import type { Level } from '../api/types'

export const LEVELS = {
  draft: { label: 'Черновик', color: '#8A94A6' },
  working: { label: 'Рабочая', color: '#3B82F6' },
  ready: { label: 'Готовая', color: '#10A37F' },
  priority: { label: 'Приоритетная', color: '#E8A317' },
} satisfies Record<Level, { label: string; color: string }>
