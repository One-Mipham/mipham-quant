import axios from 'axios'

const api = axios.create({
  // Desktop: Flask backend runs on localhost:5000
  baseURL: 'http://127.0.0.1:5000/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Desktop single-user mode: no token needed for local access
// Keep interceptor for future multi-user support
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      // Desktop: don't redirect, just clear state
    }
    return Promise.reject(err)
  },
)

export default api
