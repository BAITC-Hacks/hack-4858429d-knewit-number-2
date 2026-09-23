import { Typography } from 'antd'

export function RankChange({ from, to }: { from: number; to: number }) {
  if (from === to) return null

  return (
    <Typography.Paragraph className="rank-change" role="status">
      {to < from ? '↑' : '↓'} с #{from} на #{to}
    </Typography.Paragraph>
  )
}
