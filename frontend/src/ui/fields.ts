import type { CardField } from '../api/types'

export const FIELD_LABELS = {
  title: 'Название',
  context: 'Контекст',
  need: 'Потребность',
  users: 'Пользователи',
  data: 'Данные и материалы',
  constraints: 'Ограничения',
  expected_result: 'Ожидаемый результат',
  success_criteria: 'Критерии успеха',
  contact: 'Контакт',
  interaction_format: 'Формат взаимодействия',
} satisfies Record<CardField, string>

export const CARD_FIELDS = Object.keys(FIELD_LABELS) as CardField[]
