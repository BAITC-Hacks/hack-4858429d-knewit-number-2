import { Tag } from 'antd'
import type { Level } from '../api/types'
import { LEVELS } from './levels'

export function LevelTag({ level }: { level: Level }) {
  const { color, label } = LEVELS[level]

  return (
    <Tag bordered={false} className="level-tag" style={{ color, backgroundColor: `${color}1A` }}>
      {label}
    </Tag>
  )
}
