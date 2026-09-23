import React from 'react'
import { useLayoutEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { App as AntdApp, ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { setMessageApi } from './api/notify'
import { RoleProvider } from './context/RoleContext'
import { appTheme } from './theme'
import 'antd/dist/reset.css'
import './styles.css'

function MessageBridge({ children }: { children: React.ReactNode }) {
  const { message } = AntdApp.useApp()

  useLayoutEffect(() => {
    setMessageApi(message)
    return () => setMessageApi(null)
  }, [message])

  return children
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={ruRU} theme={appTheme}>
      <AntdApp>
        <MessageBridge>
          <BrowserRouter>
            <RoleProvider>
              <App />
            </RoleProvider>
          </BrowserRouter>
        </MessageBridge>
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>,
)
