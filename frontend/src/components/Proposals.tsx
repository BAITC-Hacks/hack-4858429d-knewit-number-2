import { useCallback, useEffect, useState } from 'react'
import { Alert, App, Button, Card, Empty, Form, Input, Popconfirm, Skeleton, Space, Typography } from 'antd'
import { confirmMilestone, createProposal, decideProposal, getTaskProposals } from '../api/client'
import type { Proposal, Task, Team } from '../api/types'
import { useRole } from '../context/RoleContext'
import { useResource } from '../hooks/useResource'
import { safeExternalUrl } from '../lib/taskPresentation'
import { LoadError, ProposalStatusTag } from '../ui'

type ProposalValues = Pick<Proposal, 'idea' | 'plan' | 'deadline' | 'prototype_url'>

function ProposalForm({ taskId, team, onCreated }: { taskId: number; team: Team; onCreated: (proposal: Proposal) => void }) {
  const [form] = Form.useForm<ProposalValues>()
  const [sending, setSending] = useState(false)
  const { message } = App.useApp()

  async function submit(values: ProposalValues) {
    if (sending) return
    setSending(true)
    try {
      const proposal = await createProposal(taskId, { ...values, team_id: team.id })
      onCreated(proposal)
      form.resetFields()
      message.success(`Отклик команды «${team.name}» отправлен`)
    } catch { /* Поля сохраняются, API-клиент показывает detail. */ }
    finally { setSending(false) }
  }

  return (
    <Card title="Откликнуться" className="proposal-form">
      <Typography.Paragraph>От команды «{team.name}». Выбор делает бизнес вручную.</Typography.Paragraph>
      <Form form={form} layout="vertical" onFinish={submit} disabled={sending}>
        <Form.Item name="idea" label="Идея" rules={[{ required: true, whitespace: true, message: 'Опишите идею' },
          { min: 10, transform: (value: string) => value?.trim(), message: 'Минимум 10 символов' }]}>
          <Input.TextArea autoSize={{ minRows: 3, maxRows: 8 }} />
        </Form.Item>
        <Form.Item name="plan" label="План" rules={[{ required: true, whitespace: true, message: 'Опишите план' },
          { min: 10, transform: (value: string) => value?.trim(), message: 'Минимум 10 символов' }]}>
          <Input.TextArea autoSize={{ minRows: 3, maxRows: 8 }} />
        </Form.Item>
        <Form.Item name="deadline" label="Срок" rules={[{ required: true, whitespace: true, message: 'Укажите срок' }]}>
          <Input placeholder="Например, 6 недель" />
        </Form.Item>
        <Form.Item name="prototype_url" label="Ссылка на прототип" required rules={[{
          validator: (_, value: string) => safeExternalUrl(value ?? '') ? Promise.resolve() : Promise.reject(new Error('Укажите корректную ссылку http:// или https://')),
        }]}><Input placeholder="https://example.com/prototype" /></Form.Item>
        <Button type="primary" htmlType="submit" loading={sending}>Отправить отклик</Button>
      </Form>
    </Card>
  )
}

export function Proposals({ task, onCountChange }: { task: Task; onCountChange: (count: number) => void }) {
  const { role, teams, teamsLoading, selectedTeamId, refreshTeams } = useRole()
  const { message } = App.useApp()
  const load = useCallback(() => getTaskProposals(task.id), [task.id, role])
  const { data, setData, error, loading, reload } = useResource(load)
  const [busyId, setBusyId] = useState<number | null>(null)
  const team = teams.find((item) => item.id === selectedTeamId)
  const visible = role === 'business' ? data ?? [] : (data ?? []).filter((item) => item.team_id === selectedTeamId)

  useEffect(() => { if (data) onCountChange(data.length) }, [data, onCountChange])

  async function update(proposal: Proposal, action: 'selected' | 'rejected' | 'milestone') {
    if (role !== 'business' || busyId != null) return
    setBusyId(proposal.id)
    try {
      const updated = action === 'milestone' ? await confirmMilestone(proposal.id) : await decideProposal(proposal.id, action)
      setData((items) => items?.map((item) => item.id === updated.id ? updated : item) ?? null)
      if (action === 'milestone') {
        refreshTeams()
        message.success(`Этап подтверждён. Команде «${updated.team_name}» начислено 10 баллов`)
      } else message.success(action === 'selected' ? `Команда «${updated.team_name}» выбрана` : 'Отклик отклонён')
    } catch { /* Решение не меняется локально до успешного ответа API. */ }
    finally { setBusyId(null) }
  }

  return (
    <section className="proposals-section" aria-label="Отклики на задачу">
      <div className="section-heading">
        <Typography.Title level={3}>{role === 'business' ? 'Отклики команд' : 'Отклики вашей команды'}</Typography.Title>
        <Button onClick={reload} disabled={busyId != null || loading}>Обновить отклики</Button>
      </div>
      {role === 'business' && <Typography.Paragraph type="secondary">Можно выбрать несколько команд или не выбирать ни одну.</Typography.Paragraph>}
      {loading ? <Skeleton active /> : error ? <LoadError title="Не удалось загрузить отклики" onRetry={reload} /> : (
        <>
          {visible.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Откликов пока нет" />}
          <div className="proposal-list">
            {visible.map((proposal) => {
              const href = safeExternalUrl(proposal.prototype_url)
              return <section key={proposal.id} aria-label={`Отклик ${proposal.team_name} №${proposal.id}`}>
                <Card title={proposal.team_name} extra={<ProposalStatusTag status={proposal.status} />}>
                  <dl className="task-fields compact-fields">
                    <div><dt>Идея</dt><dd>{proposal.idea}</dd></div>
                    <div><dt>План</dt><dd>{proposal.plan}</dd></div>
                    <div><dt>Срок</dt><dd>{proposal.deadline}</dd></div>
                    <div><dt>Прототип</dt><dd>{href ? <a href={href} target="_blank" rel="noopener noreferrer">Открыть прототип</a> : 'Ссылка недоступна'}</dd></div>
                    <div><dt>Подтверждено этапов</dt><dd>{proposal.milestones_confirmed}</dd></div>
                  </dl>
                  {role === 'business' && <Space wrap>
                    <Popconfirm title={`Выбрать команду «${proposal.team_name}»?`} description="Другие выбранные команды сохранятся."
                      okText="Выбрать" cancelText="Отмена" onConfirm={() => update(proposal, 'selected')}
                      disabled={busyId != null || proposal.status === 'selected'}>
                      <Button type="primary" disabled={busyId != null || proposal.status === 'selected'}>Выбрать</Button>
                    </Popconfirm>
                    <Popconfirm title={`Отклонить отклик команды «${proposal.team_name}»?`} okText="Отклонить" cancelText="Отмена"
                      onConfirm={() => update(proposal, 'rejected')} disabled={busyId != null || proposal.status === 'rejected'}>
                      <Button danger disabled={busyId != null || proposal.status === 'rejected'}>Отклонить</Button>
                    </Popconfirm>
                    {proposal.status === 'selected' && <Popconfirm title={`Подтвердить этап ${proposal.milestones_confirmed + 1}?`}
                      description={`Команда «${proposal.team_name}» получит +10 баллов.`} okText="Подтвердить этап" cancelText="Отмена"
                      disabled={busyId != null} onConfirm={() => update(proposal, 'milestone')}>
                      <Button disabled={busyId != null}>Подтвердить этап</Button>
                    </Popconfirm>}
                    {busyId === proposal.id && <Typography.Text type="secondary">Сохраняем…</Typography.Text>}
                  </Space>}
                </Card>
              </section>
            })}
          </div>
          {role === 'team' && (task.status !== 'published' ? (
            <Alert type="info" showIcon message="Откликнуться можно после публикации задачи" />
          ) : <>
            {task.rating?.level === 'draft' && <Alert className="builder-alert" type="warning" showIcon message="Задача требует уточнения, но откликнуться можно" />}
            {teamsLoading ? <Skeleton active /> : team ? <ProposalForm key={team.id} taskId={task.id} team={team}
              onCreated={(proposal) => setData((items) => [...items ?? [], proposal])} />
              : <Alert type="info" showIcon message="Выберите команду в шапке, чтобы отправить отклик" />}
          </>)}
        </>
      )}
    </section>
  )
}
