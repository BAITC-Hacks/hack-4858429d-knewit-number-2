import { useEffect, useState } from 'react'
import {
  Alert,
  App as AntdApp,
  Badge,
  Button,
  Card,
  Form,
  Input,
  List,
  Modal,
  Select,
  Space,
  Spin,
  Steps,
  Tag,
  Typography,
  theme,
} from 'antd'
import { Link } from 'react-router-dom'
import {
  createTask,
  getCatalog,
  getDraftExamples,
  getIndustries,
  previewRating,
  publishTask,
  submitAnswers,
  updateTaskCard,
} from '../api/client'
import type { CardField, CatalogItem, DraftExample, Rating, Task, TaskCard } from '../api/types'
import { useRole } from '../context/RoleContext'
import { AiModeTag, EvidenceNote, FIELD_LABELS, LevelTag, RankChange } from '../ui'
import { RatingPanel } from '../components/RatingPanel'
import { predictCatalogPosition } from '../lib/catalogPosition'

interface DraftValues {
  draft_text: string
  industry: string
  business_name?: string
}

const CARD_FIELDS: CardField[] = [
  'title',
  'context',
  'need',
  'users',
  'data',
  'constraints',
  'expected_result',
  'success_criteria',
  'contact',
  'interaction_format',
]

export function NewTaskPage() {
  const { role, setRole } = useRole()
  const { message } = AntdApp.useApp()
  const { token } = theme.useToken()
  const [draftForm] = Form.useForm<DraftValues>()
  const [cardForm] = Form.useForm<TaskCard>()
  const [step, setStep] = useState(0)
  const [task, setTask] = useState<Task | null>(null)
  const [industries, setIndustries] = useState<string[]>([])
  const [industriesLoading, setIndustriesLoading] = useState(true)
  const [examples, setExamples] = useState<DraftExample[]>([])
  const [examplesOpen, setExamplesOpen] = useState(false)
  const [examplesLoading, setExamplesLoading] = useState(false)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [cardDraft, setCardDraft] = useState<TaskCard | null>(null)
  const [preview, setPreview] = useState<Rating | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [catalog, setCatalog] = useState<CatalogItem[] | null>(null)
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [catalogRevision, setCatalogRevision] = useState(0)
  const [rankChange, setRankChange] = useState<{ from: number; to: number } | null>(null)

  useEffect(() => {
    let active = true
    getIndustries()
      .then((items) => { if (active) setIndustries(items) })
      .catch(() => {}) // Ошибку показывает API-клиент.
      .finally(() => { if (active) setIndustriesLoading(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (step !== 2 || !cardDraft) return
    let active = true
    setPreviewLoading(true)
    const timer = window.setTimeout(() => {
      previewRating(cardDraft)
        .then((rating) => { if (active) setPreview(rating) })
        .catch(() => { if (active) setPreview(null) }) // Ошибку показывает API-клиент.
        .finally(() => { if (active) setPreviewLoading(false) })
    }, 400)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [cardDraft, step])

  useEffect(() => {
    if (step !== 2) return
    let active = true
    setCatalog(null)
    setCatalogLoading(true)
    getCatalog()
      .then((items) => { if (active) setCatalog(items) })
      .catch(() => {}) // Ошибку показывает API-клиент; не выдаём пустой каталог за место #1.
      .finally(() => { if (active) setCatalogLoading(false) })
    return () => { active = false }
  }, [step, catalogRevision])

  async function loadExamples() {
    setExamplesLoading(true)
    try {
      const items = await getDraftExamples()
      if (items.length === 0) {
        message.info('Примеры пока не загружены')
        return
      }
      setExamples(items)
      setExamplesOpen(true)
    } catch {
      // Ошибку показывает API-клиент.
    } finally {
      setExamplesLoading(false)
    }
  }

  function chooseExample(example: DraftExample) {
    draftForm.setFieldsValue({ draft_text: example.text, industry: example.industry })
    setExamplesOpen(false)
  }

  async function analyzeDraft(values: DraftValues) {
    setSubmitting(true)
    try {
      const created = await createTask(values)
      setTask(created)
      setAnswers({})
      setStep(1)
    } catch {
      // Ошибку показывает API-клиент.
    } finally {
      setSubmitting(false)
    }
  }

  async function buildCard() {
    if (!task) return
    if (!task.questions.some((question) => answers[question.id]?.trim())) {
      message.warning('Ответьте хотя бы на один вопрос')
      return
    }
    setSubmitting(true)
    try {
      const updated = await submitAnswers(
        task.id,
        task.questions.map((question) => ({ question_id: question.id, answer: answers[question.id] ?? '' })),
      )
      setTask(updated)
      cardForm.setFieldsValue(updated.card)
      setCardDraft(updated.card)
      setStep(2)
    } catch {
      // Ошибку показывает API-клиент.
    } finally {
      setSubmitting(false)
    }
  }

  async function confirmCard(values: TaskCard) {
    if (!task) return
    setSubmitting(true)
    try {
      const updated = await updateTaskCard(task.id, values)
      setRankChange(task.position != null && updated.position != null && task.position !== updated.position
        ? { from: task.position, to: updated.position }
        : null)
      setTask(updated)
      setStep(3)
    } catch {
      // Ошибку показывает API-клиент.
    } finally {
      setSubmitting(false)
    }
  }

  async function publish() {
    if (!task || task.status !== 'confirmed') return
    setSubmitting(true)
    try {
      setTask(await publishTask(task.id))
    } catch {
      // Ошибку показывает API-клиент.
    } finally {
      setSubmitting(false)
    }
  }

  function editCard() {
    if (!task) return
    cardForm.setFieldsValue(task.card)
    setCardDraft(task.card)
    setPreview(null)
    setRankChange(null)
    setStep(2)
  }

  const forecastPosition = preview && catalog && !previewLoading && !catalogLoading
    ? predictCatalogPosition(preview.total, catalog, task ?? undefined)
    : null

  if (role !== 'business') {
    return (
      <>
        <Typography.Title level={2}>Конструктор</Typography.Title>
        <Alert
          type="info"
          showIcon
          message="Конструктор доступен для роли «Бизнес»"
          action={<Button onClick={() => setRole('business')}>Переключиться на бизнес</Button>}
        />
      </>
    )
  }

  return (
    <div className="task-builder">
      <div className="builder-heading">
        <Typography.Title level={2}>Конструктор задачи</Typography.Title>
        {task && <AiModeTag mode={task.ai_mode} />}
      </div>
      <Steps
        className="builder-steps"
        current={step}
        items={[
          { title: 'Черновик' },
          { title: 'Уточнение' },
          { title: 'Карточка' },
          { title: 'Публикация' },
        ]}
      />

      {step === 0 && (
        <Card className="builder-main-card">
          <Typography.Title level={4}>Опишите задачу своими словами</Typography.Title>
          <Form form={draftForm} layout="vertical" onFinish={analyzeDraft}>
            <Form.Item
              name="draft_text"
              label="Описание задачи"
              rules={[
                { required: true, message: 'Опишите задачу' },
                { min: 20, message: 'Нужно минимум 20 символов' },
              ]}
            >
              <Input.TextArea
                placeholder="Что происходит сейчас и что вы хотите изменить?"
                autoSize={{ minRows: 5, maxRows: 10 }}
                showCount
                maxLength={3000}
              />
            </Form.Item>
            <Form.Item
              name="industry"
              label="Отрасль"
              rules={[{ required: true, message: 'Выберите отрасль' }]}
            >
              <Select
                placeholder="Выберите отрасль"
                loading={industriesLoading}
                showSearch
                options={industries.map((industry) => ({ value: industry, label: industry }))}
              />
            </Form.Item>
            <Form.Item name="business_name" label="Название компании (необязательно)">
              <Input placeholder="Как представить вашу компанию в каталоге" />
            </Form.Item>
            <Space>
              <Button onClick={loadExamples} loading={examplesLoading}>Взять пример</Button>
              <Button type="primary" htmlType="submit" loading={submitting}>Проанализировать</Button>
            </Space>
          </Form>
        </Card>
      )}

      {step === 1 && task && (
        <div className="builder-grid">
          <div>
            <Card className="builder-main-card">
              <Typography.Title level={4}>Ответьте на уточняющие вопросы</Typography.Title>
              <Typography.Paragraph type="secondary">
                Можно оставить отдельные ответы пустыми. Для формирования карточки нужен хотя бы один ответ.
              </Typography.Paragraph>
              <div className="question-list">
                {task.questions.map((question) => (
                  <Card key={question.id} size="small" className="question-card">
                    <Space className="question-meta">
                      <Tag>{FIELD_LABELS[question.field]}</Tag>
                      <Badge count={`+${question.points} баллов`} color={token.colorPrimary} />
                    </Space>
                    <Typography.Paragraph strong>{question.text}</Typography.Paragraph>
                    <Input.TextArea
                      aria-label={`Ответ на вопрос: ${question.text}`}
                      value={answers[question.id] ?? ''}
                      onChange={(event) => setAnswers((current) => ({
                        ...current,
                        [question.id]: event.target.value,
                      }))}
                      autoSize={{ minRows: 2, maxRows: 6 }}
                      showCount
                      maxLength={2000}
                    />
                  </Card>
                ))}
              </div>
              <Button type="primary" onClick={buildCard} loading={submitting}>
                Сформировать карточку
              </Button>
            </Card>
          </div>
          <aside className="builder-aside">
            <Card>
              <Tag>Прогноз</Tag>
              <Typography.Title level={5}>
                {task.draft_rating ? `Оценка черновика: ${task.draft_rating.total}/100` : 'Оценка черновика пока недоступна'}
              </Typography.Title>
              {task.draft_rating && <LevelTag level={task.draft_rating.level} label={task.draft_rating.level_label} />}
              <Typography.Paragraph className="builder-caption" type="secondary">
                Это предварительная оценка. Итоговый рейтинг появится после подтверждения карточки.
              </Typography.Paragraph>
            </Card>
          </aside>
        </div>
      )}

      {step === 2 && task && (
        <div className="builder-grid">
          <Card className="builder-main-card">
            <Typography.Title level={4}>Проверьте и дополните карточку</Typography.Title>
            {task.removed.length > 0 && (
              <Alert
                className="builder-alert"
                type="warning"
                showIcon
                message={`ИИ не стал заполнять: ${task.removed.map((item) =>
                  `${FIELD_LABELS[item.field]} — ${item.reason}`).join('; ')}`}
              />
            )}
            <Form
              form={cardForm}
              layout="vertical"
              onValuesChange={(_, values: TaskCard) => setCardDraft(values)}
              onFinish={confirmCard}
            >
              {CARD_FIELDS.map((field) => (
                <Form.Item
                  key={field}
                  name={field}
                  label={FIELD_LABELS[field]}
                  rules={field === 'title' ? [
                    { required: true, whitespace: true, message: 'Введите название' },
                    { min: 3, message: 'Название должно содержать минимум 3 символа' },
                  ] : undefined}
                  extra={cardDraft?.[field] === task.card[field]
                    ? <EvidenceNote evidence={task.evidence[field]} />
                    : undefined}
                >
                  {field === 'title' ? (
                    <Input maxLength={120} showCount />
                  ) : (
                    <Input.TextArea autoSize={{ minRows: 2, maxRows: 6 }} maxLength={2000} showCount />
                  )}
                </Form.Item>
              ))}
              <Button type="primary" htmlType="submit" loading={submitting}>
                Подтвердить карточку
              </Button>
            </Form>
          </Card>
          <aside className="builder-aside">
            <Card size="small" title="Прогноз места в каталоге" className="builder-position">
              {forecastPosition != null ? (
                <Typography.Paragraph strong>#{forecastPosition}</Typography.Paragraph>
              ) : (
                <Typography.Paragraph type="secondary">
                  {catalogLoading || previewLoading ? 'Обновляем прогноз…' : 'Прогноз места недоступен'}
                </Typography.Paragraph>
              )}
              {!catalogLoading && catalog === null && (
                <Button size="small" onClick={() => setCatalogRevision((value) => value + 1)}>Обновить каталог</Button>
              )}
              <Typography.Text type="secondary">
                По текущему полному каталогу. Фактическое место определит сервер после подтверждения и публикации.
              </Typography.Text>
            </Card>
            <Spin spinning={previewLoading}>
              {preview ? <RatingPanel rating={preview} preview /> : (
                <Card title="Прогноз рейтинга">
                  {previewLoading ? <Typography.Text type="secondary">Расчёт рейтинга…</Typography.Text> : (
                    <Space direction="vertical">
                      <Typography.Text type="secondary">Не удалось получить прогноз</Typography.Text>
                      <Button onClick={() => setCardDraft({ ...cardForm.getFieldsValue() })}>Повторить</Button>
                    </Space>
                  )}
                </Card>
              )}
            </Spin>
          </aside>
        </div>
      )}

      {step === 3 && task && (
        <div className="builder-grid">
          <Card className="builder-main-card">
            <Typography.Title level={4}>Карточка подтверждена</Typography.Title>
            {task.status === 'published' ? (
              <Alert
                type="success"
                showIcon
                message={task.position != null
                  ? `Задача в каталоге на месте #${task.position}`
                  : 'Задача опубликована в каталоге'}
                description={<Link to={`/tasks/${task.id}`}>Открыть страницу задачи</Link>}
              />
            ) : (
              <Button type="primary" onClick={publish} loading={submitting} disabled={task.status !== 'confirmed'}>
                Опубликовать
              </Button>
            )}
            {rankChange && <RankChange from={rankChange.from} to={rankChange.to} />}
            <Button className="builder-edit" onClick={editCard} disabled={submitting}>Редактировать карточку</Button>
          </Card>
          {task.rating && <aside className="builder-aside"><RatingPanel rating={task.rating} /></aside>}
        </div>
      )}

      <Modal
        title="Выберите пример черновика"
        open={examplesOpen}
        onCancel={() => setExamplesOpen(false)}
        footer={null}
      >
        <List
          dataSource={examples}
          renderItem={(example) => (
            <List.Item
              actions={[<Button key="choose" type="link" onClick={() => chooseExample(example)}>Взять</Button>]}
            >
              <List.Item.Meta
                title={example.industry}
                description={<Typography.Paragraph ellipsis={{ rows: 2 }}>{example.text}</Typography.Paragraph>}
              />
            </List.Item>
          )}
        />
      </Modal>
    </div>
  )
}
