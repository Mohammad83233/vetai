import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import { queueAPI } from '../services/api'
import { Users, Clock, Activity, CheckCircle, Stethoscope, ClipboardList } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Dashboard() {
    const { user, isDoctor, isStaff } = useAuth()

    const { data: queueData } = useQuery({
        queryKey: ['queue'],
        queryFn: async () => {
            const res = await queueAPI.display()
            return res.data
        },
        refetchInterval: 10000 // Refresh every 10 seconds
    })

    const stats = [
        {
            label: 'Waiting Patients',
            value: queueData?.total_waiting || 0,
            icon: Users,
            color: 'var(--color-warning-500)',
            bgColor: 'var(--color-warning-50)'
        },
        {
            label: 'In Progress',
            value: queueData?.in_progress?.length || 0,
            icon: Activity,
            color: 'var(--color-primary-500)',
            bgColor: 'var(--color-primary-50)'
        },
        {
            label: 'Avg Wait Time',
            value: queueData?.average_wait_minutes ? `${Math.round(queueData.average_wait_minutes)} min` : 'N/A',
            icon: Clock,
            color: 'var(--color-secondary-500)',
            bgColor: 'var(--color-secondary-50)'
        },
        {
            label: 'Next Token',
            value: queueData?.next_token || '-',
            icon: CheckCircle,
            color: 'var(--color-success-500)',
            bgColor: 'var(--color-success-50)'
        }
    ]

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">Welcome, {user?.full_name}</h1>
                    <p className="page-subtitle">
                        Here's what's happening at the clinic today
                    </p>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-4 mb-6">
                {stats.map((stat, idx) => (
                    <div key={idx} className="card stats-card">
                        <div className="flex justify-between items-center mb-4">
                            <div style={{
                                width: 40,
                                height: 40,
                                borderRadius: 'var(--radius)',
                                background: stat.bgColor,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}>
                                <stat.icon size={20} color={stat.color} />
                            </div>
                        </div>
                        <div className="stats-value">{stat.value}</div>
                        <div className="stats-label">{stat.label}</div>
                    </div>
                ))}
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-2 mb-6">
                {user?.role === 'staff' && (
                    <div className="card" style={{ padding: 'var(--space-6)' }}>
                        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, marginBottom: 'var(--space-4)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            <ClipboardList size={20} />
                            Staff Actions
                        </h3>
                        <div className="flex gap-4">
                            <Link to="/staff/register" className="btn btn-primary">
                                Register New Patient
                            </Link>
                            <Link to="/staff" className="btn btn-secondary">
                                Issue Token
                            </Link>
                        </div>
                    </div>
                )}

                {isDoctor && (
                    <div className="card" style={{ padding: 'var(--space-6)' }}>
                        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, marginBottom: 'var(--space-4)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            <Stethoscope size={20} />
                            Doctor Actions
                        </h3>
                        <div className="flex gap-4">
                            <Link to="/doctor" className="btn btn-primary">
                                View My Cases
                            </Link>
                            <Link to="/diagnosis" className="btn btn-secondary">
                                New Diagnosis
                            </Link>
                        </div>
                    </div>
                )}
            </div>

            {/* Queue Preview */}
            <div className="card">
                <div className="card-header flex justify-between items-center">
                    <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>
                        Current Queue
                    </h3>
                    <Link to="/queue" className="btn btn-secondary" style={{ fontSize: 'var(--font-size-sm)' }}>
                        View Full Queue
                    </Link>
                </div>
                <div className="card-body" style={{ padding: 0 }}>
                    {queueData?.waiting?.length > 0 ? (
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Token</th>
                                    <th>Patient</th>
                                    <th>Species</th>
                                    <th>Owner</th>
                                    <th>Wait Time</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {queueData.waiting.slice(0, 5).map((token) => (
                                    <tr key={token.id}>
                                        <td>
                                            <span className="badge badge-primary" style={{ fontWeight: 600 }}>
                                                {token.token_number}
                                            </span>
                                        </td>
                                        <td style={{ fontWeight: 500 }}>{token.patient_name}</td>
                                        <td style={{ textTransform: 'capitalize' }}>{token.species}</td>
                                        <td>{token.owner_name}</td>
                                        <td>{token.estimated_wait_minutes} min</td>
                                        <td>
                                            <span className={`badge ${token.priority > 0 ? 'badge-error' : 'badge-warning'}`}>
                                                {token.priority > 0 ? 'Priority' : 'Waiting'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-gray-500)' }}>
                            <Activity size={40} style={{ marginBottom: 'var(--space-2)', opacity: 0.5 }} />
                            <p>No patients waiting in queue</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
