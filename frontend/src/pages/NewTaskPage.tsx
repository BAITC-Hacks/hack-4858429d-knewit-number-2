import { useCallback, useState } from 'react'
import { Alert, App, Button, Card, Form, Input, List, Modal, Select, Skeleton, Space, Steps, Typography } from 'antd'
import { Link, useSearchParams } from 'react-router-dom'
import { ApiError, createTask, getDraftExamples, getIndustries, getTask, publishTask, updateTaskCard } from '../api/client'
import type { DraftExample, Task, TaskCard } from '../api/types'
import { useRole } from '../context/RoleContext'
import { useResource } from '../hooks/useResource'
import { parseTaskId } from '../lib/taskPresentation'
import { AiModeTag, LoadError, RankChange } from '../ui'
import { RatingPanel } from '../components/RatingPanel'
import { TaskCardEditor } from '../components/TaskCardEditor'
import { TaskClarification } from '../components/TaskClarification'
import { TaskNotFound } from './TaskPage'

const steps = [{ title: 'Черновик' }, { title: 'Уточнение' }, { title: 'Карточка' }, { title: 'Публикация' }]
interface DraftValues { draft_text: string; industry: string; business_name?: string }

function DraftForm({ onCreated }: { onCreated: (task: Task) => void }) {
  const [form] = Form.useForm<DraftValues>()
  const { message } = App.useApp()
  const industries = useResource(getIndustries)
  const [examples, setExamples] = useState<DraftExample[]>([])
  const [examplesOpen, setExamplesOpen] = useState(false)
  const [examplesLoading, setExamplesLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  async function loadExamples() {
    setExamplesLoading(true)
    try {
      const items = await getDraftExamples()
      if (!items.length) { message.info('Примеры пока не загружены'); return }
      setExamples(items)
      setExamplesOpen(true)
    } catch { /* API-клиент показывает detail. */ }
    finally { setExamplesLoading(false) }
  }

  async function analyze(values: DraftValues) {
    if (saving) return
    setSaving(true)
    try { onCreated(await createTask(values)) }
    catch { /* Введённый черновик остаётся в форме. */ }
    finally { setSaving(false) }
  }

  return <>
    <Steps className="builder-steps" current={0} items={steps} />
    <Card className="builder-main-card">
      <Typography.Title level={4}>Опишите задачу своими словами</Typography.Title>
      {industries.error ? <LoadError title="Не удалось загрузить отрасли" onRetry={industries.reload} /> : null}
      <Form form={form} layout="vertical" onFinish={analyze} disabled={saving}>
        <Form.Item name="draft_text" label="Описание задачи" rules={[
          { required: true, whitespace: true, message: 'Опишите задачу' },
          { min: 20, transform: (value: string) => value?.trim(), message: 'Нужно минимум 20 символов' },
        ]}><Input.TextArea placeholder="Что происходит сейчас и что вы хотите изменить?" autoSize={{ minRows: 5, maxRows: 10 }} showCount maxLength={3000} /></Form.Item>
        <Form.Item name="industry" label="Отрасль" rules={[{ required: true, message: 'Выберите отрасль' }]}>
          <Select placeholder="Выберите отрасль" loading={industries.loading} showSearch options={(industries.data ?? []).map((value) => ({ value, label: value }))} />
        </Form.Item>
        <Form.Item name="business_name" label="Название компании (необязательно)"><Input placeholder="Как представить вашу компанию в каталоге" /></Form.Item>
        <Space><Button onClick={loadExamples} loading={examplesLoading}>Взять пример</Button><Button type="primary" htmlType="submit" loading={saving}>Проанализировать</Button></Space>
      </Form>
    </Card>
    <Modal title="Выберите пример черновика" open={examplesOpen} onCancel={() => setExamplesOpen(false)} footer={null}>
      <List dataSource={examples} renderItem={(example) => <List.Item actions={[<Button key="choose" type="link" onClick={() => {
        form.setFieldsValue({ draft_text: example.text, industry: example.industry }); setExamplesOpen(false)
      }}>Взять</Button>]}><List.Item.Meta title={example.industry} description={<Typography.Paragraph ellipsis={{ rows: 2 }}>{example.text}</Typography.Paragraph>} /></List.Item>} />
    </Modal>
  </>
}

function SavedBuilder({ id }: { id: number }) {
  const load = useCallback(() => getTask(id), [id])
  const { data: task, setData: setTask, error, loading, reload } = useResource(load)
  const [editing, setEditing] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [rankChange, setRankChange] = useState<{ from: number; to: number } | null>(null)
  const step = task?.status === 'clarifying' ? 1 : task?.status === 'card_ready' || editing ? 2 : 3

  async function confirm(card: TaskCard) {
    if (!task) return
    const updated = await updateTaskCard(id, card)
    setRankChange(task.position != null && updated.position != null && task.position !== updated.position
      ? { from: task.position, to: updated.position } : null)
    setTask(updated)
    setEditing(false)
    window.scrollTo({ top: 0 })
  }

  async function publish() {
    if (!task || task.status !== 'confirmed' || publishing) return
    setPublishing(true)
    try { setTask(await publishTask(id)); window.scrollTo({ top: 0 }) }
    catch { /* API-клиент показывает detail. */ }
    finally { setPublishing(false) }
  }

  if (loading) return <Skeleton active paragraph={{ rows: 6 }} />
  if (error instanceof ApiError && error.status === 404) return <TaskNotFound />
  if (error || !task) return <LoadError title="Не удалось загрузить черновик" onRetry={reload} />

  return <>
    <Space><AiModeTag mode={task.ai_mode} /><Link to={`/tasks/${task.id}`}>Страница задачи</Link></Space>
    <Steps className="builder-steps" current={step} items={steps} />
    {step === 1 && <TaskClarification task={task} onBuilt={(updated) => { setTask(updated); window.scrollTo({ top: 0 }) }} />}
    {step === 2 && <TaskCardEditor key={task.id} task={task} onConfirm={confirm}
      onCancel={task.rating ? () => setEditing(false) : undefined} />}
    {step === 3 && <div className="builder-grid">
      <Card className="builder-main-card">
        <Typography.Title level={4}>Карточка подтверждена</Typography.Title>
        {task.status === 'published' ? <Alert type="success" showIcon
          message={`Задача в каталоге на месте #${task.position}`}
          description={<Link to={`/tasks/${task.id}`}>Открыть страницу задачи</Link>} />
          : <Button type="primary" loading={publishing} onClick={publish}>Опубликовать</Button>}
        {rankChange && <RankChange {...rankChange} />}
        <Button className="builder-edit" onClick={() => { setRankChange(null); setEditing(true) }} disabled={publishing}>Редактировать карточку</Button>
      </Card>
      {task.rating && <aside className="builder-aside"><RatingPanel rating={task.rating} /></aside>}
    </div>}
  </>
}

export function NewTaskPage() {
  const { role, setRole } = useRole()
  const [params, setParams] = useSearchParams()
  const resume = params.get('task')
  const id = parseTaskId(resume)
  if (role !== 'business') return <Alert type="info" showIcon message="Конструктор доступен для роли «Бизнес»"
    action={<Button onClick={() => setRole('business')}>Переключиться на бизнес</Button>} />

  return <div className="task-builder">
    <Typography.Title level={2}>Конструктор задачи</Typography.Title>
    {resume != null ? id == null ? <TaskNotFound /> : <SavedBuilder key={id} id={id} />
      : <DraftForm onCreated={(task) => { setParams({ task: String(task.id) }, { replace: true }); window.scrollTo({ top: 0 }) }} />}
  </div>
}
