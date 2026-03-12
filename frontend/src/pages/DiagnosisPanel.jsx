import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { clinicalAPI, diagnosisAPI, patientsAPI, treatmentAPI, reportsAPI, imagesAPI } from '../services/api'
import { Brain, AlertCircle, CheckCircle, HelpCircle, Pill, FileText, Download, Upload, Image, X, Target, Shield } from 'lucide-react'

export default function DiagnosisPanel() {
    const { recordId } = useParams()
    const navigate = useNavigate()

    const [symptoms, setSymptoms] = useState('')
    const [selectedPatientId, setSelectedPatientId] = useState('')
    const [patientSearch, setPatientSearch] = useState('')
    const [diagnosisResult, setDiagnosisResult] = useState(null)
    const [treatmentPlan, setTreatmentPlan] = useState(null)
    const [activeTab, setActiveTab] = useState('symptoms')

    // Vitals input states
    const [temperature, setTemperature] = useState('')
    const [heartRate, setHeartRate] = useState('')
    const [durationDays, setDurationDays] = useState('')

    // Follow-up symptom selection (multi-select from combined list)
    const [selectedFollowUps, setSelectedFollowUps] = useState({})

    // Final diagnosis chosen by doctor
    const [finalDiagnosis, setFinalDiagnosis] = useState(null)

    // Image upload states
    const [uploadedImages, setUploadedImages] = useState([])
    const [isUploading, setIsUploading] = useState(false)
    const [imageAnalysis, setImageAnalysis] = useState(null)



    // Fetch clinical record if editing existing
    const { data: clinicalRecord } = useQuery({
        queryKey: ['clinical-record', recordId],
        queryFn: async () => {
            const res = await clinicalAPI.getRecord(recordId)
            setSelectedPatientId(res.data.patient_id)
            return res.data
        },
        enabled: !!recordId
    })

    // Fetch patient data
    const { data: patient } = useQuery({
        queryKey: ['patient', selectedPatientId],
        queryFn: async () => {
            const res = await patientsAPI.get(selectedPatientId)
            return res.data
        },
        enabled: !!selectedPatientId
    })

    // Patient search
    const { data: patients } = useQuery({
        queryKey: ['patients-search', patientSearch],
        queryFn: async () => {
            const res = await patientsAPI.list({ q: patientSearch })
            return res.data
        },
        enabled: patientSearch.length >= 2 && !selectedPatientId
    })

    // Diagnosis mutation
    const diagnosisMutation = useMutation({
        mutationFn: (data) => diagnosisAPI.predict(data),
        onSuccess: (res) => {
            setDiagnosisResult(res.data)
            setActiveTab('results')
            setSelectedFollowUps({})
            setFinalDiagnosis(null)
        }
    })

    // Refine mutation
    const refineMutation = useMutation({
        mutationFn: (data) => diagnosisAPI.refineWithSymptoms(data),
        onSuccess: (res) => {
            setDiagnosisResult(res.data)
            setSelectedFollowUps({})
        }
    })

    // Finalize mutation
    const finalizeMutation = useMutation({
        mutationFn: (data) => diagnosisAPI.finalize(data),
        onSuccess: (res) => {
            setDiagnosisResult(res.data)
            setFinalDiagnosis(res.data.final_diagnosis)
        }
    })

    // Treatment mutation — lookup from treatment_knowledge.json
    const treatmentMutation = useMutation({
        mutationFn: (diseaseName) => treatmentAPI.lookup(diseaseName),
        onSuccess: (res) => {
            setTreatmentPlan(res.data)
            setActiveTab('treatment')
        }
    })

    // Report mutation
    const reportMutation = useMutation({
        mutationFn: (data) => reportsAPI.generate(data),
        onSuccess: (res) => {
            navigate(`/report/${res.data.id}`)
        }
    })

    const handleDiagnose = () => {
        if (!patient || !symptoms.trim()) return
        diagnosisMutation.mutate({
            patient_id: patient._id,
            species: patient.species,
            breed: patient.breed || '',
            symptoms: symptoms.split(',').map(s => s.trim()).filter(Boolean),
            weight_kg: patient.weight_kg || 10,
            age_months: patient.age_months || 24,
            temperature: temperature ? parseFloat(temperature) : undefined,
            heart_rate: heartRate ? parseInt(heartRate) : undefined,
            duration_days: durationDays ? parseInt(durationDays) : undefined,
            clinical_record_id: recordId || null
        })
    }

    // Handle refine: gather selected follow-up symptoms and call refine endpoint
    const handleRefineWithSymptoms = () => {
        if (!diagnosisResult?.id) return
        const selected = Object.entries(selectedFollowUps)
            .filter(([_, checked]) => checked)
            .map(([symptom]) => symptom)

        if (selected.length === 0) return

        refineMutation.mutate({
            diagnosis_id: diagnosisResult.id,
            selected_symptoms: selected
        })
    }

    // Handle final diagnosis selection
    const handleSelectFinalDiagnosis = (diseaseName) => {
        if (!diagnosisResult?.id) return
        finalizeMutation.mutate({
            diagnosis_id: diagnosisResult.id,
            selected_disease: diseaseName
        })
    }

    // Image upload handler
    const handleImageUpload = async (e) => {
        const files = Array.from(e.target.files)
        if (files.length === 0) return

        setIsUploading(true)

        for (const file of files) {
            try {
                const formData = new FormData()
                formData.append('file', file)
                formData.append('image_type', 'general')

                // Upload
                const uploadRes = await imagesAPI.upload(formData)
                const imageData = uploadRes.data

                setUploadedImages(prev => [...prev, imageData])

                // Auto-analyze
                const analyzeRes = await imagesAPI.analyze(imageData.image_id)
                setImageAnalysis(analyzeRes.data)
            } catch (err) {
                console.error('Image upload/analysis failed:', err)
            }
        }

        setIsUploading(false)
        e.target.value = ''
    }

    const removeImage = (imageId) => {
        setUploadedImages(prev => prev.filter(img => img.image_id !== imageId))
        if (uploadedImages.length <= 1) {
            setImageAnalysis(null)
        }
    }



    const handleGetTreatment = () => {
        if (!diagnosisResult) return
        const disease = finalDiagnosis || diagnosisResult.predictions?.[0]?.disease_name
        if (!disease) return
        treatmentMutation.mutate(disease)
    }

    const handleGenerateReport = () => {
        if (!recordId || !patient) return
        reportMutation.mutate({
            patient_id: patient._id,
            clinical_record_id: recordId,
            diagnosis_id: diagnosisResult?.id || null,
            treatment_id: treatmentPlan?.id || null,
            auto_generate: true
        })
    }

    const selectedCount = Object.values(selectedFollowUps).filter(v => v).length

    // Tab configuration
    const tabs = [
        { id: 'symptoms', label: 'Symptoms', icon: <Brain size={16} /> },
        { id: 'images', label: 'Images', icon: <Image size={16} /> },
        { id: 'results', label: 'Results', icon: <CheckCircle size={16} /> },
        { id: 'treatment', label: 'Treatment', icon: <Pill size={16} /> }
    ]

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">AI Diagnosis Assistant</h1>
                    <p className="page-subtitle">Enter symptoms to get AI-powered disease predictions</p>
                </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
                {/* Main Panel */}
                <div style={{ gridColumn: 'span 2' }}>
                    {/* Tabs */}
                    <div style={{
                        display: 'flex',
                        background: 'white',
                        borderRadius: '12px 12px 0 0',
                        borderBottom: '2px solid #f1f5f9',
                        overflow: 'hidden'
                    }}>
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                style={{
                                    flex: 1,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: 6,
                                    padding: '14px 12px',
                                    border: 'none',
                                    background: activeTab === tab.id ? 'white' : '#f8fafc',
                                    color: activeTab === tab.id ? '#3b82f6' : '#94a3b8',
                                    fontWeight: 600,
                                    fontSize: '0.9rem',
                                    cursor: 'pointer',
                                    borderBottom: activeTab === tab.id ? '3px solid #3b82f6' : '3px solid transparent',
                                    transition: 'all 0.2s ease',
                                    fontFamily: 'inherit'
                                }}
                            >
                                {tab.icon}
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {/* ═══════════════════════════════════════════ */}
                    {/* SYMPTOMS TAB                               */}
                    {/* ═══════════════════════════════════════════ */}
                    {activeTab === 'symptoms' && (
                        <div className="card" style={{ borderRadius: '0 0 12px 12px', borderTop: 'none' }}>
                            <div className="card-header">
                                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                    <Brain size={20} />
                                    Clinical Input
                                </h3>
                            </div>
                            <div className="card-body">
                                {/* Patient Selection */}
                                {!selectedPatientId && (
                                    <div className="form-group">
                                        <label className="form-label">Select Patient</label>
                                        <input
                                            type="text"
                                            value={patientSearch}
                                            onChange={(e) => setPatientSearch(e.target.value)}
                                            className="form-input"
                                            placeholder="Search patient..."
                                        />
                                        {patients?.length > 0 && (
                                            <div style={{
                                                maxHeight: 150,
                                                overflowY: 'auto',
                                                border: '1px solid var(--color-gray-200)',
                                                borderRadius: 'var(--radius)',
                                                marginTop: 'var(--space-2)'
                                            }}>
                                                {patients.map((p) => (
                                                    <div
                                                        key={p._id}
                                                        onClick={() => { setSelectedPatientId(p._id); setPatientSearch(''); }}
                                                        style={{
                                                            padding: 'var(--space-3)',
                                                            borderBottom: '1px solid var(--color-gray-100)',
                                                            cursor: 'pointer'
                                                        }}
                                                    >
                                                        <strong>{p.name}</strong> ({p.species}) - {p.owner?.name}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                <div className="form-group">
                                    <label className="form-label">Symptoms</label>
                                    <textarea
                                        value={symptoms}
                                        onChange={(e) => setSymptoms(e.target.value)}
                                        className="form-input form-textarea"
                                        placeholder="e.g., vomiting, lethargy, loss of appetite, diarrhea"
                                        rows={4}
                                    />

                                </div>

                                {/* Vitals Input */}
                                <div className="form-group" style={{ marginTop: 'var(--space-4)' }}>
                                    <label className="form-label" style={{ fontWeight: 600, marginBottom: 'var(--space-2)' }}>
                                        🩺 Clinical Vitals
                                    </label>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-3)' }}>
                                        <div>
                                            <label className="form-label" style={{ fontSize: 'var(--font-size-sm)' }}>Temperature (°C)</label>
                                            <input
                                                type="number"
                                                step="0.1"
                                                value={temperature}
                                                onChange={(e) => setTemperature(e.target.value)}
                                                className="form-input"
                                                placeholder="e.g., 39.5"
                                            />
                                        </div>
                                        <div>
                                            <label className="form-label" style={{ fontSize: 'var(--font-size-sm)' }}>Heart Rate (bpm)</label>
                                            <input
                                                type="number"
                                                value={heartRate}
                                                onChange={(e) => setHeartRate(e.target.value)}
                                                className="form-input"
                                                placeholder="e.g., 120"
                                            />
                                        </div>
                                        <div>
                                            <label className="form-label" style={{ fontSize: 'var(--font-size-sm)' }}>Duration (days)</label>
                                            <input
                                                type="number"
                                                value={durationDays}
                                                onChange={(e) => setDurationDays(e.target.value)}
                                                className="form-input"
                                                placeholder="e.g., 3"
                                            />
                                        </div>
                                    </div>
                                </div>



                                <button
                                    className="btn btn-primary btn-lg"
                                    style={{ width: '100%' }}
                                    onClick={handleDiagnose}
                                    disabled={!patient || !symptoms.trim() || diagnosisMutation.isPending}
                                >
                                    {diagnosisMutation.isPending ? (
                                        <span className="loading-spinner" style={{ width: 18, height: 18 }}></span>
                                    ) : (
                                        <>
                                            <Brain size={18} />
                                            Get AI Diagnosis
                                        </>
                                    )}
                                </button>

                                {diagnosisMutation.isError && (
                                    <div className="alert alert-error" style={{ marginTop: 'var(--space-4)' }}>
                                        <AlertCircle size={18} />
                                        <span>Diagnosis failed. Please try again.</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* ═══════════════════════════════════════════ */}
                    {/* IMAGES TAB                                 */}
                    {/* ═══════════════════════════════════════════ */}
                    {activeTab === 'images' && (
                        <div className="card" style={{ borderRadius: '0 0 12px 12px', borderTop: 'none' }}>
                            <div className="card-header">
                                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                    <Image size={20} />
                                    AI Disease Detection
                                </h3>
                                <p style={{ margin: '4px 0 0 0', fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-500)' }}>
                                    Upload a clinical image for AI-powered disease detection
                                </p>
                            </div>
                            <div className="card-body">
                                {/* Upload Drop Zone */}
                                <div
                                    style={{
                                        border: '2px dashed #cbd5e1',
                                        borderRadius: 12,
                                        padding: 'var(--space-8)',
                                        textAlign: 'center',
                                        cursor: 'pointer',
                                        background: '#f8fafc',
                                        transition: 'all 0.2s ease'
                                    }}
                                    onClick={() => document.getElementById('image-upload').click()}
                                    onMouseEnter={e => {
                                        e.currentTarget.style.borderColor = '#3b82f6'
                                        e.currentTarget.style.background = '#eff6ff'
                                    }}
                                    onMouseLeave={e => {
                                        e.currentTarget.style.borderColor = '#cbd5e1'
                                        e.currentTarget.style.background = '#f8fafc'
                                    }}
                                >
                                    <input
                                        id="image-upload"
                                        type="file"
                                        accept="image/*"
                                        multiple
                                        onChange={handleImageUpload}
                                        style={{ display: 'none' }}
                                    />
                                    {isUploading ? (
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 'var(--space-2)' }}>
                                            <span className="loading-spinner" style={{ width: 20, height: 20 }}></span>
                                            <span>Uploading & Analyzing...</span>
                                        </div>
                                    ) : (
                                        <div>
                                            <Upload size={36} style={{ color: '#94a3b8', marginBottom: 8 }} />
                                            <p style={{ margin: 0, color: '#475569', fontWeight: 500, fontSize: '0.95rem' }}>
                                                Drop clinical images here or click to upload
                                            </p>
                                            <p style={{ margin: '4px 0 0 0', fontSize: 'var(--font-size-sm)', color: '#94a3b8' }}>
                                                Trained veterinary disease detection model
                                            </p>
                                        </div>
                                    )}
                                </div>

                                {/* Uploaded Images Grid */}
                                {uploadedImages.length > 0 && (
                                    <div style={{ marginTop: 'var(--space-4)' }}>
                                        <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
                                            {uploadedImages.map((img) => (
                                                <div
                                                    key={img.image_id}
                                                    style={{
                                                        position: 'relative',
                                                        width: 100,
                                                        height: 100,
                                                        borderRadius: 'var(--radius)',
                                                        overflow: 'hidden',
                                                        border: '2px solid var(--color-success-500)'
                                                    }}
                                                >
                                                    <img
                                                        src={`/uploads/${img.thumbnail_path?.split('uploads/')[1] || ''}`}
                                                        alt="Clinical"
                                                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                                        onError={(e) => { e.target.style.display = 'none' }}
                                                    />
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); removeImage(img.image_id); }}
                                                        style={{
                                                            position: 'absolute',
                                                            top: 2,
                                                            right: 2,
                                                            background: 'var(--color-error-500)',
                                                            border: 'none',
                                                            borderRadius: '50%',
                                                            padding: 2,
                                                            cursor: 'pointer',
                                                            display: 'flex'
                                                        }}
                                                    >
                                                        <X size={14} color="white" />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>

                                        {imageAnalysis && (
                                            <div style={{
                                                marginTop: 'var(--space-4)',
                                                border: '1px solid var(--color-success-200)',
                                                borderRadius: 'var(--radius)',
                                                overflow: 'hidden'
                                            }}>
                                                <div style={{
                                                    padding: 'var(--space-3) var(--space-4)',
                                                    background: 'linear-gradient(135deg, #065f46, #047857)',
                                                    color: 'white',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 'var(--space-2)'
                                                }}>
                                                    <CheckCircle size={18} />
                                                    <strong>AI Disease Detection Result</strong>
                                                </div>
                                                <div style={{ padding: 'var(--space-4)', textAlign: 'center' }}>
                                                    {imageAnalysis.top_prediction ? (
                                                        <div style={{
                                                            fontSize: '1.25rem',
                                                            fontWeight: 700,
                                                            color: '#065f46',
                                                            textTransform: 'capitalize',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'center',
                                                            gap: '8px'
                                                        }}>
                                                            <Target size={20} />
                                                            Predicted Disease: {imageAnalysis.top_prediction.disease?.replace(/_/g, ' ')}
                                                        </div>
                                                    ) : (
                                                        <div style={{ color: 'var(--color-gray-500)' }}>No clear prediction found</div>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Get AI Diagnosis Button (image-based) */}
                                <button
                                    className="btn btn-primary btn-lg"
                                    style={{ width: '100%', marginTop: 'var(--space-6)' }}
                                    onClick={handleDiagnose}
                                    disabled={!patient || !symptoms.trim() || diagnosisMutation.isPending}
                                >
                                    {diagnosisMutation.isPending ? (
                                        <span className="loading-spinner" style={{ width: 18, height: 18 }}></span>
                                    ) : (
                                        <>
                                            <Brain size={18} />
                                            Get AI Diagnosis
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ═══════════════════════════════════════════ */}
                    {/* RESULTS TAB                                */}
                    {/* ═══════════════════════════════════════════ */}
                    {activeTab === 'results' && diagnosisResult && (
                        <div className="card" style={{ borderRadius: '0 0 12px 12px', borderTop: 'none' }}>
                            <div className="card-header">
                                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                    <CheckCircle size={20} color="var(--color-success-500)" />
                                    Diagnosis Results
                                </h3>
                            </div>
                            <div className="card-body">

                                {/* Final diagnosis banner */}
                                {finalDiagnosis && (
                                    <div style={{
                                        background: 'linear-gradient(135deg, #065f46, #047857)',
                                        color: 'white',
                                        padding: 'var(--space-4)',
                                        borderRadius: 'var(--radius)',
                                        marginBottom: 'var(--space-4)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 'var(--space-3)'
                                    }}>
                                        <Shield size={24} />
                                        <div>
                                            <div style={{ fontSize: 'var(--font-size-sm)', opacity: 0.9 }}>Doctor's Final Diagnosis</div>
                                            <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700 }}>{finalDiagnosis}</div>
                                        </div>
                                    </div>
                                )}

                                {/* Top 3 Predictions */}
                                <h4 style={{ fontWeight: 600, marginBottom: 'var(--space-3)' }}>Top 3 Predicted Conditions</h4>
                                {diagnosisResult.predictions.map((pred, idx) => (
                                    <div
                                        key={idx}
                                        style={{
                                            padding: 'var(--space-4)',
                                            border: finalDiagnosis === pred.disease_name
                                                ? '2px solid #065f46'
                                                : idx === 0 ? '2px solid var(--color-success-400)' : '1px solid var(--color-gray-200)',
                                            borderRadius: 'var(--radius)',
                                            marginBottom: 'var(--space-3)',
                                            background: finalDiagnosis === pred.disease_name
                                                ? '#ecfdf5'
                                                : idx === 0 ? 'var(--color-success-50)' : 'white',
                                            boxShadow: finalDiagnosis === pred.disease_name
                                                ? '0 2px 12px rgba(5,150,105,0.15)'
                                                : idx === 0 ? '0 2px 8px rgba(34,197,94,0.10)' : 'none',
                                            transition: 'all 0.2s ease'
                                        }}
                                    >
                                        {/* Disease header with scores */}
                                        <div className="flex justify-between items-center" style={{ marginBottom: 'var(--space-2)' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                                {idx === 0 && !finalDiagnosis && <span style={{ fontSize: '1.2em' }}>🏆</span>}
                                                {finalDiagnosis === pred.disease_name && <Shield size={20} color="#065f46" />}
                                                <div style={{ fontWeight: 700, fontSize: idx === 0 ? 'var(--font-size-lg)' : 'var(--font-size-base)' }}>
                                                    {pred.disease_name}
                                                </div>
                                            </div>
                                            <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
                                                <span style={{
                                                    padding: '4px 14px',
                                                    borderRadius: '12px',
                                                    background: (pred.symptom_confidence || 0) >= 50
                                                        ? 'var(--color-success-100)'
                                                        : 'var(--color-gray-100)',
                                                    color: (pred.symptom_confidence || 0) >= 50
                                                        ? 'var(--color-success-700)'
                                                        : 'var(--color-gray-700)',
                                                    fontSize: 'var(--font-size-sm)',
                                                    fontWeight: 600
                                                }}>
                                                    Confidence: {pred.symptom_confidence || 0}%
                                                </span>
                                            </div>
                                        </div>

                                        {/* Matched symptoms count */}
                                        {pred.matched_symptoms?.length > 0 && (
                                            <div style={{ marginBottom: 'var(--space-2)' }}>
                                                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-success-600)', fontWeight: 500 }}>
                                                    ✅ {pred.matched_symptoms.length}/{pred.all_disease_symptoms?.length || 8} symptoms matched
                                                </div>
                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: 'var(--space-1)' }}>
                                                    {pred.matched_symptoms.map((s, si) => (
                                                        <span key={si} style={{
                                                            display: 'inline-flex', alignItems: 'center', gap: '3px',
                                                            padding: '1px 8px', borderRadius: '10px',
                                                            background: 'var(--color-success-100)', color: 'var(--color-success-700)',
                                                            fontSize: '12px', fontWeight: 500
                                                        }}>
                                                            <CheckCircle size={10} /> {s}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Select Final Diagnosis button */}
                                        {!finalDiagnosis && (
                                            <button
                                                onClick={() => handleSelectFinalDiagnosis(pred.disease_name)}
                                                disabled={finalizeMutation.isPending}
                                                style={{
                                                    marginTop: 'var(--space-2)',
                                                    padding: '6px 16px',
                                                    border: '1px solid var(--color-gray-300)',
                                                    borderRadius: 'var(--radius)',
                                                    background: 'white',
                                                    cursor: 'pointer',
                                                    fontSize: 'var(--font-size-sm)',
                                                    fontWeight: 500,
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 'var(--space-1)',
                                                    transition: 'all 0.15s ease'
                                                }}
                                            >
                                                <Target size={14} />
                                                Select as Final Diagnosis
                                            </button>
                                        )}
                                    </div>
                                ))}

                                {/* Follow-Up Symptoms Multi-Select */}
                                {diagnosisResult.followup_symptoms?.length > 0 && !finalDiagnosis && (
                                    <div style={{
                                        marginTop: 'var(--space-4)',
                                        padding: 'var(--space-4)',
                                        border: '1px solid var(--color-primary-200)',
                                        borderRadius: 'var(--radius)',
                                        background: 'var(--color-primary-50)'
                                    }}>
                                        <h4 style={{
                                            fontWeight: 600,
                                            marginBottom: 'var(--space-2)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 'var(--space-2)',
                                            color: 'var(--color-primary-700)'
                                        }}>
                                            <HelpCircle size={18} />
                                            Additional Symptoms — Does the patient show any of these?
                                        </h4>
                                        <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-600)', marginBottom: 'var(--space-3)' }}>
                                            Select any observed symptoms below to refine the prediction scores.
                                        </p>

                                        <div style={{
                                            background: 'white',
                                            borderRadius: 'var(--radius)',
                                            padding: 'var(--space-2)',
                                            border: '1px solid var(--color-gray-200)',
                                            maxHeight: 280,
                                            overflowY: 'auto'
                                        }}>
                                            {diagnosisResult.followup_symptoms.map((symptom, si) => (
                                                <label
                                                    key={si}
                                                    style={{
                                                        display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
                                                        padding: 'var(--space-2) var(--space-3)',
                                                        cursor: 'pointer',
                                                        borderRadius: 'var(--radius)',
                                                        transition: 'background 0.15s',
                                                        background: selectedFollowUps[symptom] ? 'var(--color-primary-50)' : 'transparent'
                                                    }}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={!!selectedFollowUps[symptom]}
                                                        onChange={(e) => setSelectedFollowUps(prev => ({
                                                            ...prev,
                                                            [symptom]: e.target.checked
                                                        }))}
                                                        style={{ width: 18, height: 18, accentColor: 'var(--color-primary-500)' }}
                                                    />
                                                    <span style={{
                                                        fontSize: 'var(--font-size-sm)',
                                                        color: selectedFollowUps[symptom] ? 'var(--color-primary-700)' : 'var(--color-gray-700)',
                                                        fontWeight: selectedFollowUps[symptom] ? 600 : 400
                                                    }}>
                                                        {symptom}
                                                    </span>
                                                </label>
                                            ))}
                                        </div>

                                        {/* Refine Prediction Button */}
                                        {selectedCount > 0 && (
                                            <button
                                                className="btn btn-primary btn-lg"
                                                style={{
                                                    width: '100%',
                                                    marginTop: 'var(--space-3)',
                                                    background: 'linear-gradient(135deg, var(--color-primary-500), var(--color-primary-700))',
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 'var(--space-2)'
                                                }}
                                                onClick={handleRefineWithSymptoms}
                                                disabled={refineMutation.isPending}
                                            >
                                                {refineMutation.isPending ? (
                                                    <span className="loading-spinner" style={{ width: 18, height: 18 }}></span>
                                                ) : (
                                                    <>
                                                        <Brain size={18} />
                                                        Refine Prediction ({selectedCount} symptom{selectedCount > 1 ? 's' : ''} selected)
                                                    </>
                                                )}
                                            </button>
                                        )}
                                    </div>
                                )}

                                {/* Get Treatment Plan Button */}
                                <button
                                    className="btn btn-success btn-lg"
                                    style={{ width: '100%', marginTop: 'var(--space-4)' }}
                                    onClick={handleGetTreatment}
                                    disabled={treatmentMutation.isPending}
                                >
                                    {treatmentMutation.isPending ? (
                                        <span className="loading-spinner" style={{ width: 18, height: 18 }}></span>
                                    ) : (
                                        <>
                                            <Pill size={18} />
                                            Get Treatment Plan{finalDiagnosis ? ` for ${finalDiagnosis}` : ''}
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ═══════════════════════════════════════════ */}
                    {/* TREATMENT TAB                              */}
                    {/* ═══════════════════════════════════════════ */}
                    {activeTab === 'treatment' && treatmentPlan && (
                        <div className="card" style={{ borderRadius: '0 0 12px 12px', borderTop: 'none' }}>
                            <div className="card-header">
                                <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                    <Pill size={20} color="var(--color-success-500)" />
                                    Treatment Recommendation
                                </h3>
                            </div>
                            <div className="card-body">
                                {/* Predicted Disease */}
                                <div style={{
                                    padding: 'var(--space-3) var(--space-4)',
                                    background: 'linear-gradient(135deg, #065f46, #047857)',
                                    color: 'white',
                                    borderRadius: 'var(--radius)',
                                    marginBottom: 'var(--space-4)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 'var(--space-2)'
                                }}>
                                    <Target size={18} />
                                    <strong>Predicted Disease:</strong>
                                    <span style={{ marginLeft: 4 }}>{treatmentPlan.disease}</span>
                                </div>

                                {/* Medicines */}
                                <div style={{
                                    padding: 'var(--space-4)',
                                    border: '1px solid var(--color-gray-200)',
                                    borderRadius: 'var(--radius)',
                                    marginBottom: 'var(--space-3)'
                                }}>
                                    <h5 style={{ fontWeight: 600, marginBottom: 'var(--space-3)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                        <Pill size={16} />
                                        Medicines
                                    </h5>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        {treatmentPlan.medicines?.map((med, idx) => (
                                            <div key={idx} style={{
                                                padding: '8px 14px',
                                                background: 'var(--color-success-50)',
                                                borderRadius: 'var(--radius)',
                                                border: '1px solid var(--color-success-200)',
                                                fontSize: 'var(--font-size-base)',
                                                fontWeight: 500,
                                                color: '#065f46',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '8px'
                                            }}>
                                                <span style={{
                                                    width: 22, height: 22, borderRadius: '50%',
                                                    background: 'var(--color-success-500)', color: 'white',
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                    fontSize: '0.7rem', fontWeight: 700, flexShrink: 0
                                                }}>{idx + 1}</span>
                                                {med}
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Treatment Duration */}
                                <div style={{
                                    padding: 'var(--space-4)',
                                    border: '1px solid var(--color-gray-200)',
                                    borderRadius: 'var(--radius)',
                                    marginBottom: 'var(--space-3)'
                                }}>
                                    <h5 style={{ fontWeight: 600, marginBottom: 'var(--space-2)' }}>Treatment Duration</h5>
                                    <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--color-primary-700)' }}>
                                        {treatmentPlan.treatment_duration}
                                    </div>
                                </div>

                                {/* Clinical Notes */}
                                <div style={{
                                    padding: 'var(--space-4)',
                                    border: '1px solid var(--color-warning-200)',
                                    borderRadius: 'var(--radius)',
                                    background: 'var(--color-warning-50)',
                                    marginBottom: 'var(--space-3)'
                                }}>
                                    <h5 style={{ fontWeight: 600, marginBottom: 'var(--space-2)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                        <AlertCircle size={16} />
                                        Clinical Notes
                                    </h5>
                                    <div style={{ fontSize: 'var(--font-size-base)', color: '#92400e', fontWeight: 500 }}>
                                        {treatmentPlan.notes}
                                    </div>
                                </div>

                                {recordId && (
                                    <button
                                        className="btn btn-primary btn-lg"
                                        style={{ width: '100%', marginTop: 'var(--space-4)' }}
                                        onClick={handleGenerateReport}
                                        disabled={reportMutation.isPending}
                                    >
                                        {reportMutation.isPending ? (
                                            <span className="loading-spinner" style={{ width: 18, height: 18 }}></span>
                                        ) : (
                                            <>
                                                <FileText size={18} />
                                                Generate Report
                                            </>
                                        )}
                                    </button>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Patient Info Sidebar */}
                <div>
                    <div className="card">
                        <div className="card-header">
                            <h3 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>Patient Info</h3>
                        </div>
                        <div className="card-body">
                            {patient ? (
                                <>
                                    <div style={{ marginBottom: 'var(--space-4)' }}>
                                        <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700 }}>{patient.name}</div>
                                        <span className="badge badge-primary" style={{ marginTop: 'var(--space-2)' }}>
                                            {patient.species}
                                        </span>
                                    </div>

                                    <div style={{ fontSize: 'var(--font-size-sm)' }}>
                                        <div style={{ marginBottom: 'var(--space-2)' }}>
                                            <strong>Breed:</strong> {patient.breed || 'N/A'}
                                        </div>
                                        <div style={{ marginBottom: 'var(--space-2)' }}>
                                            <strong>Weight:</strong> {patient.weight_kg} kg
                                        </div>
                                        <div style={{ marginBottom: 'var(--space-2)' }}>
                                            <strong>Age:</strong> {patient.age_months} months
                                        </div>
                                        <div style={{ marginBottom: 'var(--space-2)' }}>
                                            <strong>Sex:</strong> {patient.sex || 'Unknown'}
                                        </div>
                                        <hr style={{ margin: 'var(--space-4) 0', borderColor: 'var(--color-gray-200)' }} />
                                        <div style={{ marginBottom: 'var(--space-2)' }}>
                                            <strong>Owner:</strong> {patient.owner?.name}
                                        </div>
                                        <div>
                                            <strong>Phone:</strong> {patient.owner?.phone}
                                        </div>
                                    </div>
                                </>
                            ) : (
                                <div style={{ color: 'var(--color-gray-500)', textAlign: 'center', padding: 'var(--space-4)' }}>
                                    Select a patient to view details
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
