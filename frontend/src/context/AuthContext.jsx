import { createContext, useContext, useState, useEffect } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        // Check for existing token on mount
        const token = localStorage.getItem('vetai_token')
        if (token) {
            fetchUser(token)
        } else {
            setLoading(false)
        }
    }, [])

    const fetchUser = async (token) => {
        try {
            api.defaults.headers.common['Authorization'] = `Bearer ${token}`
            const response = await api.get('/auth/me')
            setUser(response.data)
        } catch (err) {
            localStorage.removeItem('vetai_token')
            delete api.defaults.headers.common['Authorization']
        } finally {
            setLoading(false)
        }
    }

    const login = async (email, password) => {
        setError(null)
        try {
            const response = await api.post('/auth/login', { email, password })
            const { access_token, user: userData } = response.data

            localStorage.setItem('vetai_token', access_token)
            api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
            setUser(userData)

            return { success: true }
        } catch (err) {
            const message = err.response?.data?.detail || 'Login failed'
            setError(message)
            return { success: false, error: message }
        }
    }

    const register = async (userData) => {
        setError(null)
        try {
            await api.post('/auth/register', userData)
            return { success: true }
        } catch (err) {
            const message = err.response?.data?.detail || 'Registration failed'
            setError(message)
            return { success: false, error: message }
        }
    }

    const logout = () => {
        localStorage.removeItem('vetai_token')
        delete api.defaults.headers.common['Authorization']
        setUser(null)
    }

    const value = {
        user,
        loading,
        error,
        login,
        register,
        logout,
        isAuthenticated: !!user,
        isDoctor: user?.role === 'doctor' || user?.role === 'admin',
        isStaff: user?.role === 'staff' || user?.role === 'doctor' || user?.role === 'admin',
        isAdmin: user?.role === 'admin'
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
