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
  Typography,
  theme,
} from 'antd'
import { Link } from 'react-router-dom'
import {
  createTask,
  getDraftExamples,
  getIndustries,
  previewRating,
  publishTask,
  submitAnswers,
  updateTaskCard,
} from '../api/client'
import type { CardField, DraftExample, Rating, Task, TaskCard } from '../api/types'
import { useRole } from '../context/RoleContext'
import { AiModeTag, EvidenceNote, FIELD_LABELS, LevelTag, ScoreRing } from '../ui'

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
    setPreview(null)
    setPreviewLoading(true)
    const timer = window.setTimeout(() => {
      previewRating(cardDraft)
        .then((rating) => { if (active) setPreview(rating) })
        .catch(() => {}) // Ошибку показывает API-клиент.
        .finally(() => { if (active) setPreviewLoading(false) })
    }, 400)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [cardDraft, step])

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
      setTask(updated)
      setStep(3)
    } catch {
      // Ошибку показывает API-клиент.
    } finally {
      setSubmitting(false)
    }
  }

  async function publish() {
    if (!task) return
    setSubmitting(true)
    try {
      setTask(await publishTask(task.id))
    } catch {
      // Ошибку показывает API-клиент.
    } finally {
      setSubmitting(false)
    }
  }

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
                      <Typography.Text type="secondary">{FIELD_LABELS[question.field]}</Typography.Text>
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
              <Typography.Title level={5}>Оценка черновика: {task.draft_rating?.total ?? 0}/100</Typography.Title>
              {task.draft_rating && <LevelTag level={task.draft_rating.level} />}
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
            <Card>
              <Typography.Title level={5}>Прогноз рейтинга</Typography.Title>
              <Spin spinning={previewLoading}>
                <div className="builder-score">
                  {preview ? (
                    <>
                      <ScoreRing score={preview.total} level={preview.level} size={136} />
                      <LevelTag level={preview.level} />
                    </>
                  ) : (
                    <Typography.Text type="secondary">Расчёт рейтинга…</Typography.Text>
                  )}
                </div>
              </Spin>
              <Typography.Paragraph className="builder-caption" type="secondary">
                прогноз, засчитывается после подтверждения
              </Typography.Paragraph>
            </Card>
          </aside>
        </div>
      )}

      {step === 3 && task && (
        <Card className="builder-main-card">
          <Typography.Title level={4}>Карточка подтверждена</Typography.Title>
          {task.rating && (
            <div className="builder-score builder-final-score">
              <ScoreRing score={task.rating.total} level={task.rating.level} size={144} />
              <LevelTag level={task.rating.level} />
              <Typography.Text type="secondary">Подтверждённый рейтинг</Typography.Text>
            </div>
          )}
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
            <Button type="primary" onClick={publish} loading={submitting}>Опубликовать</Button>
          )}
        </Card>
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
