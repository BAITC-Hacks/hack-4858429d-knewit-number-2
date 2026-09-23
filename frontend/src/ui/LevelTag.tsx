import { Tag } from 'antd'
import type { Level } from '../api/types'
import { LEVELS } from './levels'

export function LevelTag({ level, showClarification = false }: { level: Level; showClarification?: boolean }) {
  const { color, label } = LEVELS[level]

  return (
    <Tag bordered={false} className="level-tag" style={{ color, backgroundColor: `${color}1A` }}>
      {label}{level === 'draft' && showClarification ? ' · требует уточнения' : ''}
    </Tag>
  )
}
