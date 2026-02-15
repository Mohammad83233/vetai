import { useQuery } from '@tanstack/react-query'
import { queueAPI } from '../services/api'
import { Clock, Users, Activity, AlertTriangle } from 'lucide-react'

export default function QueueDisplay() {
    const { data: queueData, isLoading } = useQuery({
        queryKey: ['queue'],
        queryFn: async () => {
            const res = await queueAPI.display()
            return res.data
        },
        refetchInterval: 5000 // Auto-refresh every 5 seconds
    })

    if (isLoading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
                <div className="loading-spinner" style={{ width: 40, height: 40 }}></div>
            </div>
        )
    }

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">Live Queue Display</h1>
                    <p className="page-subtitle">Real-time patient queue status</p>
                </div>
                <div className="flex gap-4 items-center">
                    <span className="badge badge-success" style={{ padding: 'var(--space-2) var(--space-3)' }}>
                        <span style={{
                            width: 8,
                            height: 8,
                            background: 'currentColor',
                            borderRadius: '50%',
                            display: 'inline-block',
                            marginRight: 'var(--space-2)',
                            animation: 'pulse 2s infinite'
                        }}></span>
                        Live
                    </span>
                </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="card stats-card" style={{ background: 'linear-gradient(135deg, var(--color-warning-50), white)' }}>
                    <div className="flex items-center gap-4">
                        <div style={{
                            width: 50,
                            height: 50,
                            borderRadius: 'var(--radius-lg)',
                            background: 'var(--color-warning-500)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <Users size={24} color="white" />
                        </div>
                        <div>
                            <div className="stats-value">{queueData?.total_waiting || 0}</div>
                            <div className="stats-label">Waiting</div>
                        </div>
                    </div>
                </div>

                <div className="card stats-card" style={{ background: 'linear-gradient(135deg, var(--color-primary-50), white)' }}>
                    <div className="flex items-center gap-4">
                        <div style={{
                            width: 50,
                            height: 50,
                            borderRadius: 'var(--radius-lg)',
                            background: 'var(--color-primary-500)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <Activity size={24} color="white" />
                        </div>
                        <div>
                            <div className="stats-value">{queueData?.in_progress?.length || 0}</div>
                            <div className="stats-label">In Progress</div>
                        </div>
                    </div>
                </div>

                <div className="card stats-card" style={{ background: 'linear-gradient(135deg, var(--color-secondary-50), white)' }}>
                    <div className="flex items-center gap-4">
                        <div style={{
                            width: 50,
                            height: 50,
                            borderRadius: 'var(--radius-lg)',
                            background: 'var(--color-secondary-500)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <Clock size={24} color="white" />
                        </div>
                        <div>
                            <div className="stats-value">
                                {queueData?.average_wait_minutes ? `${Math.round(queueData.average_wait_minutes)}m` : '-'}
                            </div>
                            <div className="stats-label">Avg Wait</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Now Being Served */}
            {queueData?.in_progress?.length > 0 && (
                <div className="card mb-6" style={{
                    background: 'linear-gradient(135deg, var(--color-success-500), var(--color-secondary-500))',
                    color: 'white'
                }}>
                    <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
                        <h3 style={{ fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-4)', opacity: 0.9 }}>
                            NOW BEING SERVED
                        </h3>
                        <div className="flex gap-4" style={{ justifyContent: 'center', flexWrap: 'wrap' }}>
                            {queueData.in_progress.map((token) => (
                                <div key={token.id} style={{
                                    background: 'rgba(255,255,255,0.2)',
                                    padding: 'var(--space-4) var(--space-6)',
                                    borderRadius: 'var(--radius-lg)'
                                }}>
                                    <div style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 700 }}>
                                        {token.token_number}
                                    </div>
                                    <div style={{ fontSize: 'var(--font-size-sm)', opacity: 0.9 }}>
                                        {token.patient_name}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Next Token Display */}
            {queueData?.next_token && (
                <div className="card mb-6" style={{
                    background: 'linear-gradient(135deg, var(--color-warning-500), var(--color-accent-500))',
                    color: 'white'
                }}>
                    <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-6)' }}>
                        <h3 style={{ fontSize: 'var(--font-size-lg)', marginBottom: 'var(--space-3)', opacity: 0.9 }}>
                            NEXT IN QUEUE
                        </h3>
                        <div style={{ fontSize: 'var(--font-size-4xl)', fontWeight: 700 }}>
                            {queueData.next_token}
                        </div>
                    </div>
                </div>
            )}

            {/* Queue List */}
            <div className="card">
                <div className="card-header">
                    <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>
                        Waiting Queue
                    </h3>
                </div>
                <div className="card-body" style={{ padding: 0 }}>
                    {queueData?.waiting?.length > 0 ? (
                        <table className="table">
                            <thead>
                                <tr>
                                    <th style={{ width: 80 }}>Position</th>
                                    <th>Token</th>
                                    <th>Patient</th>
                                    <th>Species</th>
                                    <th>Owner</th>
                                    <th>Est. Wait</th>
                                    <th>Priority</th>
                                </tr>
                            </thead>
                            <tbody>
                                {queueData.waiting.map((token, idx) => (
                                    <tr key={token.id}>
                                        <td>
                                            <span style={{
                                                width: 32,
                                                height: 32,
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                background: idx === 0 ? 'var(--color-success-500)' : 'var(--color-gray-200)',
                                                color: idx === 0 ? 'white' : 'var(--color-gray-700)',
                                                borderRadius: '50%',
                                                fontWeight: 600
                                            }}>
                                                {idx + 1}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`token-display ${idx === 0 ? 'token-called' : 'token-waiting'}`}
                                                style={{ fontSize: 'var(--font-size-base)', padding: 'var(--space-2) var(--space-3)' }}>
                                                {token.token_number}
                                            </span>
                                        </td>
                                        <td style={{ fontWeight: 500 }}>{token.patient_name}</td>
                                        <td style={{ textTransform: 'capitalize' }}>{token.species}</td>
                                        <td>{token.owner_name}</td>
                                        <td>~{token.estimated_wait_minutes} min</td>
                                        <td>
                                            {token.priority > 5 ? (
                                                <span className="badge badge-error">
                                                    <AlertTriangle size={12} style={{ marginRight: 4 }} />
                                                    Emergency
                                                </span>
                                            ) : token.priority > 0 ? (
                                                <span className="badge badge-warning">Priority</span>
                                            ) : (
                                                <span className="badge badge-secondary">Normal</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <div style={{ padding: 'var(--space-12)', textAlign: 'center', color: 'var(--color-gray-500)' }}>
                            <Users size={48} style={{ marginBottom: 'var(--space-4)', opacity: 0.5 }} />
                            <h4 style={{ marginBottom: 'var(--space-2)' }}>No Patients Waiting</h4>
                            <p>The queue is currently empty</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
