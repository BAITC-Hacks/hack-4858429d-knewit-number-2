import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useAutoAnimate } from '@formkit/auto-animate/react'
import { Alert, Button, Empty, Select, Skeleton, Space, Spin, Tag, Typography, theme } from 'antd'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { getCatalog, getIndustries } from '../api/client'
import type { CatalogItem, Level } from '../api/types'
import { useRole } from '../context/RoleContext'
import { LEVELS, LevelTag, RankBadge, ScoreRing } from '../ui'
import { Recommendations } from '../components/Recommendations'

const levelOptions = (Object.keys(LEVELS) as Level[]).map((level) => ({
  value: level,
  label: LEVELS[level].label,
}))

export function CatalogPage() {
  const { token } = theme.useToken()
  const { role, selectedTeamId } = useRole()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const industry = searchParams.get('industry') || undefined
  const levelParam = searchParams.get('level')
  const level = levelOptions.find((option) => option.value === levelParam)?.value
  const [tasks, setTasks] = useState<CatalogItem[]>([])
  const [industries, setIndustries] = useState<string[]>([])
  const [industriesLoading, setIndustriesLoading] = useState(true)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [revision, setRevision] = useState(0)
  const [listRef, enableAnimations] = useAutoAnimate<HTMLUListElement>({ duration: 180 })
  const [animateChanges, setAnimateChanges] = useState(false)

  useEffect(() => { enableAnimations(animateChanges) }, [animateChanges, enableAnimations])

  useEffect(() => {
    let active = true
    getIndustries()
      .then((items) => { if (active) setIndustries(items) })
      .catch(() => {}) // Сообщение об ошибке показывает API-клиент.
      .finally(() => { if (active) setIndustriesLoading(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    setLoading(true)
    setFailed(false)
    getCatalog({ industry, level })
      .then((items) => {
        // Порядок и глобальные позиции сохраняются ровно как в ответе API.
        if (active) setTasks(items)
      })
      .catch(() => {
        if (active) {
          setTasks([])
          setFailed(true)
        }
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [industry, level, revision])

  function changeFilter(key: 'industry' | 'level', value?: string) {
    setAnimateChanges(true)
    setSearchParams((current) => {
      const next = new URLSearchParams(current)
      if (value) next.set(key, value)
      else next.delete(key)
      return next
    })
  }

  function resetFilters() {
    setAnimateChanges(true)
    setSearchParams((current) => {
      const next = new URLSearchParams(current)
      next.delete('industry')
      next.delete('level')
      return next
    })
  }

  return (
    <section className="catalog-page">
      <div className="catalog-heading">
        <div>
          <Typography.Title level={2}>Каталог задач</Typography.Title>
          <Typography.Paragraph type="secondary">
            Задачи по убыванию рейтинга. Место в общем каталоге сохраняется при фильтрации.
          </Typography.Paragraph>
        </div>
        {role === 'business' && (
          <Button type="primary" onClick={() => navigate('/tasks/new')}>Создать задачу</Button>
        )}
      </div>

      {role === 'team' && selectedTeamId != null && <Recommendations key={selectedTeamId} teamId={selectedTeamId} />}

      <div className="catalog-filters">
        <div className="catalog-filter">
          <label htmlFor="catalog-industry">Отрасль</label>
          <Select
            id="catalog-industry"
            placeholder="Все отрасли"
            value={industry}
            allowClear
            showSearch
            loading={industriesLoading}
            options={industries.map((item) => ({ value: item, label: item }))}
            onChange={(value: string | undefined) => changeFilter('industry', value)}
          />
        </div>
        <div className="catalog-filter">
          <label htmlFor="catalog-level">Уровень готовности</label>
          <Select
            id="catalog-level"
            placeholder="Все уровни"
            value={level}
            allowClear
            options={levelOptions}
            onChange={(value: Level | undefined) => changeFilter('level', value)}
          />
        </div>
        {(industry || level) && <Button onClick={resetFilters}>Сбросить фильтры</Button>}
      </div>

      <div aria-busy={loading}>
        <Spin spinning={loading} tip="Загружаем задачи…">
          {loading && tasks.length === 0 && <Skeleton className="catalog-loading" active paragraph={{ rows: 4 }} />}
          <ul ref={listRef} className="catalog-list">
            {tasks.map((task) => (
              <li key={task.id}>
                <Link
                  to={`/tasks/${task.id}`}
                  className="catalog-task"
                  style={{
                    backgroundColor: token.colorBgContainer,
                    borderRadius: token.borderRadius,
                    '--catalog-border': task.level === 'priority' ? LEVELS.priority.color : token.colorBorderSecondary,
                    '--catalog-hover': task.level === 'priority' ? LEVELS.priority.color : token.colorPrimary,
                    '--catalog-focus': token.colorPrimary,
                  } as CSSProperties}
                >
                  <div className="catalog-rank"><RankBadge position={task.position} /></div>
                  <div className="catalog-task-content">
                    <Typography.Title level={4}>{task.title}</Typography.Title>
                    <Space size={[8, 4]} wrap className="catalog-task-meta">
                      <Tag>{task.industry}</Tag>
                      {task.business_name && <Typography.Text type="secondary">{task.business_name}</Typography.Text>}
                    </Space>
                    <Typography.Paragraph className="catalog-need">{task.need_short}</Typography.Paragraph>
                    <Typography.Text type="secondary">Откликов: {task.proposals_count}</Typography.Text>
                  </div>
                  <div className="catalog-rating">
                    <ScoreRing score={task.rating_total} level={task.level} type="circle" size={84} />
                    <LevelTag level={task.level} label={task.level_label} />
                    {task.level === 'draft' && !task.level_label.includes('требует уточнения') && (
                      <Typography.Text type="secondary">требует уточнения</Typography.Text>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
          {!loading && failed && (
            <Alert
              type="error"
              showIcon
              message="Не удалось загрузить каталог"
              action={<Button onClick={() => setRevision((value) => value + 1)}>Повторить</Button>}
            />
          )}
          {!loading && !failed && tasks.length === 0 && (
            <Empty description={industry || level ? 'По выбранным фильтрам задач нет' : 'Опубликованных задач пока нет'}>
              {(industry || level) && <Button onClick={resetFilters}>Сбросить фильтры</Button>}
            </Empty>
          )}
        </Spin>
      </div>
    </section>
  )
}
