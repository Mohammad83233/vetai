import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
    LayoutDashboard,
    Users,
    UserPlus,
    Stethoscope,
    ClipboardList,
    FileText,
    LogOut,
    Activity,
    PawPrint
} from 'lucide-react'

export default function Sidebar() {
    const { user, logout, isDoctor, isStaff } = useAuth()
    const navigate = useNavigate()

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <div className="sidebar-logo">
                    <PawPrint size={28} />
                    <span>VetAI</span>
                </div>
                <p style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '0.25rem' }}>
                    Clinical Decision Support
                </p>
            </div>

            <nav className="sidebar-nav">
                <NavLink to="/dashboard" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                    <LayoutDashboard size={20} />
                    <span>Dashboard</span>
                </NavLink>

                <NavLink to="/queue" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                    <Activity size={20} />
                    <span>Live Queue</span>
                </NavLink>

                {user?.role === 'staff' && (
                    <>
                        <div className="nav-section-title">Staff Panel</div>

                        <NavLink to="/staff" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                            <ClipboardList size={20} />
                            <span>Token Management</span>
                        </NavLink>

                        <NavLink to="/staff/register" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                            <UserPlus size={20} />
                            <span>Register Patient</span>
                        </NavLink>
                    </>
                )}

                {isDoctor && (
                    <>
                        <div className="nav-section-title">Doctor Panel</div>

                        <NavLink to="/doctor" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                            <Stethoscope size={20} />
                            <span>My Cases</span>
                        </NavLink>

                        <NavLink to="/diagnosis" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                            <FileText size={20} />
                            <span>AI Diagnosis</span>
                        </NavLink>
                    </>
                )}

                <div className="nav-section-title">Records</div>

                <NavLink to="/patients" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                    <Users size={20} />
                    <span>All Patients</span>
                </NavLink>
            </nav>

            <div style={{ padding: 'var(--space-4)', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ marginBottom: 'var(--space-3)', padding: 'var(--space-3)', background: 'rgba(255,255,255,0.1)', borderRadius: 'var(--radius)' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{user?.full_name}</div>
                    <div style={{ fontSize: '0.75rem', opacity: 0.7, textTransform: 'capitalize' }}>{user?.role}</div>
                </div>

                <button
                    onClick={handleLogout}
                    className="nav-item"
                    style={{ width: '100%', border: 'none', background: 'transparent', cursor: 'pointer' }}
                >
                    <LogOut size={20} />
                    <span>Logout</span>
                </button>
            </div>
        </aside>
    )
}
