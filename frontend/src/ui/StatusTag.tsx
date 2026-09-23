import { Tag } from 'antd'
import type { ProposalStatus, TaskStatus } from '../api/types'

export const TASK_STATUSES: Record<TaskStatus, string> = {
  clarifying: 'Уточнение', card_ready: 'Карточка готова', confirmed: 'Подтверждена', published: 'Опубликована',
}
const PROPOSAL_STATUSES: Record<ProposalStatus, { label: string; color: string }> = {
  pending: { label: 'Ожидает решения', color: 'default' },
  selected: { label: 'Выбрана', color: 'success' },
  rejected: { label: 'Отклонена', color: 'error' },
}

export function TaskStatusTag({ status }: { status: TaskStatus }) {
  return <Tag>{TASK_STATUSES[status]}</Tag>
}

export function ProposalStatusTag({ status }: { status: ProposalStatus }) {
  const { label, color } = PROPOSAL_STATUSES[status]
  return <Tag color={color}>{label}</Tag>
}
