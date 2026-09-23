import { Button, Space, Table, Typography } from 'antd'
import type { TableColumnsType } from 'antd'
import { Link } from 'react-router-dom'
import { getTasks } from '../api/client'
import type { Task } from '../api/types'
import { useRole } from '../context/RoleContext'
import { useResource } from '../hooks/useResource'
import { taskTitle } from '../lib/taskPresentation'
import { LevelTag, LoadError, TaskStatusTag } from '../ui'

const columns: TableColumnsType<Task> = [
  { title: 'Название', key: 'title', render: (_, task) => <Link to={`/tasks/${task.id}`}>{taskTitle(task)}</Link> },
  { title: 'Статус', dataIndex: 'status', render: (status: Task['status']) => <TaskStatusTag status={status} /> },
  { title: 'Рейтинг', key: 'rating', render: (_, task) => task.rating ? `${task.rating.total}/100` : 'Не подтверждён' },
  { title: 'Уровень', key: 'level', render: (_, task) => task.rating ? <LevelTag level={task.rating.level} label={task.rating.level_label} /> : '—' },
  { title: 'Отклики', dataIndex: 'proposals_count' },
  { title: 'Ссылка', key: 'link', render: (_, task) => <Link to={`/tasks/${task.id}`}>Открыть</Link> },
]

export function MyTasks() {
  const { role } = useRole()
  const tasks = useResource(getTasks)
  return (
    <section>
      <div className="section-heading"><Typography.Title level={2}>Мои задачи</Typography.Title>
        <Space><Button onClick={tasks.reload} loading={tasks.loading}>Обновить</Button>{role === 'business' && <Link to="/tasks/new"><Button type="primary">Создать задачу</Button></Link>}</Space>
      </div>
      <Typography.Paragraph type="secondary">В демо без авторизации здесь показаны все задачи, включая незавершённые.</Typography.Paragraph>
      {tasks.error ? <LoadError title="Не удалось загрузить задачи" onRetry={tasks.reload} /> : <Table<Task> rowKey="id"
        dataSource={tasks.data ?? []} columns={columns} loading={tasks.loading} pagination={{ pageSize: 10, hideOnSinglePage: true }}
        locale={{ emptyText: 'Задач пока нет' }} />}
    </section>
  )
}
