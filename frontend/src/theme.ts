import type { ThemeConfig } from 'antd'

export const appTheme: ThemeConfig = {
  token: {
    colorPrimary: '#3B5BDB',
    colorBgLayout: '#F4F6FA',
    colorText: '#1B2440',
    colorBorderSecondary: '#E4E9F1',
    fontFamily: "'Onest', system-ui, sans-serif",
    borderRadius: 10,
    boxShadow: 'none',
    boxShadowSecondary: 'none',
    boxShadowTertiary: 'none',
  },
  components: {
    Layout: {
      headerBg: '#FFFFFF',
      headerColor: '#1B2440',
      bodyBg: '#F4F6FA',
    },
  },
}
