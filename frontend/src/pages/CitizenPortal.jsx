import React, { useState, useEffect, createContext, useContext } from 'react';
import { Routes, Route, Link, useNavigate, Navigate } from 'react-router-dom';
import client from '../api/client';
import MapPicker from '../components/MapPicker';

// Auth Context for citizen session
const CitizenContext = createContext(null);

function CitizenPortal() {
    const [citizen, setCitizen] = useState(() => {
        const saved = localStorage.getItem('cst_citizen');
        return saved ? JSON.parse(saved) : null;
    });

    const login = (citizenData) => {
        setCitizen(citizenData);
        localStorage.setItem('cst_citizen', JSON.stringify(citizenData));
    };

    const logout = () => {
        setCitizen(null);
        localStorage.removeItem('cst_citizen');
    };

    return (
        <CitizenContext.Provider value={{ citizen, login, logout }}>
            <div>
                <div className="page-header">
                    <div className="container flex justify-between items-center">
                        <div>
                            <h1 className="page-title">Citizen Portal</h1>
                            <p className="text-muted">Report issues, track requests, and rate services</p>
                        </div>
                        {citizen && (
                            <div className="flex items-center gap-4">
                                <span className="text-sm">Welcome, <strong>{citizen.full_name}</strong></span>
                                {citizen.verification_state === 'verified' && <span className="badge badge-resolved">✓ Verified</span>}
                                <button className="btn btn-outline btn-sm" onClick={logout}>Logout</button>
                            </div>
                        )}
                    </div>
                </div>
                <div className="page-content container">
                    <Routes>
                        <Route path="/" element={<PortalHome />} />
                        <Route path="/register" element={<RegisterForm />} />
                        <Route path="/login" element={<LoginForm />} />
                        <Route path="/verify" element={<VerifyForm />} />
                        <Route path="/report" element={<ProtectedRoute><ReportIssue /></ProtectedRoute>} />
                        <Route path="/track" element={<ProtectedRoute><TrackRequest /></ProtectedRoute>} />
                        <Route path="/my-requests" element={<ProtectedRoute><MyRequests /></ProtectedRoute>} />
                    </Routes>
                </div>
            </div>
        </CitizenContext.Provider>
    );
}

// Protected Route Component
function ProtectedRoute({ children }) {
    const { citizen } = useContext(CitizenContext);
    const navigate = useNavigate();

    if (!citizen) {
        return (
            <div className="card text-center" style={{ maxWidth: '500px', margin: '2rem auto' }}>
                <div style={{ fontSize: '4rem' }}>🔒</div>
                <h2 className="mt-4">Login Required</h2>
                <p className="text-muted mt-2">You need to login to access this feature</p>
                <div className="flex gap-2 justify-center mt-4">
                    <Link to="/citizen/login" className="btn btn-primary">Login</Link>
                    <Link to="/citizen/register" className="btn btn-outline">Register</Link>
                </div>
            </div>
        );
    }

    if (citizen.verification_state !== 'verified') {
        return (
            <div className="card text-center" style={{ maxWidth: '500px', margin: '2rem auto' }}>
                <div style={{ fontSize: '4rem' }}>⚠️</div>
                <h2 className="mt-4">Verification Required</h2>
                <p className="text-muted mt-2">Your account needs to be verified to access this feature</p>
                <Link to="/citizen/verify" className="btn btn-primary mt-4">Verify Account</Link>
            </div>
        );
    }

    return children;
}

function PortalHome() {
    const { citizen } = useContext(CitizenContext);
    const navigate = useNavigate();

    return (
        <div>
            {!citizen && (
                <div className="card mb-4" style={{ background: 'linear-gradient(135deg, #2563eb 0%, #1e40af 100%)', color: 'white' }}>
                    <div className="flex justify-between items-center">
                        <div>
                            <h3>Welcome to CST Citizen Portal</h3>
                            <p style={{ opacity: 0.9 }}>Login or register to report issues and track your requests</p>
                        </div>
                        <div className="flex gap-2">
                            <Link to="/citizen/login" className="btn" style={{ background: 'white', color: '#2563eb' }}>Login</Link>
                            <Link to="/citizen/register" className="btn" style={{ background: 'rgba(255,255,255,0.2)', color: 'white' }}>Register</Link>
                        </div>
                    </div>
                </div>
            )}

            <div className="grid grid-3 gap-4">
                <div className="card" onClick={() => navigate('/citizen/report')} style={{ cursor: 'pointer' }}>
                    <div className="text-center">
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📝</div>
                        <h3>Report an Issue</h3>
                        <p className="text-sm text-muted mt-2">Submit a new service request</p>
                        {!citizen && <span className="badge mt-2" style={{ background: '#fef3c7', color: '#92400e' }}>Login Required</span>}
                    </div>
                </div>
                <div className="card" onClick={() => navigate('/citizen/track')} style={{ cursor: 'pointer' }}>
                    <div className="text-center">
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔍</div>
                        <h3>Track Request</h3>
                        <p className="text-sm text-muted mt-2">Check status by Request ID</p>
                        {!citizen && <span className="badge mt-2" style={{ background: '#fef3c7', color: '#92400e' }}>Login Required</span>}
                    </div>
                </div>
                <div className="card" onClick={() => navigate('/citizen/my-requests')} style={{ cursor: 'pointer' }}>
                    <div className="text-center">
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
                        <h3>My Requests</h3>
                        <p className="text-sm text-muted mt-2">View all your requests</p>
                        {!citizen && <span className="badge mt-2" style={{ background: '#fef3c7', color: '#92400e' }}>Login Required</span>}
                    </div>
                </div>
            </div>
        </div>
    );
}

function RegisterForm() {
    const [form, setForm] = useState({ full_name: '', email: '', phone: '', password: '' });
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const { login } = useContext(CitizenContext);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await client.post('/citizens/', {
                full_name: form.full_name,
                password: form.password,
                contacts: { email: form.email, phone: form.phone, preferred_contact: 'email' }
            });
            setResult({ success: true, data: res.data });
            // Auto-login after registration
            login(res.data);
        } catch (err) {
            setResult({ success: false, message: err.response?.data?.detail || 'Registration failed' });
        }
        setLoading(false);
    };

    if (result?.success) {
        return (
            <div className="card" style={{ maxWidth: '500px', margin: '0 auto' }}>
                <div className="text-center">
                    <div style={{ fontSize: '4rem' }}>✅</div>
                    <h2 className="mt-4">Registration Successful!</h2>
                    <p className="text-muted mt-2">Your Citizen ID:</p>
                    <code className="text-lg">{result.data._id}</code>
                    <p className="text-sm text-muted mt-4">Now verify your account to access all features</p>
                    <button className="btn btn-primary mt-4" onClick={() => navigate('/citizen/verify')}>Verify Account</button>
                </div>
            </div>
        );
    }

    return (
        <div className="card" style={{ maxWidth: '500px', margin: '0 auto' }}>
            <h2 className="mb-4">Create Citizen Account</h2>
            {result?.message && <div className="text-danger mb-4" style={{ padding: '0.5rem', background: '#fef2f2', borderRadius: '0.25rem' }}>{result.message}</div>}
            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label className="form-label">Full Name</label>
                    <input className="form-input" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} required />
                </div>
                <div className="form-group">
                    <label className="form-label">Email</label>
                    <input type="email" className="form-input" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required />
                </div>
                <div className="form-group">
                    <label className="form-label">Phone</label>
                    <input className="form-input" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} />
                </div>
                <div className="form-group">
                    <label className="form-label">Password</label>
                    <input type="password" className="form-input" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} required />
                </div>
                <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? 'Creating...' : 'Create Account'}</button>
                <p className="text-sm text-muted mt-4">Already have an account? <Link to="/citizen/login" style={{ color: 'var(--primary)' }}>Login here</Link></p>
            </form>
        </div>
    );
}

function LoginForm() {
    const [form, setForm] = useState({ email: '', password: '' });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const { login } = useContext(CitizenContext);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            const res = await client.post('/citizens/login', { email: form.email, password: form.password });
            login(res.data);
            navigate('/citizen');
        } catch (err) {
            setError(err.response?.data?.detail || 'Login failed');
        }
        setLoading(false);
    };

    return (
        <div className="card" style={{ maxWidth: '400px', margin: '0 auto' }}>
            <h2 className="mb-4">Citizen Login</h2>
            {error && <div className="text-danger mb-4" style={{ padding: '0.5rem', background: '#fef2f2', borderRadius: '0.25rem' }}>{error}</div>}
            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label className="form-label">Email</label>
                    <input type="email" className="form-input" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required />
                </div>
                <div className="form-group">
                    <label className="form-label">Password</label>
                    <input type="password" className="form-input" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} required />
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
                    {loading ? 'Logging in...' : 'Login'}
                </button>
                <p className="text-sm text-muted mt-4 text-center">Don't have an account? <Link to="/citizen/register" style={{ color: 'var(--primary)' }}>Register here</Link></p>
            </form>
        </div>
    );
}

function VerifyForm() {
    const { citizen, login } = useContext(CitizenContext);
    const [otp, setOtp] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    if (!citizen) {
        return <Navigate to="/citizen/login" />;
    }

    if (citizen.verification_state === 'verified') {
        return (
            <div className="card text-center" style={{ maxWidth: '400px', margin: '0 auto' }}>
                <div style={{ fontSize: '4rem' }}>✅</div>
                <h2 className="mt-4">Already Verified!</h2>
                <p className="text-muted">Your account is verified</p>
                <button className="btn btn-primary mt-4" onClick={() => navigate('/citizen')}>Go to Portal</button>
            </div>
        );
    }

    const handleVerify = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            await client.post(`/citizens/${citizen._id}/verify`, { otp_code: otp });
            // Update local state
            const updated = { ...citizen, verification_state: 'verified' };
            login(updated);
            navigate('/citizen');
        } catch (err) {
            setError(err.response?.data?.detail || 'Verification failed');
        }
        setLoading(false);
    };

    return (
        <div className="card" style={{ maxWidth: '400px', margin: '0 auto' }}>
            <h2 className="mb-4">Verify Your Account</h2>
            <p className="text-muted mb-4">Enter the 6-digit verification code sent to your email/phone</p>
            <div className="p-4 mb-4" style={{ background: '#dbeafe', borderRadius: '0.5rem' }}>
                <strong>Demo Mode:</strong> Enter any 6-digit code (e.g., 123456)
            </div>
            {error && <div className="text-danger mb-4" style={{ padding: '0.5rem', background: '#fef2f2', borderRadius: '0.25rem' }}>{error}</div>}
            <form onSubmit={handleVerify}>
                <div className="form-group">
                    <label className="form-label">Verification Code</label>
                    <input
                        className="form-input"
                        value={otp}
                        onChange={e => setOtp(e.target.value)}
                        placeholder="Enter 6-digit code"
                        maxLength={6}
                        style={{ fontSize: '1.5rem', textAlign: 'center', letterSpacing: '0.5rem' }}
                        required
                    />
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
                    {loading ? 'Verifying...' : 'Verify Account'}
                </button>
            </form>
        </div>
    );
}

function ReportIssue() {
    const { citizen } = useContext(CitizenContext);
    const [form, setForm] = useState({
        category: 'pothole',
        description: '',
        priority: 'medium',
        location: null
    });
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    const categories = [
        { value: 'pothole', label: 'Pothole / Road Damage' },
        { value: 'water_leak', label: 'Water Leak' },
        { value: 'trash', label: 'Missed Trash / Waste' },
        { value: 'lighting', label: 'Street Lighting' },
        { value: 'sewage', label: 'Sewage Issue' },
        { value: 'signage', label: 'Signs / Traffic' },
        { value: 'other', label: 'Other' }
    ];

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.location) {
            alert('Please select a location on the map');
            return;
        }
        setLoading(true);
        try {
            const payload = {
                citizen_id: citizen._id,
                anonymous: false,
                category: form.category,
                description: form.description,
                priority: form.priority,
                location: { type: 'Point', coordinates: form.location }
            };
            const res = await client.post('/requests/', payload);
            setResult({ success: true, data: res.data });
        } catch (err) {
            setResult({ success: false, message: err.response?.data?.detail || 'Submission failed' });
        }
        setLoading(false);
    };

    if (result?.success) {
        return (
            <div className="card" style={{ maxWidth: '600px', margin: '0 auto' }}>
                <div className="text-center">
                    <div style={{ fontSize: '4rem' }}>📨</div>
                    <h2 className="mt-4">Request Submitted!</h2>
                    <p className="text-muted mt-2">Your Request ID:</p>
                    <code className="text-2xl font-bold">{result.data.request_id}</code>
                    <div className="mt-4 p-4" style={{ background: 'var(--background)', borderRadius: 'var(--radius)' }}>
                        <div className="flex justify-between mb-2">
                            <span>Status:</span>
                            <span className="badge badge-new">New</span>
                        </div>
                        <div className="flex justify-between mb-2">
                            <span>Category:</span>
                            <span>{result.data.category}</span>
                        </div>
                        <div className="flex justify-between">
                            <span>Expected Resolution:</span>
                            <span>{result.data.sla_policy?.target_hours || 96} hours</span>
                        </div>
                    </div>
                    <button className="btn btn-primary mt-4" onClick={() => setResult(null)}>Submit Another</button>
                </div>
            </div>
        );
    }

    return (
        <div className="card" style={{ maxWidth: '800px', margin: '0 auto' }}>
            <h2 className="mb-4">Report a Service Issue</h2>
            {result?.message && <div className="text-danger mb-4" style={{ padding: '0.5rem', background: '#fef2f2', borderRadius: '0.25rem' }}>{result.message}</div>}
            <form onSubmit={handleSubmit}>
                <div className="grid grid-2 gap-4">
                    <div className="form-group">
                        <label className="form-label">Issue Category</label>
                        <select className="form-select" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
                            {categories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                        </select>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Priority</label>
                        <select className="form-select" value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}>
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                            <option value="critical">Critical</option>
                        </select>
                    </div>
                </div>

                <div className="form-group">
                    <label className="form-label">Description</label>
                    <textarea className="form-textarea" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Describe the issue in detail..." required />
                </div>

                <div className="form-group">
                    <label className="form-label">Location (Click on map)</label>
                    <MapPicker onLocationSelect={(loc) => setForm({ ...form, location: loc })} />
                    {form.location && (
                        <p className="text-sm text-muted mt-2">📍 {form.location[1].toFixed(4)}, {form.location[0].toFixed(4)}</p>
                    )}
                </div>

                <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? 'Submitting...' : 'Submit Request'}</button>
            </form>
        </div>
    );
}

function TrackRequest() {
    const [requestId, setRequestId] = useState('');
    const [request, setRequest] = useState(null);
    const [loading, setLoading] = useState(false);
    const [rating, setRating] = useState({ stars: 0, comment: '' });

    const handleSearch = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await client.get(`/requests/${requestId}`);
            setRequest(res.data);
        } catch {
            alert('Request not found');
        }
        setLoading(false);
    };

    const handleRate = async () => {
        try {
            await client.post(`/requests/${requestId}/rating`, { stars: rating.stars, comment: rating.comment });
            alert('Rating submitted!');
            handleSearch({ preventDefault: () => { } });
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to submit rating');
        }
    };

    return (
        <div style={{ maxWidth: '700px', margin: '0 auto' }}>
            <div className="card mb-4">
                <h2 className="mb-4">Track Your Request</h2>
                <form onSubmit={handleSearch} className="flex gap-2">
                    <input className="form-input" value={requestId} onChange={e => setRequestId(e.target.value)} placeholder="Enter Request ID (e.g., CST-2026-0001)" style={{ flex: 1 }} />
                    <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? 'Searching...' : 'Track'}</button>
                </form>
            </div>

            {request && (
                <div className="card">
                    <div className="flex justify-between items-center mb-4">
                        <h3>{request.request_id}</h3>
                        <span className={`badge badge-${request.status}`}>{request.status.replace('_', ' ')}</span>
                    </div>

                    <div className="grid grid-2 gap-4 mb-4">
                        <div><span className="text-muted">Category:</span> {request.category}</div>
                        <div><span className="text-muted">Priority:</span> <span className={`badge badge-${request.priority}`}>{request.priority}</span></div>
                    </div>

                    <p className="mb-4">{request.description}</p>

                    <h4 className="mb-2">Timeline</h4>
                    <div className="timeline mb-4">
                        {['created_at', 'triaged_at', 'assigned_at', 'resolved_at', 'closed_at'].map(key => (
                            <div key={key} className={`timeline-item ${request.timestamps?.[key] ? 'completed' : ''}`}>
                                <strong>{key.replace('_at', '').replace('_', ' ')}</strong>
                                <p className="text-sm text-muted">{request.timestamps?.[key] ? new Date(request.timestamps[key]).toLocaleString() : 'Pending'}</p>
                            </div>
                        ))}
                    </div>

                    {(request.status === 'resolved' || request.status === 'closed') && !request.rating && (
                        <div className="p-4" style={{ background: 'var(--background)', borderRadius: 'var(--radius)' }}>
                            <h4 className="mb-2">Rate This Service</h4>
                            <div className="stars mb-2">
                                {[1, 2, 3, 4, 5].map(n => (
                                    <span key={n} className={`star ${rating.stars >= n ? 'filled' : ''}`} onClick={() => setRating({ ...rating, stars: n })}>★</span>
                                ))}
                            </div>
                            <textarea className="form-textarea" value={rating.comment} onChange={e => setRating({ ...rating, comment: e.target.value })} placeholder="Leave a comment (optional)" />
                            <button className="btn btn-primary mt-2" onClick={handleRate} disabled={rating.stars === 0}>Submit Rating</button>
                        </div>
                    )}

                    {request.rating && (
                        <div className="p-4" style={{ background: '#dcfce7', borderRadius: 'var(--radius)' }}>
                            <strong>Your Rating:</strong> {'★'.repeat(request.rating.stars)}{'☆'.repeat(5 - request.rating.stars)}
                            {request.rating.comment && <p className="mt-2">{request.rating.comment}</p>}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function MyRequests() {
    const { citizen } = useContext(CitizenContext);
    const [requests, setRequests] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // In a real app, we'd filter by citizen_id on the backend
        client.get(`/requests/?limit=50`).then(res => {
            // Filter client-side for now
            const myReqs = res.data.filter(r => r.citizen_id === citizen._id);
            setRequests(myReqs);
            setLoading(false);
        });
    }, [citizen._id]);

    if (loading) return <div className="loading"><div className="spinner"></div> Loading...</div>;

    return (
        <div>
            <h2 className="mb-4">My Requests</h2>
            {requests.length === 0 ? (
                <div className="empty-state card">
                    <div className="empty-state-icon">📭</div>
                    <p>You haven't submitted any requests yet</p>
                    <Link to="/citizen/report" className="btn btn-primary mt-4">Report an Issue</Link>
                </div>
            ) : (
                <div className="flex flex-col gap-2">
                    {requests.map(req => (
                        <div key={req.request_id} className="request-item">
                            <div className="request-info">
                                <h4>{req.request_id} - {req.category}</h4>
                                <p>{req.description?.substring(0, 100)}...</p>
                            </div>
                            <div className="request-meta">
                                <span className={`badge badge-${req.status}`}>{req.status.replace('_', ' ')}</span>
                                <p className="text-xs text-muted mt-1">{new Date(req.timestamps?.created_at).toLocaleDateString()}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default CitizenPortal;
