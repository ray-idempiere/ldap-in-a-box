import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })
export const apiV2 = axios.create({ baseURL: '/api/v2' })

api.interceptors.request.use(config => {
    const token = localStorage.getItem('token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
})

apiV2.interceptors.request.use(config => {
    const token = localStorage.getItem('token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
})

const responseInterceptor = [
    res => res,
    err => {
        if (err.response?.status === 401) {
            localStorage.removeItem('token')
            window.location.href = '/login'
        }
        return Promise.reject(err)
    }
]

api.interceptors.response.use(...responseInterceptor)
apiV2.interceptors.response.use(...responseInterceptor)

export default api
