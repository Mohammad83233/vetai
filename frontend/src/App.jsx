import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'

// Pages
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import StaffDashboard from './pages/StaffDashboard'
import DoctorDashboard from './pages/DoctorDashboard'
import PatientRegistration from './pages/PatientRegistration'
import QueueDisplay from './pages/QueueDisplay'
import DiagnosisPanel from './pages/DiagnosisPanel'
import ReportViewer from './pages/ReportViewer'

// Components
import Sidebar from './components/Sidebar'
import LoadingSpinner from './components/LoadingSpinner'

function ProtectedRoute({ children, requireRole }) {
    const { isAuthenticated, loading, user } = useAuth()

    if (loading) {
        return <LoadingSpinner />
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />
    }

    if (requireRole) {
        const roles = Array.isArray(requireRole) ? requireRole : [requireRole]
        if (!roles.includes(user?.role) && user?.role !== 'admin') {
            return <Navigate to="/dashboard" replace />
        }
    }

    return children
}

function AppLayout({ children }) {
    return (
        <div className="app-container">
            <Sidebar />
            <main className="main-content">
                {children}
            </main>
        </div>
    )
}

function App() {
    const { loading } = useAuth()

    if (loading) {
        return <LoadingSpinner fullScreen />
    }

    return (
        <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<Login />} />

            {/* Protected Routes */}
            <Route path="/dashboard" element={
                <ProtectedRoute>
                    <AppLayout>
                        <Dashboard />
                    </AppLayout>
                </ProtectedRoute>
            } />

            <Route path="/staff" element={
                <ProtectedRoute requireRole={['staff', 'admin']}>
                    <AppLayout>
                        <StaffDashboard />
                    </AppLayout>
                </ProtectedRoute>
            } />

            <Route path="/staff/register" element={
                <ProtectedRoute requireRole={['staff', 'admin']}>
                    <AppLayout>
                        <PatientRegistration />
                    </AppLayout>
                </ProtectedRoute>
            } />

            <Route path="/doctor" element={
                <ProtectedRoute requireRole={['doctor', 'admin']}>
                    <AppLayout>
                        <DoctorDashboard />
                    </AppLayout>
                </ProtectedRoute>
            } />

            <Route path="/queue" element={
                <ProtectedRoute>
                    <AppLayout>
                        <QueueDisplay />
                    </AppLayout>
                </ProtectedRoute>
            } />

            <Route path="/diagnosis/:recordId?" element={
                <ProtectedRoute requireRole={['doctor', 'admin']}>
                    <AppLayout>
                        <DiagnosisPanel />
                    </AppLayout>
                </ProtectedRoute>
            } />

            <Route path="/report/:reportId" element={
                <ProtectedRoute>
                    <AppLayout>
                        <ReportViewer />
                    </AppLayout>
                </ProtectedRoute>
            } />

            {/* Default Redirect */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
    )
}

export default App
