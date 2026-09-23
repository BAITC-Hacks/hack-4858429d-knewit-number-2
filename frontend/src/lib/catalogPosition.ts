import type { CatalogItem, Task } from '../api/types'

// Only a position forecast; scores and levels are always returned by the API.
export function predictCatalogPosition(
  total: number,
  catalog: CatalogItem[],
  task?: Pick<Task, 'id' | 'published_at'>,
): number {
  return 1 + catalog.filter((item) => {
    if (item.id === task?.id) return false
    if (item.rating_total !== total) return item.rating_total > total
    // An unpublished task joins after all existing tasks with the same score.
    if (!task?.published_at) return true
    const timeDifference = Date.parse(item.published_at) - Date.parse(task.published_at)
    return timeDifference < 0 || (timeDifference === 0 && item.id < task.id)
  }).length
}
