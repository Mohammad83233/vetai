import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { PawPrint, Stethoscope, ClipboardList, Mail, Lock, User, AlertCircle, Eye, EyeOff } from 'lucide-react'

export default function Login() {
    const [isRegister, setIsRegister] = useState(false)
    const [activeRole, setActiveRole] = useState('staff')
    const [showPassword, setShowPassword] = useState(false)
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        full_name: '',
        role: 'staff'
    })
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const { login, register } = useAuth()
    const navigate = useNavigate()

    const handleRoleSwitch = (role) => {
        setActiveRole(role)
        setFormData({ ...formData, role })
        setError('')
    }

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value })
        setError('')
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        setError('')

        try {
            if (isRegister) {
                const result = await register({ ...formData, role: activeRole })
                if (result.success) {
                    const loginResult = await login(formData.email, formData.password)
                    if (loginResult.success) {
                        navigate('/dashboard')
                    }
                } else {
                    setError(result.error)
                }
            } else {
                const result = await login(formData.email, formData.password)
                if (result.success) {
                    navigate('/dashboard')
                } else {
                    setError(result.error)
                }
            }
        } catch (err) {
            setError('An unexpected error occurred')
        } finally {
            setLoading(false)
        }
    }

    const roleTitle = activeRole === 'doctor' ? 'Doctor' : 'Staff'

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'linear-gradient(135deg, #e8f0fe 0%, #f0f7ff 30%, #e6f9f5 70%, #f5f5fa 100%)',
            padding: '20px',
            fontFamily: 'var(--font-family)'
        }}>
            <div style={{ width: '100%', maxWidth: 460 }}>

                {/* Logo Section */}
                <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <div style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: 64,
                        height: 64,
                        background: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
                        borderRadius: 16,
                        marginBottom: 12,
                        boxShadow: '0 8px 30px rgba(59,130,246,0.3)'
                    }}>
                        <PawPrint size={32} color="white" />
                    </div>
                    <h1 style={{
                        fontSize: '1.75rem',
                        fontWeight: 700,
                        color: '#1e293b',
                        margin: 0
                    }}>VetAI</h1>
                    <p style={{
                        color: '#64748b',
                        fontSize: '0.9rem',
                        marginTop: 4
                    }}>Clinical Decision Support System</p>
                </div>

                {/* Main Card */}
                <div style={{
                    background: 'white',
                    borderRadius: 16,
                    boxShadow: '0 4px 24px rgba(0,0,0,0.08), 0 1px 3px rgba(0,0,0,0.04)',
                    overflow: 'hidden'
                }}>

                    {/* Role Tabs */}
                    <div style={{
                        display: 'flex',
                        borderBottom: '2px solid #f1f5f9'
                    }}>
                        <button
                            type="button"
                            onClick={() => handleRoleSwitch('staff')}
                            style={{
                                flex: 1,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: 8,
                                padding: '16px 0',
                                border: 'none',
                                background: activeRole === 'staff' ? 'white' : '#f8fafc',
                                color: activeRole === 'staff' ? '#3b82f6' : '#94a3b8',
                                fontWeight: 600,
                                fontSize: '0.95rem',
                                cursor: 'pointer',
                                borderBottom: activeRole === 'staff' ? '3px solid #3b82f6' : '3px solid transparent',
                                transition: 'all 0.2s ease',
                                fontFamily: 'inherit'
                            }}
                        >
                            <ClipboardList size={18} />
                            Staff
                        </button>
                        <button
                            type="button"
                            onClick={() => handleRoleSwitch('doctor')}
                            style={{
                                flex: 1,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: 8,
                                padding: '16px 0',
                                border: 'none',
                                background: activeRole === 'doctor' ? 'white' : '#f8fafc',
                                color: activeRole === 'doctor' ? '#3b82f6' : '#94a3b8',
                                fontWeight: 600,
                                fontSize: '0.95rem',
                                cursor: 'pointer',
                                borderBottom: activeRole === 'doctor' ? '3px solid #3b82f6' : '3px solid transparent',
                                transition: 'all 0.2s ease',
                                fontFamily: 'inherit'
                            }}
                        >
                            <Stethoscope size={18} />
                            Doctor
                        </button>
                    </div>

                    {/* Form Content */}
                    <div style={{ padding: '32px 36px 36px' }}>

                        {/* Heading */}
                        <h2 style={{
                            fontSize: '1.5rem',
                            fontWeight: 700,
                            color: '#1e293b',
                            marginBottom: 24
                        }}>
                            {isRegister ? `${roleTitle} Registration` : `${roleTitle} Login`}
                        </h2>

                        {/* Error Alert */}
                        {error && (
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 10,
                                padding: '12px 16px',
                                background: '#fef2f2',
                                border: '1px solid #fecaca',
                                borderRadius: 10,
                                marginBottom: 20,
                                color: '#dc2626',
                                fontSize: '0.9rem'
                            }}>
                                <AlertCircle size={18} />
                                <span>{error}</span>
                            </div>
                        )}

                        <form onSubmit={handleSubmit}>

                            {/* Full Name (register only) */}
                            {isRegister && (
                                <div style={{ marginBottom: 20 }}>
                                    <label style={{
                                        display: 'block',
                                        fontSize: '0.9rem',
                                        fontWeight: 600,
                                        color: '#3b82f6',
                                        marginBottom: 8
                                    }}>Full Name</label>
                                    <div style={{ position: 'relative' }}>
                                        <input
                                            type="text"
                                            name="full_name"
                                            value={formData.full_name}
                                            onChange={handleChange}
                                            placeholder={activeRole === 'doctor' ? 'Dr. John Smith' : 'John Smith'}
                                            required
                                            style={{
                                                width: '100%',
                                                padding: '12px 16px',
                                                fontSize: '0.95rem',
                                                border: '1.5px solid #e2e8f0',
                                                borderRadius: 10,
                                                outline: 'none',
                                                transition: 'border-color 0.2s, box-shadow 0.2s',
                                                fontFamily: 'inherit',
                                                color: '#334155'
                                            }}
                                            onFocus={e => {
                                                e.target.style.borderColor = '#3b82f6'
                                                e.target.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.1)'
                                            }}
                                            onBlur={e => {
                                                e.target.style.borderColor = '#e2e8f0'
                                                e.target.style.boxShadow = 'none'
                                            }}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Email */}
                            <div style={{ marginBottom: 20 }}>
                                <label style={{
                                    display: 'block',
                                    fontSize: '0.9rem',
                                    fontWeight: 600,
                                    color: '#3b82f6',
                                    marginBottom: 8
                                }}>Email</label>
                                <input
                                    type="email"
                                    name="email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    placeholder={activeRole === 'doctor' ? 'doctor@hospital.com' : 'staff@hospital.com'}
                                    required
                                    style={{
                                        width: '100%',
                                        padding: '12px 16px',
                                        fontSize: '0.95rem',
                                        border: '1.5px solid #e2e8f0',
                                        borderRadius: 10,
                                        outline: 'none',
                                        transition: 'border-color 0.2s, box-shadow 0.2s',
                                        fontFamily: 'inherit',
                                        color: '#334155'
                                    }}
                                    onFocus={e => {
                                        e.target.style.borderColor = '#3b82f6'
                                        e.target.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.1)'
                                    }}
                                    onBlur={e => {
                                        e.target.style.borderColor = '#e2e8f0'
                                        e.target.style.boxShadow = 'none'
                                    }}
                                />
                            </div>

                            {/* Password */}
                            <div style={{ marginBottom: isRegister ? 20 : 8 }}>
                                <label style={{
                                    display: 'block',
                                    fontSize: '0.9rem',
                                    fontWeight: 600,
                                    color: '#3b82f6',
                                    marginBottom: 8
                                }}>Password</label>
                                <div style={{ position: 'relative' }}>
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        name="password"
                                        value={formData.password}
                                        onChange={handleChange}
                                        placeholder="••••••••"
                                        required
                                        minLength={6}
                                        style={{
                                            width: '100%',
                                            padding: '12px 44px 12px 16px',
                                            fontSize: '0.95rem',
                                            border: '1.5px solid #e2e8f0',
                                            borderRadius: 10,
                                            outline: 'none',
                                            transition: 'border-color 0.2s, box-shadow 0.2s',
                                            fontFamily: 'inherit',
                                            color: '#334155'
                                        }}
                                        onFocus={e => {
                                            e.target.style.borderColor = '#3b82f6'
                                            e.target.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.1)'
                                        }}
                                        onBlur={e => {
                                            e.target.style.borderColor = '#e2e8f0'
                                            e.target.style.boxShadow = 'none'
                                        }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        style={{
                                            position: 'absolute',
                                            right: 12,
                                            top: '50%',
                                            transform: 'translateY(-50%)',
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            color: '#94a3b8',
                                            padding: 4,
                                            display: 'flex'
                                        }}
                                    >
                                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                    </button>
                                </div>
                            </div>

                            {/* Login Button */}
                            <button
                                type="submit"
                                disabled={loading}
                                style={{
                                    width: '100%',
                                    padding: '13px 24px',
                                    marginTop: 20,
                                    fontSize: '1rem',
                                    fontWeight: 600,
                                    color: 'white',
                                    background: loading
                                        ? '#93c5fd'
                                        : 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                                    border: 'none',
                                    borderRadius: 10,
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    transition: 'all 0.2s ease',
                                    boxShadow: loading ? 'none' : '0 4px 14px rgba(59,130,246,0.35)',
                                    fontFamily: 'inherit',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: 8
                                }}
                                onMouseEnter={e => {
                                    if (!loading) {
                                        e.target.style.transform = 'translateY(-1px)'
                                        e.target.style.boxShadow = '0 6px 20px rgba(59,130,246,0.4)'
                                    }
                                }}
                                onMouseLeave={e => {
                                    e.target.style.transform = 'translateY(0)'
                                    e.target.style.boxShadow = '0 4px 14px rgba(59,130,246,0.35)'
                                }}
                            >
                                {loading ? (
                                    <span style={{
                                        display: 'inline-block',
                                        width: 20,
                                        height: 20,
                                        border: '2px solid rgba(255,255,255,0.3)',
                                        borderTopColor: 'white',
                                        borderRadius: '50%',
                                        animation: 'spin 0.8s linear infinite'
                                    }} />
                                ) : (
                                    isRegister ? 'Create Account' : 'Login'
                                )}
                            </button>
                        </form>

                        {/* Switch login/register */}
                        <div style={{
                            textAlign: 'center',
                            marginTop: 24,
                            fontSize: '0.9rem',
                            color: '#64748b'
                        }}>
                            {isRegister ? 'Already have an account? ' : "Don't have an account? "}
                            <button
                                type="button"
                                onClick={() => { setIsRegister(!isRegister); setError(''); }}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    color: '#3b82f6',
                                    cursor: 'pointer',
                                    fontWeight: 600,
                                    fontSize: '0.9rem',
                                    fontFamily: 'inherit',
                                    textDecoration: 'none',
                                    padding: 0
                                }}
                                onMouseEnter={e => e.target.style.textDecoration = 'underline'}
                                onMouseLeave={e => e.target.style.textDecoration = 'none'}
                            >
                                {isRegister ? 'Sign in' : 'Register here'}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <p style={{
                    textAlign: 'center',
                    marginTop: 24,
                    color: '#94a3b8',
                    fontSize: '0.8rem'
                }}>
                    © 2024 VetAI Clinical Decision Support
                </p>
            </div>
        </div>
    )
}
