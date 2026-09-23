import { Progress } from 'antd'
import type { Level } from '../api/types'
import { LEVELS } from './levels'

interface ScoreRingProps {
  score: number
  level: Level
  size?: number
  type?: 'circle' | 'dashboard'
}

export function ScoreRing({ score, level, size = 120, type = 'dashboard' }: ScoreRingProps) {
  return (
    <Progress
      type={type}
      aria-label={`Рейтинг: ${score} из 100`}
      percent={score}
      size={size}
      strokeColor={LEVELS[level].color}
      format={() => <span className="score-ring-value">{score}</span>}
    />
  )
}
