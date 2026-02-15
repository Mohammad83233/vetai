import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { queueAPI, clinicalAPI } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { Stethoscope, Phone, Play, CheckCircle, Clock, FileText } from 'lucide-react'

export default function DoctorDashboard() {
    const { user } = useAuth()
    const navigate = useNavigate()
    const queryClient = useQueryClient()

    const { data: queueData } = useQuery({
        queryKey: ['queue'],
        queryFn: async () => {
            const res = await queueAPI.display()
            return res.data
        },
        refetchInterval: 5000
    })

    const { data: activeTokens } = useQuery({
        queryKey: ['my-active-tokens'],
        queryFn: async () => {
            const res = await queueAPI.myActive()
            return res.data.tokens
        },
        refetchInterval: 5000
    })

    const { data: myRecords } = useQuery({
        queryKey: ['my-records'],
        queryFn: async () => {
            const res = await clinicalAPI.myRecords({ status: 'in_progress' })
            return res.data
        }
    })

    const callNextMutation = useMutation({
        mutationFn: () => queueAPI.callNext({}),
        onSuccess: () => {
            queryClient.invalidateQueries(['queue'])
            queryClient.invalidateQueries(['my-active-tokens'])
        }
    })

    const completeTokenMutation = useMutation({
        mutationFn: async (tokenId) => {
            // Complete the queue token
            await queueAPI.updateStatus(tokenId, { status: 'completed' })

            // Also complete any in-progress clinical records for this token's patient
            if (myRecords?.length > 0) {
                for (const record of myRecords) {
                    if (record.status === 'in_progress') {
                        try {
                            await clinicalAPI.completeRecord(record.id)
                        } catch (err) {
                            console.error('Failed to complete clinical record:', err)
                        }
                    }
                }
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['queue'])
            queryClient.invalidateQueries(['my-active-tokens'])
            queryClient.invalidateQueries(['my-records'])
        }
    })

    const startDiagnosis = async (token) => {
        try {
            // Create clinical record
            const res = await clinicalAPI.createRecord({
                patient_id: token.patient_id,
                token_id: token.id,
                clinical_input: {
                    text_description: token.notes || ''
                }
            })
            navigate(`/diagnosis/${res.data.id}`)
        } catch (err) {
            console.error('Failed to create clinical record:', err)
        }
    }

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">Doctor Dashboard</h1>
                    <p className="page-subtitle">Manage your cases and patient queue</p>
                </div>
                <button
                    className="btn btn-success btn-lg"
                    onClick={() => callNextMutation.mutate()}
                    disabled={callNextMutation.isPending || !queueData?.next_token}
                >
                    {callNextMutation.isPending ? (
                        <span className="loading-spinner" style={{ width: 18, height: 18 }}></span>
                    ) : (
                        <>
                            <Phone size={18} />
                            Call Next: {queueData?.next_token || 'None'}
                        </>
                    )}
                </button>
            </div>

            {/* Active Cases */}
            {activeTokens?.length > 0 && (
                <div className="card mb-6" style={{ borderLeft: '4px solid var(--color-primary-500)' }}>
                    <div className="card-header">
                        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            <Stethoscope size={20} color="var(--color-primary-500)" />
                            Active Cases
                        </h3>
                    </div>
                    <div className="card-body" style={{ padding: 0 }}>
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Token</th>
                                    <th>Patient</th>
                                    <th>Species</th>
                                    <th>Owner</th>
                                    <th>Called At</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {activeTokens.map((token) => (
                                    <tr key={token.id}>
                                        <td>
                                            <span className="token-display token-called" style={{ fontSize: 'var(--font-size-sm)', padding: 'var(--space-2) var(--space-3)' }}>
                                                {token.token_number}
                                            </span>
                                        </td>
                                        <td style={{ fontWeight: 500 }}>{token.patient_name}</td>
                                        <td style={{ textTransform: 'capitalize' }}>{token.species}</td>
                                        <td>{token.owner_name}</td>
                                        <td>
                                            {token.called_at && new Date(token.called_at).toLocaleTimeString()}
                                        </td>
                                        <td>
                                            <div className="flex gap-2">
                                                <button
                                                    className="btn btn-primary"
                                                    style={{ fontSize: 'var(--font-size-sm)' }}
                                                    onClick={() => startDiagnosis(token)}
                                                >
                                                    <Play size={14} />
                                                    Start Diagnosis
                                                </button>
                                                <button
                                                    className="btn btn-success"
                                                    style={{ fontSize: 'var(--font-size-sm)' }}
                                                    onClick={() => completeTokenMutation.mutate(token.id)}
                                                >
                                                    <CheckCircle size={14} />
                                                    Complete
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* In-Progress Records */}
            {myRecords?.length > 0 && (
                <div className="card mb-6">
                    <div className="card-header">
                        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            <FileText size={20} />
                            In-Progress Records
                        </h3>
                    </div>
                    <div className="card-body" style={{ padding: 0 }}>
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Record ID</th>
                                    <th>Patient ID</th>
                                    <th>Status</th>
                                    <th>Created</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {myRecords.map((record) => (
                                    <tr key={record.id}>
                                        <td style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-sm)' }}>
                                            {record.id.slice(-8)}
                                        </td>
                                        <td style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-sm)' }}>
                                            {record.patient_id.slice(-8)}
                                        </td>
                                        <td>
                                            <span className={`badge ${record.diagnosis_id ? 'badge-success' : 'badge-warning'}`}>
                                                {record.diagnosis_id ? 'Diagnosed' : 'Pending'}
                                            </span>
                                        </td>
                                        <td>{new Date(record.created_at).toLocaleString()}</td>
                                        <td>
                                            <Link
                                                to={`/diagnosis/${record.id}`}
                                                className="btn btn-secondary"
                                                style={{ fontSize: 'var(--font-size-sm)' }}
                                            >
                                                Continue
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Waiting Queue */}
            <div className="card">
                <div className="card-header flex justify-between items-center">
                    <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <Clock size={20} />
                        Waiting Queue ({queueData?.total_waiting || 0})
                    </h3>
                    <Link to="/queue" className="btn btn-secondary" style={{ fontSize: 'var(--font-size-sm)' }}>
                        Full View
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
                                    <th>Priority</th>
                                    <th>Wait Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                {queueData.waiting.slice(0, 10).map((token) => (
                                    <tr key={token.id}>
                                        <td>
                                            <span className="badge badge-primary" style={{ fontWeight: 600 }}>
                                                {token.token_number}
                                            </span>
                                        </td>
                                        <td style={{ fontWeight: 500 }}>{token.patient_name}</td>
                                        <td style={{ textTransform: 'capitalize' }}>{token.species}</td>
                                        <td>
                                            <span className={`badge ${token.priority > 5 ? 'badge-error' : token.priority > 0 ? 'badge-warning' : 'badge-secondary'}`}>
                                                {token.priority > 5 ? 'Emergency' : token.priority > 0 ? 'Priority' : 'Normal'}
                                            </span>
                                        </td>
                                        <td>~{token.estimated_wait_minutes} min</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-gray-500)' }}>
                            No patients waiting
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
