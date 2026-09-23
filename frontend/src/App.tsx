import { useEffect } from 'react'
import { Button, Layout, Menu, Result, Segmented, Select, theme, Typography } from 'antd'
import { Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useRole } from './context/RoleContext'
import type { Role } from './context/RoleContext'
import { NewTaskPage } from './pages/NewTaskPage'
import { CatalogPage } from './pages/CatalogPage'
import { TaskPage } from './pages/TaskPage'
import { MyTasks } from './pages/MyTasks'

const navigation = [
  { key: '/', label: 'Каталог' },
  { key: '/tasks/new', label: 'Конструктор' },
  { key: '/my', label: 'Мои задачи' },
]

export default function App() {
  const { token } = theme.useToken()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo({ top: 0 }) }, [pathname])
  const { role, setRole, teams, teamsLoading, teamsFailed, refreshTeams, selectedTeamId, setSelectedTeamId } = useRole()
  const selectedTeam = teams.find((team) => team.id === selectedTeamId)
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
            <>
            <Select
              aria-label="Выбор команды"
              className="team-select"
              placeholder="Выберите команду"
              loading={teamsLoading}
              value={selectedTeamId}
              options={teams.map(({ id, name }) => ({ value: id, label: name }))}
              onChange={setSelectedTeamId}
              notFoundContent={teamsLoading ? 'Загружаем команды…' : 'Команды не найдены'}
            />
            {teamsFailed ? <Button onClick={refreshTeams}>Обновить команды</Button>
              : selectedTeam && <Typography.Text className="team-points">{selectedTeam.points} баллов</Typography.Text>}
            </>
          )}
        </div>
      </Layout.Header>
      <Layout.Content className="app-content">
        <Routes>
          <Route path="/" element={<CatalogPage />} />
          <Route path="/tasks/new" element={<NewTaskPage />} />
          <Route path="/tasks/:id" element={<TaskPage />} />
          <Route path="/my" element={<MyTasks />} />
          <Route path="*" element={<Result status="404" title="Страница не найдена" extra={<Link to="/">Вернуться в каталог</Link>} />} />
        </Routes>
      </Layout.Content>
    </Layout>
  )
}
