import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { patientsAPI } from '../services/api'
import { UserPlus, CheckCircle, AlertCircle } from 'lucide-react'

const SPECIES_OPTIONS = [
    { value: 'dog', label: 'Dog' },
    { value: 'cat', label: 'Cat' },
    { value: 'bird', label: 'Bird' },
    { value: 'rabbit', label: 'Rabbit' },
    { value: 'hamster', label: 'Hamster' },
    { value: 'guinea_pig', label: 'Guinea Pig' },
    { value: 'fish', label: 'Fish' },
    { value: 'reptile', label: 'Reptile' },
    { value: 'horse', label: 'Horse' },
    { value: 'cattle', label: 'Cattle' },
    { value: 'goat', label: 'Goat' },
    { value: 'sheep', label: 'Sheep' },
    { value: 'pig', label: 'Pig' },
    { value: 'poultry', label: 'Poultry' },
    { value: 'other', label: 'Other' }
]

export default function PatientRegistration() {
    const navigate = useNavigate()
    const [success, setSuccess] = useState(null)

    const [formData, setFormData] = useState({
        name: '',
        species: 'dog',
        breed: '',
        weight_kg: '',
        age_months: '',
        sex: 'unknown',
        color: '',
        microchip_id: '',
        owner: {
            name: '',
            phone: '',
            email: '',
            address: ''
        }
    })

    const createMutation = useMutation({
        mutationFn: (data) => patientsAPI.create(data),
        onSuccess: (res) => {
            setSuccess(res.data)
        }
    })

    const handleChange = (e) => {
        const { name, value } = e.target
        if (name.startsWith('owner.')) {
            const field = name.split('.')[1]
            setFormData(prev => ({
                ...prev,
                owner: { ...prev.owner, [field]: value }
            }))
        } else {
            setFormData(prev => ({ ...prev, [name]: value }))
        }
    }

    const handleSubmit = (e) => {
        e.preventDefault()

        const submitData = {
            ...formData,
            weight_kg: parseFloat(formData.weight_kg),
            age_months: parseInt(formData.age_months)
        }

        createMutation.mutate(submitData)
    }

    if (success) {
        return (
            <div>
                <div className="page-header">
                    <h1 className="page-title">Patient Registered</h1>
                </div>

                <div className="card" style={{ maxWidth: 500, margin: '0 auto', textAlign: 'center', padding: 'var(--space-8)' }}>
                    <CheckCircle size={64} color="var(--color-success-500)" style={{ marginBottom: 'var(--space-4)' }} />
                    <h2 style={{ marginBottom: 'var(--space-2)' }}>Success!</h2>
                    <p style={{ color: 'var(--color-gray-500)', marginBottom: 'var(--space-6)' }}>
                        <strong>{success.name}</strong> has been registered successfully.
                    </p>

                    <div style={{
                        background: 'var(--color-gray-50)',
                        padding: 'var(--space-4)',
                        borderRadius: 'var(--radius)',
                        marginBottom: 'var(--space-6)',
                        textAlign: 'left'
                    }}>
                        <div style={{ marginBottom: 'var(--space-2)' }}>
                            <strong>Species:</strong> {success.species}
                        </div>
                        <div style={{ marginBottom: 'var(--space-2)' }}>
                            <strong>Weight:</strong> {success.weight_kg} kg
                        </div>
                        <div>
                            <strong>Owner:</strong> {success.owner?.name}
                        </div>
                    </div>

                    <div className="flex gap-4" style={{ justifyContent: 'center' }}>
                        <button className="btn btn-primary" onClick={() => navigate('/staff')}>
                            Issue Token
                        </button>
                        <button className="btn btn-secondary" onClick={() => {
                            setSuccess(null); setFormData({
                                name: '',
                                species: 'dog',
                                breed: '',
                                weight_kg: '',
                                age_months: '',
                                sex: 'unknown',
                                color: '',
                                microchip_id: '',
                                owner: { name: '', phone: '', email: '', address: '' }
                            });
                        }}>
                            Register Another
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">Register New Patient</h1>
                    <p className="page-subtitle">Add a new patient to the system</p>
                </div>
            </div>

            <div className="card" style={{ maxWidth: 800, margin: '0 auto' }}>
                <div className="card-header">
                    <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <UserPlus size={20} />
                        Patient Information
                    </h3>
                </div>
                <div className="card-body">
                    <form onSubmit={handleSubmit}>
                        {/* Pet Information */}
                        <h4 style={{ fontWeight: 600, marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-2)', borderBottom: '1px solid var(--color-gray-200)' }}>
                            Pet Details
                        </h4>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="form-group">
                                <label className="form-label">Pet Name *</label>
                                <input
                                    type="text"
                                    name="name"
                                    value={formData.name}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="e.g., Max"
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label className="form-label">Species *</label>
                                <select
                                    name="species"
                                    value={formData.species}
                                    onChange={handleChange}
                                    className="form-input form-select"
                                    required
                                >
                                    {SPECIES_OPTIONS.map(opt => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="form-group">
                                <label className="form-label">Breed</label>
                                <input
                                    type="text"
                                    name="breed"
                                    value={formData.breed}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="e.g., Golden Retriever"
                                />
                            </div>

                            <div className="form-group">
                                <label className="form-label">Sex</label>
                                <select
                                    name="sex"
                                    value={formData.sex}
                                    onChange={handleChange}
                                    className="form-input form-select"
                                >
                                    <option value="unknown">Unknown</option>
                                    <option value="male">Male</option>
                                    <option value="female">Female</option>
                                </select>
                            </div>

                            <div className="form-group">
                                <label className="form-label">Weight (kg) *</label>
                                <input
                                    type="number"
                                    name="weight_kg"
                                    value={formData.weight_kg}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="e.g., 15.5"
                                    step="0.1"
                                    min="0.01"
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label className="form-label">Age (months) *</label>
                                <input
                                    type="number"
                                    name="age_months"
                                    value={formData.age_months}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="e.g., 24"
                                    min="0"
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label className="form-label">Color</label>
                                <input
                                    type="text"
                                    name="color"
                                    value={formData.color}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="e.g., Golden"
                                />
                            </div>

                            <div className="form-group">
                                <label className="form-label">Microchip ID</label>
                                <input
                                    type="text"
                                    name="microchip_id"
                                    value={formData.microchip_id}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="Optional"
                                />
                            </div>
                        </div>

                        {/* Owner Information */}
                        <h4 style={{ fontWeight: 600, marginBottom: 'var(--space-4)', marginTop: 'var(--space-6)', paddingBottom: 'var(--space-2)', borderBottom: '1px solid var(--color-gray-200)' }}>
                            Owner Details
                        </h4>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="form-group">
                                <label className="form-label">Owner Name *</label>
                                <input
                                    type="text"
                                    name="owner.name"
                                    value={formData.owner.name}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="e.g., John Smith"
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label className="form-label">Phone Number *</label>
                                <input
                                    type="tel"
                                    name="owner.phone"
                                    value={formData.owner.phone}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="e.g., +1234567890"
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label className="form-label">Email</label>
                                <input
                                    type="email"
                                    name="owner.email"
                                    value={formData.owner.email}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="Optional"
                                />
                            </div>

                            <div className="form-group">
                                <label className="form-label">Address</label>
                                <input
                                    type="text"
                                    name="owner.address"
                                    value={formData.owner.address}
                                    onChange={handleChange}
                                    className="form-input"
                                    placeholder="Optional"
                                />
                            </div>
                        </div>

                        {createMutation.isError && (
                            <div className="alert alert-error" style={{ marginTop: 'var(--space-4)' }}>
                                <AlertCircle size={18} />
                                <span>{createMutation.error?.response?.data?.detail || 'Failed to register patient'}</span>
                            </div>
                        )}

                        <div style={{ marginTop: 'var(--space-6)', display: 'flex', gap: 'var(--space-4)' }}>
                            <button
                                type="submit"
                                className="btn btn-primary btn-lg"
                                disabled={createMutation.isPending}
                            >
                                {createMutation.isPending ? (
                                    <span className="loading-spinner" style={{ width: 18, height: 18 }}></span>
                                ) : (
                                    <>
                                        <UserPlus size={18} />
                                        Register Patient
                                    </>
                                )}
                            </button>

                            <button
                                type="button"
                                className="btn btn-secondary btn-lg"
                                onClick={() => navigate('/staff')}
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    )
}
