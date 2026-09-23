import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { RoleProvider } from './context/RoleContext'
import 'antd/dist/reset.css'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={ruRU}>
      <BrowserRouter>
        <RoleProvider>
          <App />
        </RoleProvider>
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>,
)
