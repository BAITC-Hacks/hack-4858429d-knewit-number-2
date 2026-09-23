import { Tag, theme } from 'antd'
import type { AiMode } from '../api/types'

const AI_MODE_LABELS: Record<AiMode, string> = {
  openai: 'ИИ: OpenAI',
  nvidia: 'ИИ: NVIDIA',
  stub: 'ИИ: заглушка',
}

export function AiModeTag({ mode }: { mode: AiMode | null | undefined }) {
  const { token } = theme.useToken()
  if (!mode) return null

  return (
    <Tag
      bordered={false}
      style={{ color: token.colorTextSecondary, backgroundColor: token.colorFillSecondary }}
    >
      {AI_MODE_LABELS[mode]}
    </Tag>
  )
}
