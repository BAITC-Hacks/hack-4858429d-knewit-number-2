import { useState } from 'react'
import { App, Badge, Button, Card, Input, Space, Tag, Typography, theme } from 'antd'
import { submitAnswers } from '../api/client'
import type { Task } from '../api/types'
import { FIELD_LABELS, LevelTag } from '../ui'

export function TaskClarification({ task, onBuilt }: { task: Task; onBuilt: (task: Task) => void }) {
  const { token } = theme.useToken()
  const { message } = App.useApp()
  const [answers, setAnswers] = useState<Record<string, string>>(() => Object.fromEntries(task.answers.map((answer) => [answer.question_id, answer.answer])))
  const [saving, setSaving] = useState(false)

  async function build() {
    if (saving) return
    if (!task.questions.some((question) => answers[question.id]?.trim())) {
      message.warning('Ответьте хотя бы на один вопрос')
      return
    }
    setSaving(true)
    try { onBuilt(await submitAnswers(task.id, task.questions.map((question) => ({ question_id: question.id, answer: answers[question.id] ?? '' })))) }
    catch { /* API-клиент показывает detail. */ }
    finally { setSaving(false) }
  }

  return (
    <div className="builder-grid">
      <Card>
        <Typography.Title level={4}>Ответьте на уточняющие вопросы</Typography.Title>
        <Typography.Paragraph type="secondary">Можно пропустить отдельные вопросы. Для формирования карточки нужен хотя бы один ответ.</Typography.Paragraph>
        <div className="question-list">
          {task.questions.map((question) => <Card key={question.id} size="small" className="question-card">
            <Space className="question-meta"><Tag>{FIELD_LABELS[question.field]}</Tag><Badge count={`+${question.points} баллов`} color={token.colorPrimary} /></Space>
            <Typography.Paragraph strong>{question.text}</Typography.Paragraph>
            {question.why && <Typography.Paragraph type="secondary">{question.why}</Typography.Paragraph>}
            <Input.TextArea aria-label={`Ответ на вопрос: ${question.text}`} value={answers[question.id] ?? ''}
              disabled={saving} onChange={(event) => setAnswers((current) => ({ ...current, [question.id]: event.target.value }))}
              autoSize={{ minRows: 2, maxRows: 6 }} maxLength={2000} showCount />
          </Card>)}
        </div>
        <Button type="primary" onClick={build} loading={saving}>Сформировать карточку</Button>
      </Card>
      <aside className="builder-aside"><Card>
        <Tag>Прогноз</Tag>
        <Typography.Title level={5}>{task.draft_rating ? `Оценка черновика: ${task.draft_rating.total}/100` : 'Оценка черновика пока недоступна'}</Typography.Title>
        {task.draft_rating && <LevelTag level={task.draft_rating.level} label={task.draft_rating.level_label} />}
        <Typography.Paragraph className="builder-caption" type="secondary">Итоговый рейтинг появится после подтверждения карточки.</Typography.Paragraph>
      </Card></aside>
    </div>
  )
}
