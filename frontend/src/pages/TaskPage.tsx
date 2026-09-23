import { useCallback, useEffect, useState } from 'react'
import { Alert, App, Button, Card, Result, Skeleton, Space, Typography } from 'antd'
import { Link, useParams } from 'react-router-dom'
import { ApiError, getTask, publishTask, updateTaskCard } from '../api/client'
import type { TaskCard } from '../api/types'
import { useRole } from '../context/RoleContext'
import { useResource } from '../hooks/useResource'
import { parseTaskId, ratingChangeText, taskTitle } from '../lib/taskPresentation'
import { AiModeTag, CARD_FIELDS, EvidenceNote, FIELD_LABELS, LoadError, RankBadge, RankChange, TaskStatusTag } from '../ui'
import { Proposals } from '../components/Proposals'
import { RatingPanel } from '../components/RatingPanel'
import { TaskCardEditor } from '../components/TaskCardEditor'

export function TaskNotFound() {
  return <Result status="404" title="Задача не найдена" subTitle="Проверьте ссылку или выберите задачу в каталоге."
    extra={<Link to="/">Вернуться в каталог</Link>} />
}

function TaskDetails({ id }: { id: number }) {
  const { role } = useRole()
  const { notification, message } = App.useApp()
  const load = useCallback(() => getTask(id), [id])
  const { data: task, setData: setTask, error, loading, reload } = useResource(load)
  const [editing, setEditing] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [rankChange, setRankChange] = useState<{ from: number; to: number } | null>(null)

  useEffect(() => { if (role !== 'business') setEditing(false) }, [role])
  const setProposalCount = useCallback((count: number) => setTask((current) => current && current.proposals_count !== count
    ? { ...current, proposals_count: count } : current), [setTask])

  async function confirm(card: TaskCard) {
    if (!task || role !== 'business') return
    const before = task
    const updated = await updateTaskCard(id, card)
    setTask(updated)
    setEditing(false)
    window.scrollTo({ top: 0 })
    setRankChange(before.position != null && updated.position != null && before.position !== updated.position
      ? { from: before.position, to: updated.position } : null)
    notification.success({ message: 'Карточка подтверждена', description: ratingChangeText(before, updated), duration: 8 })
  }

  async function publish() {
    if (!task || task.status !== 'confirmed' || role !== 'business' || publishing) return
    setPublishing(true)
    try {
      const updated = await publishTask(id)
      setTask(updated)
      window.scrollTo({ top: 0 })
      message.success(`Задача опубликована. Место #${updated.position}`)
    } catch { /* API-клиент показывает detail. */ }
    finally { setPublishing(false) }
  }

  if (loading) return <Skeleton active paragraph={{ rows: 10 }} />
  if (error instanceof ApiError && error.status === 404) return <TaskNotFound />
  if (error || !task) return <LoadError title="Не удалось загрузить задачу" onRetry={reload} />

  return (
    <section className="task-page">
      <Link to="/">← Каталог</Link>
      <div className="section-heading task-heading">
        <div>
          <Typography.Title level={2}>{taskTitle(task)}</Typography.Title>
          <Space wrap><TaskStatusTag status={task.status} /><AiModeTag mode={task.ai_mode} />
            <Typography.Text type="secondary">{task.industry}{task.business_name ? ` · ${task.business_name}` : ''}</Typography.Text>
          </Space>
        </div>
        {task.position != null && <Space direction="vertical" align="center"><Typography.Text type="secondary">Место в каталоге</Typography.Text><RankBadge position={task.position} /></Space>}
      </div>
      <Typography.Paragraph>История рейтинга: {task.rating_history.length ? task.rating_history.map((item) => item.total).join(' → ') : 'пока нет подтверждений'}</Typography.Paragraph>
      <Typography.Paragraph type="secondary">Откликов: {task.proposals_count}</Typography.Paragraph>
      {rankChange && <RankChange key={`${rankChange.from}-${rankChange.to}-${task.rating_history.length}`} {...rankChange} />}

      {editing && role === 'business' ? <TaskCardEditor task={task} onConfirm={confirm} onCancel={() => setEditing(false)} confirmLabel="Подтвердить" /> : <>
        {role === 'business' && <Space className="task-actions" wrap>
          {task.status === 'clarifying' ? <Link to={`/tasks/new?task=${task.id}`}><Button type="primary">Ответить на вопросы</Button></Link>
            : <Button onClick={() => { setRankChange(null); setEditing(true) }} disabled={publishing}>Редактировать</Button>}
          {task.status === 'confirmed' && <Button type="primary" onClick={publish} loading={publishing}>Опубликовать</Button>}
          {task.status === 'card_ready' && <Link to={`/tasks/new?task=${task.id}`}>Продолжить в конструкторе</Link>}
        </Space>}
        <div className="builder-grid">
          <Card title="Карточка задачи">
            {task.status === 'clarifying' && <Alert className="builder-alert" type="info" message="Это черновик: сначала нужно ответить на уточняющие вопросы" />}
            <dl className="task-fields">{CARD_FIELDS.map((field) => <div key={field}>
              <dt>{FIELD_LABELS[field]}</dt>
              <dd>{task.card[field].trim() ? task.card[field] : <Typography.Text type="secondary">Не заполнено</Typography.Text>}
                <EvidenceNote evidence={task.evidence[field]} /></dd>
            </div>)}</dl>
          </Card>
          <aside className="builder-aside">{task.rating ? <RatingPanel rating={task.rating} />
            : <Card title="Подтверждённый рейтинг"><Typography.Text type="secondary">Появится после ручного подтверждения карточки. Оценка черновика не засчитывается.</Typography.Text></Card>}</aside>
        </div>
      </>}
      <Proposals task={task} onCountChange={setProposalCount} />
    </section>
  )
}

export function TaskPage() {
  const { id: value } = useParams()
  const id = parseTaskId(value)
  return id == null ? <TaskNotFound /> : <TaskDetails key={id} id={id} />
}
