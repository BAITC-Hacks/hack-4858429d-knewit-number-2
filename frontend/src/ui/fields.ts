import type { CardField } from '../api/types'

export const FIELD_LABELS = {
  title: 'Название',
  context: 'Контекст',
  need: 'Потребность',
  users: 'Для кого решение',
  data: 'Доступные данные',
  constraints: 'Ограничения',
  expected_result: 'Ожидаемый результат',
  success_criteria: 'Критерии успеха',
  contact: 'Контакт',
  interaction_format: 'Формат взаимодействия',
} satisfies Record<CardField, string>
