import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reportsAPI } from '../services/api';
import {
    FileText,
    Download,
    CheckCircle,
    ChevronLeft,
    User,
    Activity,
    Pill,
    Stethoscope,
    AlertCircle
} from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';

export default function ReportViewer() {
    const { reportId } = useParams();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [downloading, setDownloading] = useState(false);

    const { data: report, isLoading, error } = useQuery({
        queryKey: ['report', reportId],
        queryFn: async () => {
            const res = await reportsAPI.get(reportId);
            return res.data;
        },
        enabled: !!reportId
    });

    const finalizeMutation = useMutation({
        mutationFn: () => reportsAPI.finalize(reportId),
        onSuccess: () => {
            queryClient.invalidateQueries(['report', reportId]);
            queryClient.invalidateQueries(['my-records']);
        }
    });

    const handleDownloadPDF = async () => {
        try {
            setDownloading(true);
            const res = await reportsAPI.export({ report_id: reportId, format: 'pdf' });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `Report_${report.patient_name}_${new Date().toISOString().slice(0, 10)}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error('Failed to download PDF:', err);
        } finally {
            setDownloading(false);
        }
    };

    if (isLoading) return <LoadingSpinner fullScreen />;

    if (error || !report) {
        return (
            <div className="text-center" style={{ padding: 'var(--space-12)' }}>
                <AlertCircle size={48} color="var(--color-error-500)" style={{ marginBottom: 'var(--space-4)' }} />
                <h2 className="text-2xl font-bold mb-4">Report Not Found</h2>
                <p className="text-gray-500 mb-6">The report you are looking for does not exist or has been deleted.</p>
                <button className="btn btn-primary" onClick={() => navigate('/doctor')}>
                    Back to Dashboard
                </button>
            </div>
        );
    }

    const isFinal = report.status === 'final';

    return (
        <div style={{ maxWidth: '900px', margin: '0 auto', padding: 'var(--space-6)' }}>
            <style>
                {`
                .report-wrapper {
                    background: white;
                    border-radius: var(--radius-xl);
                    box-shadow: var(--shadow-xl);
                    overflow: hidden;
                    border: 1px solid var(--color-gray-200);
                }
                .report-header {
                    background: linear-gradient(135deg, var(--color-primary-600) 0%, var(--color-primary-800) 100%);
                    color: white;
                    padding: var(--space-8);
                }
                .report-body {
                    padding: var(--space-8);
                }
                .section-container {
                    margin-bottom: var(--space-10);
                }
                .section-title {
                    display: flex;
                    align-items: center;
                    gap: var(--space-2);
                    margin-bottom: var(--space-4);
                    padding-bottom: var(--space-2);
                    border-bottom: 2px solid var(--color-gray-100);
                    color: var(--color-gray-800);
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    font-size: var(--font-size-sm);
                    font-weight: 700;
                }
                .diagnosis-card {
                    background: var(--color-gray-50);
                    padding: var(--space-6);
                    border-radius: var(--radius-lg);
                    border: 1px solid var(--color-gray-200);
                }
                .medication-item {
                    display: flex;
                    gap: var(--space-4);
                    padding: var(--space-4);
                    border-radius: var(--radius);
                    border: 1px solid var(--color-gray-100);
                    margin-bottom: var(--space-3);
                    transition: border-color var(--transition);
                }
                .medication-item:hover {
                    border-color: var(--color-primary-200);
                }
                .info-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: var(--space-6);
                }
                .info-item label {
                    display: block;
                    font-size: var(--font-size-xs);
                    font-weight: 700;
                    color: var(--color-gray-400);
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                    margin-bottom: var(--space-1);
                }
                .info-item span {
                    font-weight: 500;
                    color: var(--color-gray-900);
                }
                .confidence-bar-bg {
                    height: 8px;
                    background: var(--color-gray-200);
                    border-radius: var(--radius-full);
                    margin-top: var(--space-2);
                    overflow: hidden;
                }
                .confidence-bar-fill {
                    height: 100%;
                    background: var(--color-primary-500);
                    border-radius: var(--radius-full);
                    transition: width 1s ease-out;
                }
                `}
            </style>

            {/* Top Navigation & Actions */}
            <div className="flex justify-between items-center mb-6">
                <button
                    className="flex items-center gap-2"
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-gray-600)', fontWeight: 500 }}
                    onClick={() => navigate(-1)}
                >
                    <ChevronLeft size={20} />
                    Back
                </button>

                <div className="flex gap-3">
                    <button
                        className="btn btn-secondary"
                        onClick={handleDownloadPDF}
                        disabled={downloading}
                    >
                        {downloading ? (
                            <span className="loading-spinner" style={{ width: 16, height: 16 }}></span>
                        ) : (
                            <Download size={18} />
                        )}
                        Download PDF
                    </button>

                    {!isFinal && (
                        <button
                            className="btn btn-success"
                            onClick={() => finalizeMutation.mutate()}
                            disabled={finalizeMutation.isPending}
                        >
                            {finalizeMutation.isPending ? (
                                <span className="loading-spinner" style={{ width: 16, height: 16 }}></span>
                            ) : (
                                <CheckCircle size={18} />
                            )}
                            Finalize Report
                        </button>
                    )}
                </div>
            </div>

            {/* Report Document */}
            <div className="report-wrapper">
                <div className="report-header">
                    <div className="flex justify-between items-start">
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                <Stethoscope size={32} />
                                <h1 style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 800, margin: 0 }}>Clinical Report</h1>
                            </div>
                            <p style={{ opacity: 0.9, fontSize: 'var(--font-size-sm)' }}>VetAI Clinical Decision Support System</p>
                        </div>
                        <div className="text-right">
                            <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, textTransform: 'uppercase', opacity: 0.8 }}>Status</div>
                            <div className={`badge ${isFinal ? 'badge-success' : 'badge-warning'}`} style={{ marginTop: 'var(--space-2)', fontSize: '10px', padding: 'var(--space-1) var(--space-3)' }}>
                                {isFinal ? 'FINALIZED' : 'DRAFT'}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="report-body">
                    {/* Patient Details */}
                    <div className="section-container">
                        <div className="section-title">
                            <User size={18} className="text-primary" />
                            Patient Information
                        </div>
                        <div className="info-grid">
                            <div className="info-item">
                                <label>Patient Name</label>
                                <span>{report.patient_name}</span>
                            </div>
                            <div className="info-item">
                                <label>Species / Breed</label>
                                <span>{report.species} {report.breed ? `(${report.breed})` : ''}</span>
                            </div>
                            <div className="info-item">
                                <label>Age / Weight</label>
                                <span>{report.age_months}m / {report.weight_kg}kg</span>
                            </div>
                            <div className="info-item">
                                <label>Owner</label>
                                <span>{report.owner_name}</span>
                            </div>
                            <div className="info-item">
                                <label>Date Issued</label>
                                <span>{new Date(report.created_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                    </div>

                    {/* Diagnosis Section */}
                    <div className="section-container">
                        <div className="section-title">
                            <Activity size={18} className="text-primary" />
                            Diagnosed Diseases
                        </div>
                        <div className="diagnosis-card">
                            <label style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-gray-500)', textTransform: 'uppercase', marginBottom: 'var(--space-1)', display: 'block' }}>Primary Diagnosis</label>
                            <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 800, color: 'var(--color-gray-900)' }}>
                                {report.assessment.primary_diagnosis}
                            </div>

                            {report.assessment.ai_confidence && (
                                <div style={{ marginTop: 'var(--space-4)', maxWidth: '300px' }}>
                                    <div className="flex justify-between items-center">
                                        <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-gray-600)' }}>AI Confidence</span>
                                        <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, color: 'var(--color-primary-600)' }}>
                                            {Math.round(report.assessment.ai_confidence * 100)}%
                                        </span>
                                    </div>
                                    <div className="confidence-bar-bg">
                                        <div
                                            className="confidence-bar-fill"
                                            style={{ width: `${report.assessment.ai_confidence * 100}%` }}
                                        />
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Treatment Plan */}
                    <div className="section-container">
                        <div className="section-title">
                            <Pill size={18} className="text-primary" />
                            Treatment Plan
                        </div>

                        {report.plan.medications?.length > 0 ? (
                            <div className="medication-list">
                                {report.plan.medications.map((med, idx) => (
                                    <div key={idx} className="medication-item">
                                        <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--color-primary-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                                            <Pill size={18} className="text-primary" />
                                        </div>
                                        <div>
                                            <div style={{ fontWeight: 700, color: 'var(--color-gray-900)' }}>{med.name}</div>
                                            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-600)', marginTop: '2px' }}>
                                                {med.dosage?.instructions}
                                            </div>
                                            <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-gray-400)', textTransform: 'uppercase', marginTop: '4px' }}>
                                                {med.dosage?.dose_mg}mg • {med.dosage?.duration_days} days
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p style={{ color: 'var(--color-gray-400)', fontStyle: 'italic' }}>No medications prescribed.</p>
                        )}

                        {report.plan.dietary_recommendations && (
                            <div className="alert alert-info" style={{ marginTop: 'var(--space-6)', padding: 'var(--space-4)' }}>
                                <AlertCircle size={18} />
                                <div>
                                    <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>Dietary Recommendations</div>
                                    <div style={{ fontSize: 'var(--font-size-sm)' }}>{report.plan.dietary_recommendations}</div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Report Footer */}
                <div style={{ background: 'var(--color-gray-50)', padding: 'var(--space-8)', borderTop: '1px solid var(--color-gray-100)', display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-sm)', color: 'var(--color-gray-500)' }}>
                    <div>
                        <span style={{ fontWeight: 600, color: 'var(--color-gray-700)' }}>Doctor:</span> {report.doctor_name}
                    </div>
                    <div>
                        <span style={{ fontWeight: 600, color: 'var(--color-gray-700)' }}>Clinic:</span> {report.clinic_name}
                    </div>
                </div>
            </div>
        </div>
    );
}
