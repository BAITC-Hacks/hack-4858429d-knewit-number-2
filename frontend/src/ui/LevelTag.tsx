import { Tag } from 'antd'
import type { Level } from '../api/types'
import { LEVELS } from './levels'

interface LevelTagProps {
  level: Level
  label?: string
  showClarification?: boolean
}

export function LevelTag({ level, label: apiLabel, showClarification = false }: LevelTagProps) {
  const { color, label } = LEVELS[level]
  const text = apiLabel ?? `${label}${level === 'draft' && showClarification ? ' · требует уточнения' : ''}`

  return (
    <Tag bordered={false} className="level-tag" style={{ color, backgroundColor: `${color}1A` }}>
      {text}
    </Tag>
  )
}
