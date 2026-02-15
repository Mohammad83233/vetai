export default function LoadingSpinner({ fullScreen = false }) {
    if (fullScreen) {
        return (
            <div style={{
                position: 'fixed',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'linear-gradient(135deg, var(--color-gray-50) 0%, var(--color-primary-50) 100%)'
            }}>
                <div style={{ textAlign: 'center' }}>
                    <div className="loading-spinner" style={{ width: 40, height: 40, borderWidth: 3 }}></div>
                    <p style={{ marginTop: 'var(--space-4)', color: 'var(--color-gray-500)' }}>Loading VetAI...</p>
                </div>
            </div>
        )
    }

    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-8)' }}>
            <div className="loading-spinner"></div>
        </div>
    )
}
