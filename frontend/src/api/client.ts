import { notifyError } from './notify'
import type {
  Answer,
  CatalogItem,
  DraftExample,
  Level,
  Proposal,
  Rating,
  Recommendation,
  Task,
  TaskCard,
  Team,
} from './types'

function errorDetail(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = body.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) return String(item.msg)
        return String(item)
      }).join('; ')
    }
    if (detail != null) return String(detail)
  }
  return fallback
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    })
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Не удалось связаться с сервером'
    notifyError(detail)
    throw error
  }

  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = errorDetail(body, `Ошибка запроса (${response.status})`)
    notifyError(detail)
    throw new Error(detail)
  }
  return body as T
}

const json = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) })

export const createTask = (body: { draft_text: string; industry: string; business_name?: string }) =>
  request<Task>('/api/tasks', json(body))

export const submitAnswers = (id: number, answers: Answer[]) =>
  request<Task>(`/api/tasks/${id}/answers`, json({ answers }))

export const previewRating = (card: TaskCard) =>
  request<Rating>('/api/rating/preview', json(card))

export const updateTaskCard = (id: number, card: TaskCard) =>
  request<Task>(`/api/tasks/${id}/card`, { method: 'PUT', body: JSON.stringify(card) })

export const publishTask = (id: number) =>
  request<Task>(`/api/tasks/${id}/publish`, { method: 'POST' })

export const getTasks = () => request<Task[]>('/api/tasks')
export const getTask = (id: number) => request<Task>(`/api/tasks/${id}`)

export function getCatalog(filters: { industry?: string; level?: Level } = {}) {
  const params = new URLSearchParams()
  if (filters.industry) params.set('industry', filters.industry)
  if (filters.level) params.set('level', filters.level)
  const query = params.toString()
  return request<CatalogItem[]>(`/api/catalog${query ? `?${query}` : ''}`)
}

export const getIndustries = () => request<string[]>('/api/industries')
export const getDraftExamples = () => request<DraftExample[]>('/api/examples/drafts')
export const getTeams = () => request<Team[]>('/api/teams')
export const getTeamRecommendations = (id: number) =>
  request<Recommendation[]>(`/api/teams/${id}/recommendations`)

export const createProposal = (
  taskId: number,
  body: { team_id: number; idea: string; plan: string; deadline: string; prototype_url: string },
) => request<Proposal>(`/api/tasks/${taskId}/proposals`, json(body))

export const getTaskProposals = (taskId: number) =>
  request<Proposal[]>(`/api/tasks/${taskId}/proposals`)

export const decideProposal = (id: number, decision: 'selected' | 'rejected') =>
  request<Proposal>(`/api/proposals/${id}/decision`, json({ decision }))

export const confirmMilestone = (id: number) =>
  request<Proposal>(`/api/proposals/${id}/milestone`, { method: 'POST' })
