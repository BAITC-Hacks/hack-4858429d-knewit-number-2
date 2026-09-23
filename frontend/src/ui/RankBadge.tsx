import { theme } from 'antd'

export function RankBadge({ position }: { position: number }) {
  const { token } = theme.useToken()

  return <span className="rank-badge" style={{ color: token.colorPrimary }}>#{position}</span>
}
