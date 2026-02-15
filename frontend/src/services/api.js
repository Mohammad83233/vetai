import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Add token to requests if available
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('vetai_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    console.log(`🚀 API Request: ${config.method.toUpperCase()} ${config.baseURL}${config.url}`, config.data)
    return config
})

// Handle auth errors and logging
api.interceptors.response.use(
    (response) => {
        console.log(`✅ API Response: ${response.config.method.toUpperCase()} ${response.config.url} -> ${response.status}`, response.data)
        return response
    },
    (error) => {
        const status = error.response ? error.response.status : 'NETWORK_ERROR'
        const data = error.response ? error.response.data : error.message
        console.error(`❌ API Error: ${error.config?.method?.toUpperCase()} ${error.config?.url} -> ${status}`, data)

        if (error.response?.status === 401) {
            localStorage.removeItem('vetai_token')
            if (window.location.pathname !== '/login') {
                window.location.href = '/login'
            }
        }
        return Promise.reject(error)
    }
)

export default api

// API service functions
export const authAPI = {
    login: (credentials) => api.post('/auth/login', credentials),
    register: (userData) => api.post('/auth/register', userData),
    me: () => api.get('/auth/me'),
}

export const patientsAPI = {
    list: (params) => api.get('/patients', { params }),
    get: (id) => api.get(`/patients/${id}`),
    create: (data) => api.post('/patients', data),
    update: (id, data) => api.put(`/patients/${id}`, data),
    delete: (id) => api.delete(`/patients/${id}`),
    history: (id) => api.get(`/patients/${id}/history`),
}

export const queueAPI = {
    display: () => api.get('/queue/display'),
    issueToken: (data) => api.post('/queue/tokens', data),
    getToken: (id) => api.get(`/queue/tokens/${id}`),
    callNext: (data) => api.post('/queue/call', data),
    updateStatus: (id, data) => api.put(`/queue/tokens/${id}/status`, data),
    myActive: () => api.get('/queue/my-active'),
}

export const clinicalAPI = {
    createRecord: (data) => api.post('/clinical/records', data),
    getRecord: (id) => api.get(`/clinical/records/${id}`),
    updateRecord: (id, data) => api.put(`/clinical/records/${id}`, data),
    completeRecord: (id) => api.post(`/clinical/records/${id}/complete`),
    patientRecords: (patientId) => api.get(`/clinical/patient/${patientId}/records`),
    myRecords: (params) => api.get('/clinical/my-records', { params }),
}

export const diagnosisAPI = {
    predict: (data) => api.post('/diagnosis/predict', data),
    refine: (data) => api.post('/diagnosis/refine', data),
    refineWithSymptoms: (data) => api.post('/diagnosis/refine-symptoms', data),
    finalize: (data) => api.post('/diagnosis/finalize', data),
    get: (id) => api.get(`/diagnosis/${id}`),
}

export const treatmentAPI = {
    recommend: (data) => api.post('/treatment/recommend', data),
    calculateDosage: (data) => api.post('/treatment/dosage', data),
    get: (id) => api.get(`/treatment/${id}`),
    approve: (id) => api.post(`/treatment/${id}/approve`),
}

export const reportsAPI = {
    generate: (data) => api.post('/reports/generate', data),
    get: (id) => api.get(`/reports/${id}`),
    finalize: (id) => api.post(`/reports/${id}/finalize`),
    export: (data) => api.post('/reports/export', data, { responseType: 'blob' }),
}

export const imagesAPI = {
    upload: (formData) => api.post('/images/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    analyze: (imageId) => api.post(`/images/analyze/${imageId}`),
    get: (imageId) => api.get(`/images/${imageId}`),
    delete: (imageId) => api.delete(`/images/${imageId}`),
    list: (params) => api.get('/images', { params }),
}

export const voiceAPI = {
    upload: (formData) => api.post('/voice/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    transcribe: (audioId, language = 'en') => api.post(`/voice/transcribe/${audioId}?language=${language}`),
    get: (audioId) => api.get(`/voice/${audioId}`),
    delete: (audioId) => api.delete(`/voice/${audioId}`),
    list: (params) => api.get('/voice', { params }),
}
