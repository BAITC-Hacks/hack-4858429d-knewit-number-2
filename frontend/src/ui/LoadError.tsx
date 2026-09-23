import { Alert, Button } from 'antd'

export function LoadError({ title, onRetry }: { title: string; onRetry: () => void }) {
  return <Alert type="error" showIcon message={title} action={<Button onClick={onRetry}>Повторить</Button>} />
}
