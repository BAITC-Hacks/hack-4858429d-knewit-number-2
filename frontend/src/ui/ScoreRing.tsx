import { Progress } from 'antd'
import type { Level } from '../api/types'
import { LEVELS } from './levels'

interface ScoreRingProps {
  score: number
  level: Level
  size?: number
}

export function ScoreRing({ score, level, size = 120 }: ScoreRingProps) {
  return (
    <Progress
      type="dashboard"
      percent={score}
      size={size}
      strokeColor={LEVELS[level].color}
      format={() => <span className="score-ring-value">{score}</span>}
    />
  )
}
