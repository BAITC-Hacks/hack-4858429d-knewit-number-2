import type { Task } from '../api/types'

export function parseTaskId(value: string | undefined | null): number | null {
  if (!value || !/^[1-9]\d*$/.test(value)) return null
  const id = Number(value)
  return Number.isSafeInteger(id) ? id : null
}

export function taskTitle(task: Pick<Task, 'id' | 'card'>): string {
  return task.card.title.trim() || `Черновик №${task.id}`
}

export function ratingChangeText(before: Task, after: Task): string {
  const position = (value: number | null) => value == null ? '—' : `#${value}`
  return `Рейтинг ${before.rating?.total ?? '—'} → ${after.rating?.total ?? '—'}, место ${position(before.position)} → ${position(after.position)}`
}

export function safeExternalUrl(value: string): string | null {
  try {
    const url = new URL(value.trim())
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null
  } catch {
    return null
  }
}
