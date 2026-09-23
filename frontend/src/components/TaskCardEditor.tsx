import { useEffect, useState } from 'react'
import { Alert, Button, Card, Form, Input, Space, Spin, Typography } from 'antd'
import { getCatalog, previewRating } from '../api/client'
import type { Rating, Task, TaskCard } from '../api/types'
import { useResource } from '../hooks/useResource'
import { predictCatalogPosition } from '../lib/catalogPosition'
import { CARD_FIELDS, EvidenceNote, FIELD_LABELS, LoadError } from '../ui'
import { RatingPanel } from './RatingPanel'

interface TaskCardEditorProps {
  task: Task
  onConfirm: (card: TaskCard) => Promise<void>
  onCancel?: () => void
  confirmLabel?: string
}

export function TaskCardEditor({ task, onConfirm, onCancel, confirmLabel = 'Подтвердить карточку' }: TaskCardEditorProps) {
  const [form] = Form.useForm<TaskCard>()
  const [draft, setDraft] = useState(task.card)
  const [preview, setPreview] = useState<Rating | null>(null)
  const [previewLoading, setPreviewLoading] = useState(true)
  const [revision, setRevision] = useState(0)
  const [saving, setSaving] = useState(false)
  const catalog = useResource(getCatalog)

  useEffect(() => {
    let active = true
    setPreviewLoading(true)
    const timer = window.setTimeout(() => {
      previewRating(draft)
        .then((value) => { if (active) setPreview(value) })
        .catch(() => { if (active) setPreview(null) })
        .finally(() => { if (active) setPreviewLoading(false) })
    }, 400)
    return () => { active = false; window.clearTimeout(timer) }
  }, [draft, revision])

  async function save(card: TaskCard) {
    if (saving) return
    setSaving(true)
    try { await onConfirm({ ...card, title: card.title.trim() }) }
    catch { /* API-клиент уже показал ошибку; введённые данные остаются в форме. */ }
    finally { setSaving(false) }
  }

  const position = preview && catalog.data && !previewLoading && !catalog.loading
    ? predictCatalogPosition(preview.total, catalog.data, task) : null

  return (
    <div className="builder-grid task-builder">
      <Card className="builder-main-card">
        <Typography.Title level={4}>Проверьте и дополните карточку</Typography.Title>
        {task.removed.length > 0 && <Alert className="builder-alert" type="warning" showIcon
          message={`ИИ не стал заполнять: ${task.removed.map((item) => `${FIELD_LABELS[item.field]} — ${item.reason}`).join('; ')}`} />}
        <Form form={form} layout="vertical" initialValues={task.card} disabled={saving}
          onValuesChange={(_, values: TaskCard) => { setPreviewLoading(true); setDraft(values) }} onFinish={save}>
          {CARD_FIELDS.map((field) => (
            <Form.Item key={field} name={field} label={FIELD_LABELS[field]} required={field === 'title'}
              rules={field === 'title' ? [{ validator: (_, value: string) => value?.trim().length >= 3 && value.trim().length <= 120
                ? Promise.resolve() : Promise.reject(new Error('Название должно содержать от 3 до 120 символов')) }] : undefined}
              extra={draft[field] === task.card[field] ? <EvidenceNote evidence={task.evidence[field]} /> : undefined}>
              {field === 'title' ? <Input maxLength={120} showCount />
                : <Input.TextArea autoSize={{ minRows: 2, maxRows: 6 }} maxLength={2000} showCount />}
            </Form.Item>
          ))}
          <Space>
            <Button type="primary" htmlType="submit" loading={saving}>{confirmLabel}</Button>
            {onCancel && <Button onClick={onCancel} disabled={saving}>Отмена</Button>}
          </Space>
        </Form>
      </Card>
      <aside className="builder-aside">
        <Card size="small" title="Прогноз места в каталоге" className="builder-position">
          {catalog.error ? <LoadError title="Не удалось загрузить каталог" onRetry={catalog.reload} /> : (
            <Typography.Paragraph strong={position != null}>
              {position != null ? `#${position}` : catalog.loading || previewLoading ? 'Обновляем прогноз…' : 'Прогноз места недоступен'}
            </Typography.Paragraph>
          )}
          <Typography.Text type="secondary">По полному каталогу. Фактическое место определит сервер после подтверждения и публикации.</Typography.Text>
        </Card>
        <Spin spinning={previewLoading}>
          {preview ? <RatingPanel rating={preview} preview /> : (
            <Card title="Прогноз рейтинга">
              {previewLoading ? 'Расчёт рейтинга…' : <LoadError title="Не удалось получить прогноз" onRetry={() => setRevision((value) => value + 1)} />}
            </Card>
          )}
        </Spin>
      </aside>
    </div>
  )
}
