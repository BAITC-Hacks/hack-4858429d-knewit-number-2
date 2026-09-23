export type CardField = 'title' | 'context' | 'need' | 'users' | 'data' | 'constraints'
  | 'expected_result' | 'success_criteria' | 'contact' | 'interaction_format'

export interface TaskCard {
  title: string
  context: string
  need: string
  users: string
  data: string
  constraints: string
  expected_result: string
  success_criteria: string
  contact: string
  interaction_format: string
}
export type Evidence = Partial<Record<CardField, string | null>>
export interface Removed { field: CardField; reason: string }

export interface Question { id: string; field: CardField; text: string; why: string; points: number }
export interface Answer { question_id: string; answer: string }

export type Level = 'draft' | 'working' | 'ready' | 'priority'
export interface RatingCheck { label: string; field: CardField; points: number; passed: boolean; hint: string | null }
export interface RatingCategory { key: string; label: string; max: number; earned: number; checks: RatingCheck[] }
export interface MissingItem { field: CardField; hint: string; points: number }
export interface Rating {
  total: number
  level: Level
  level_label: string
  categories: RatingCategory[]
  missing: MissingItem[]
  next_level: { level: Level; label: string; threshold: number; points_needed: number } | null
}

export type TaskStatus = 'clarifying' | 'card_ready' | 'confirmed' | 'published'
export type AiMode = 'openai' | 'nvidia' | 'stub'

export interface Task {
  id: number; status: TaskStatus; business_name: string; industry: string
  draft_text: string; questions: Question[]; answers: Answer[]
  card: TaskCard; evidence: Evidence; removed: Removed[]
  draft_rating: Rating | null
  rating: Rating | null
  rating_history: { total: number; at: string }[]
  position: number | null
  proposals_count: number; ai_mode: AiMode | null
  created_at: string; published_at: string | null
}

export interface CatalogItem {
  id: number; title: string; industry: string; business_name: string; need_short: string
  rating_total: number; level: Level; level_label: string
  needs_clarification: boolean
  position: number; proposals_count: number; published_at: string
}

export interface Team { id: number; name: string; interests: string[]; skills: string[]; technologies: string[]; points: number }

export type ProposalStatus = 'pending' | 'selected' | 'rejected'
export interface Proposal {
  id: number; task_id: number; team_id: number; team_name: string
  idea: string; plan: string; deadline: string; prototype_url: string
  status: ProposalStatus; milestones_confirmed: number; created_at: string
}

export interface Recommendation { task: CatalogItem; reasons: string[] }
export interface DraftExample { id: number; industry: string; text: string; completeness: 'low' | 'medium' | 'high' }
