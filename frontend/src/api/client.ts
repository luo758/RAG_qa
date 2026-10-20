import axios from 'axios'

const FIELD_LABELS: Record<string, string> = {
  username: '账号',
  password: '密码',
  confirm_password: '确认密码',
  captcha_id: '图形验证码',
  captcha_code: '图形验证码',
  name: '名称',
  content: '内容',
  question: '问题',
}

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) {
      return detail
        .map((item: any) => {
          const location = Array.isArray(item?.loc) ? item.loc.filter((part: string) => part !== 'body') : []
          const field = String(location[location.length - 1] || '')
          const label = FIELD_LABELS[field] || field || '请求参数'
          const type = String(item?.type || '')
          if (type === 'string_too_short') {
            return `${label}至少需要 ${item?.ctx?.min_length ?? 8} 个字符`
          }
          if (type === 'string_too_long') {
            return `${label}长度超过限制`
          }
          if (type === 'string_pattern_mismatch') {
            return `${label}格式不正确`
          }
          if (type === 'missing') {
            return `${label}不能为空`
          }
          return `${label}：${item?.msg || '参数不合法'}`
        })
        .join('；')
    }
    if (typeof detail === 'string') return detail
    return error.message
  }
  return error instanceof Error ? error.message : '请求失败'
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('docflow_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !location.pathname.startsWith('/login')) {
      localStorage.removeItem('docflow_token')
      localStorage.removeItem('docflow_user')
      location.href = '/login'
    }
    return Promise.reject(error)
  },
)
