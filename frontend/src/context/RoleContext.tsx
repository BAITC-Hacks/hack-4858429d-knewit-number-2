import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { getTeams } from '../api/client'
import type { Team } from '../api/types'

export type Role = 'business' | 'team'

interface RoleContextValue {
  role: Role
  setRole: (role: Role) => void
  teams: Team[]
  teamsLoading: boolean
  selectedTeamId: number | null
  setSelectedTeamId: (id: number | null) => void
}

const RoleContext = createContext<RoleContextValue | null>(null)

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role>('business')
  const [teams, setTeams] = useState<Team[]>([])
  const [teamsLoading, setTeamsLoading] = useState(false)
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null)

  useEffect(() => {
    if (role !== 'team') return

    let active = true
    setTeamsLoading(true)
    getTeams()
      .then((items) => {
        if (!active) return
        setTeams(items)
        setSelectedTeamId((current) =>
          current != null && items.some((team) => team.id === current)
            ? current
            : (items[0]?.id ?? null),
        )
      })
      .catch(() => {}) // Сообщение об ошибке уже показывает API-клиент.
      .finally(() => {
        if (active) setTeamsLoading(false)
      })

    return () => { active = false }
  }, [role])

  return (
    <RoleContext.Provider value={{ role, setRole, teams, teamsLoading, selectedTeamId, setSelectedTeamId }}>
      {children}
    </RoleContext.Provider>
  )
}

export function useRole() {
  const context = useContext(RoleContext)
  if (!context) throw new Error('useRole должен использоваться внутри RoleProvider')
  return context
}
