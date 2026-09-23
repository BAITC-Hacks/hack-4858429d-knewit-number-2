import { useCallback } from 'react'
import { Card, Empty, Skeleton, Space, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { getTeamRecommendations } from '../api/client'
import { useResource } from '../hooks/useResource'
import { LevelTag, LoadError } from '../ui'

export function Recommendations({ teamId }: { teamId: number }) {
  const load = useCallback(() => getTeamRecommendations(teamId), [teamId])
  const recommendations = useResource(load)
  return <section className="recommendations" aria-label="Рекомендации команде">
    <Typography.Title level={3}>Рекомендовано вашей команде</Typography.Title>
    <Typography.Paragraph type="secondary">Рекомендации не ограничивают общий каталог. Можно откликаться на любую опубликованную задачу.</Typography.Paragraph>
    {recommendations.loading ? <Skeleton active paragraph={{ rows: 2 }} /> : recommendations.error
      ? <LoadError title="Не удалось загрузить рекомендации" onRetry={recommendations.reload} />
      : !recommendations.data?.length ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Сейчас API не вернул рекомендаций. Все задачи доступны в каталоге ниже." />
      : <div className="recommendation-list">{recommendations.data.map(({ task, reasons }) => <Card key={task.id} size="small">
        <Typography.Title level={5}><Link to={`/tasks/${task.id}`}>{task.title}</Link></Typography.Title>
        <Space wrap><Typography.Text strong>#{task.position} · {task.rating_total}/100</Typography.Text><LevelTag level={task.level} label={task.level_label} /></Space>
        <Typography.Paragraph type="secondary">{reasons.join('; ')}</Typography.Paragraph>
      </Card>)}</div>}
  </section>
}
