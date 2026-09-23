import { Layout, Menu, Segmented, Select, theme, Typography } from 'antd'
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useRole } from './context/RoleContext'
import type { Role } from './context/RoleContext'
import { NewTaskPage } from './pages/NewTaskPage'

const navigation = [
  { key: '/', label: 'Каталог' },
  { key: '/tasks/new', label: 'Конструктор' },
  { key: '/my', label: 'Мои задачи' },
]

function Page({ title }: { title: string }) {
  return <Typography.Title level={2}>{title}</Typography.Title>
}

export default function App() {
  const { token } = theme.useToken()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const { role, setRole, teams, teamsLoading, selectedTeamId, setSelectedTeamId } = useRole()
  const selectedKey = pathname.startsWith('/tasks/') && pathname !== '/tasks/new'
    ? ''
    : pathname

  return (
    <Layout className="app-layout">
      <Layout.Header
        className="app-header"
        style={{ borderBottom: `1px solid ${token.colorBorderSecondary}` }}
      >
        <Link className="app-logo" style={{ color: token.colorPrimary }} to="/">TaskReady</Link>
        <Menu
          theme="light"
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={navigation}
          onClick={({ key }) => navigate(key)}
          className="app-nav"
        />
        <div className="role-controls">
          <Segmented<Role>
            aria-label="Роль"
            value={role}
            options={[
              { label: 'Бизнес', value: 'business' },
              { label: 'Команда', value: 'team' },
            ]}
            onChange={setRole}
          />
          {role === 'team' && (
            <Select
              aria-label="Выбор команды"
              className="team-select"
              placeholder="Выберите команду"
              loading={teamsLoading}
              value={selectedTeamId}
              options={teams.map(({ id, name }) => ({ value: id, label: name }))}
              onChange={setSelectedTeamId}
            />
          )}
        </div>
      </Layout.Header>
      <Layout.Content className="app-content">
        <Routes>
          <Route path="/" element={<Page title="Каталог" />} />
          <Route path="/tasks/new" element={<NewTaskPage />} />
          <Route path="/tasks/:id" element={<Page title="Задача" />} />
          <Route path="/my" element={<Page title="Мои задачи" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout.Content>
    </Layout>
  )
}
