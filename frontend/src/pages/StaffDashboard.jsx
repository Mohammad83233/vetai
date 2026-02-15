import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { queueAPI, patientsAPI } from '../services/api'
import { Ticket, Search, Plus, AlertCircle, CheckCircle } from 'lucide-react'

export default function StaffDashboard() {
    const [searchQuery, setSearchQuery] = useState('')
    const [selectedPatient, setSelectedPatient] = useState(null)
    const [priority, setPriority] = useState(0)
    const [notes, setNotes] = useState('')
    const [issuedToken, setIssuedToken] = useState(null)

    const queryClient = useQueryClient()

    const { data: patients, isLoading: patientsLoading } = useQuery({
        queryKey: ['patients', searchQuery],
        queryFn: async () => {
            if (searchQuery.length < 2) return []
            const res = await patientsAPI.list({ q: searchQuery })
            return res.data
        },
        enabled: searchQuery.length >= 2
    })

    const { data: queueData } = useQuery({
        queryKey: ['queue'],
        queryFn: async () => {
            const res = await queueAPI.display()
            return res.data
        },
        refetchInterval: 5000
    })

    const issueTokenMutation = useMutation({
        mutationFn: (data) => queueAPI.issueToken(data),
        onSuccess: (res) => {
            setIssuedToken(res.data)
            setSelectedPatient(null)
            setNotes('')
            setPriority(0)
            queryClient.invalidateQueries(['queue'])
        }
    })

    const handleIssueToken = () => {
        if (!selectedPatient) return

        issueTokenMutation.mutate({
            patient_id: selectedPatient.id || selectedPatient._id,
            priority,
            notes
        })
    }

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">Token Management</h1>
                    <p className="page-subtitle">Issue tokens and manage patient queue</p>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
                {/* Issue Token Section */}
                <div className="card">
                    <div className="card-header">
                        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            <Ticket size={20} />
                            Issue New Token
                        </h3>
                    </div>
                    <div className="card-body">
                        {issuedToken ? (
                            <div style={{ textAlign: 'center', padding: 'var(--space-4)' }}>
                                <CheckCircle size={48} color="var(--color-success-500)" style={{ marginBottom: 'var(--space-3)' }} />
                                <h4 style={{ marginBottom: 'var(--space-2)' }}>Token Issued Successfully!</h4>
                                <div className="token-display" style={{ marginBottom: 'var(--space-4)' }}>
                                    {issuedToken.token_number}
                                </div>
                                <p style={{ color: 'var(--color-gray-500)', marginBottom: 'var(--space-4)' }}>
                                    Patient: {issuedToken.patient_name}<br />
                                    Est. Wait: {issuedToken.estimated_wait_minutes} minutes
                                </p>
                                <button className="btn btn-primary" onClick={() => setIssuedToken(null)}>
                                    Issue Another Token
                                </button>
                            </div>
                        ) : (
                            <>
                                {/* Patient Search */}
                                <div className="form-group">
                                    <label className="form-label">Search Patient</label>
                                    <div style={{ position: 'relative' }}>
                                        <Search size={18} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-gray-400)' }} />
                                        <input
                                            type="text"
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            className="form-input"
                                            style={{ paddingLeft: 40 }}
                                            placeholder="Search by patient or owner name..."
                                        />
                                    </div>
                                </div>

                                {/* Search Results */}
                                {patients && patients.length > 0 && (
                                    <div style={{
                                        maxHeight: 200,
                                        overflowY: 'auto',
                                        border: '1px solid var(--color-gray-200)',
                                        borderRadius: 'var(--radius)',
                                        marginBottom: 'var(--space-4)'
                                    }}>
                                        {patients.map((patient) => (
                                            <div
                                                key={patient.id || patient._id}
                                                onClick={() => { setSelectedPatient(patient); setSearchQuery(''); }}
                                                style={{
                                                    padding: 'var(--space-3)',
                                                    borderBottom: '1px solid var(--color-gray-100)',
                                                    cursor: 'pointer',
                                                    background: selectedPatient?.id === patient.id ? 'var(--color-primary-50)' : 'white'
                                                }}
                                            >
                                                <div style={{ fontWeight: 500 }}>{patient.name}</div>
                                                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-500)' }}>
                                                    {patient.species} • Owner: {patient.owner?.name}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Selected Patient */}
                                {selectedPatient && (
                                    <div className="alert alert-info" style={{ marginBottom: 'var(--space-4)' }}>
                                        <div>
                                            <strong>Selected:</strong> {selectedPatient.name} ({selectedPatient.species})<br />
                                            <span style={{ fontSize: 'var(--font-size-sm)' }}>Owner: {selectedPatient.owner?.name}</span>
                                        </div>
                                    </div>
                                )}

                                {/* Priority */}
                                <div className="form-group">
                                    <label className="form-label">Priority Level</label>
                                    <select
                                        value={priority}
                                        onChange={(e) => setPriority(Number(e.target.value))}
                                        className="form-input form-select"
                                    >
                                        <option value={0}>Normal</option>
                                        <option value={5}>High Priority</option>
                                        <option value={10}>Emergency</option>
                                    </select>
                                </div>

                                {/* Notes */}
                                <div className="form-group">
                                    <label className="form-label">Notes (Optional)</label>
                                    <textarea
                                        value={notes}
                                        onChange={(e) => setNotes(e.target.value)}
                                        className="form-input form-textarea"
                                        placeholder="Any special notes..."
                                        rows={2}
                                    />
                                </div>

                                <button
                                    className="btn btn-primary btn-lg"
                                    style={{ width: '100%' }}
                                    disabled={!selectedPatient || issueTokenMutation.isPending}
                                    onClick={handleIssueToken}
                                >
                                    {issueTokenMutation.isPending ? (
                                        <span className="loading-spinner" style={{ width: 18, height: 18 }}></span>
                                    ) : (
                                        <>
                                            <Plus size={18} />
                                            Issue Token
                                        </>
                                    )}
                                </button>

                                {issueTokenMutation.isError && (
                                    <div className="alert alert-error" style={{ marginTop: 'var(--space-4)' }}>
                                        <AlertCircle size={18} />
                                        <span>Failed to issue token. Please try again.</span>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>

                {/* Current Queue */}
                <div className="card">
                    <div className="card-header flex justify-between items-center">
                        <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>
                            Waiting Queue ({queueData?.total_waiting || 0})
                        </h3>
                    </div>
                    <div className="card-body" style={{ padding: 0, maxHeight: 400, overflowY: 'auto' }}>
                        {queueData?.waiting?.length > 0 ? (
                            <table className="table">
                                <thead>
                                    <tr>
                                        <th>Token</th>
                                        <th>Patient</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {queueData.waiting.map((token) => (
                                        <tr key={token.id}>
                                            <td>
                                                <span className="badge badge-primary" style={{ fontWeight: 600 }}>
                                                    {token.token_number}
                                                </span>
                                            </td>
                                            <td>
                                                <div style={{ fontWeight: 500 }}>{token.patient_name}</div>
                                                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-500)' }}>
                                                    {token.species}
                                                </div>
                                            </td>
                                            <td>
                                                <span className={`badge ${token.priority > 5 ? 'badge-error' : token.priority > 0 ? 'badge-warning' : 'badge-secondary'}`}>
                                                    {token.priority > 5 ? 'Emergency' : token.priority > 0 ? 'Priority' : 'Normal'}
                                                </span>
                                            </td>
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
        </div>
    )
}
