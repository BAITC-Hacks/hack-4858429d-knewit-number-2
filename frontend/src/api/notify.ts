import type { MessageInstance } from 'antd/es/message/interface'

let messageApi: MessageInstance | null = null

export function setMessageApi(instance: MessageInstance | null) {
  messageApi = instance
}

export function notifyError(detail: string) {
  if (messageApi) void messageApi.error({ key: `api-error:${detail}`, content: detail })
}
