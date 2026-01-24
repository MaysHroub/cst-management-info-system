import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useParams, useNavigate } from 'react-router-dom';
import client from '../api/client';
import MapDisplay from '../components/MapDisplay';

function StaffDashboard() {
    return (
        <div>
            <div className="page-header">
                <div className="container">
                    <h1 className="page-title">Municipal Staff Console</h1>
                    <p className="text-muted">Manage, triage, and assign service requests</p>
                </div>
            </div>
            <div className="page-content container">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/requests" element={<RequestsManagement />} />
                    <Route path="/requests/:requestId" element={<RequestDetail />} />
                    <Route path="/agents" element={<AgentsManagement />} />
                    <Route path="/zones" element={<ZonesManagement />} />
                </Routes>
            </div>
        </div>
    );
}

function Dashboard() {
    const [kpis, setKpis] = useState(null);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        Promise.all([
            client.get('/analytics/kpis'),
            client.get('/analytics/stats')
        ]).then(([kpiRes, statsRes]) => {
            setKpis(kpiRes.data);
            setStats(statsRes.data);
            setLoading(false);
        });
    }, []);

    if (loading) return <div className="loading"><div className="spinner"></div> Loading dashboard...</div>;

    return (
        <div>
            <div className="flex gap-2 mb-4">
                <Link to="/staff/requests" className="btn btn-primary">Manage Requests</Link>
                <Link to="/staff/agents" className="btn btn-outline">Manage Agents</Link>
                <Link to="/staff/zones" className="btn btn-outline">Manage Zones</Link>
            </div>

            <div className="grid grid-4 gap-4 mb-6">
                <div className="stat-card">
                    <div className="stat-value">{kpis?.open_requests || 0}</div>
                    <div className="stat-label">Open Requests</div>
                </div>
                <div className="stat-card warning">
                    <div className="stat-value">{kpis?.at_risk_count || 0}</div>
                    <div className="stat-label">At SLA Risk</div>
                </div>
                <div className="stat-card danger">
                    <div className="stat-value">{kpis?.breached_count || 0}</div>
                    <div className="stat-label">SLA Breached</div>
                </div>
                <div className="stat-card success">
                    <div className="stat-value">{kpis?.avg_resolution_hours || 0}h</div>
                    <div className="stat-label">Avg Resolution</div>
                </div>
            </div>

            <div className="grid grid-2 gap-4">
                <div className="card">
                    <h3 className="card-title mb-4">Requests by Status</h3>
                    <div className="flex flex-col gap-2">
                        {Object.entries(stats?.by_status || {}).map(([status, count]) => (
                            <div key={status} className="flex justify-between items-center p-2" style={{ background: 'var(--background)', borderRadius: 'var(--radius)' }}>
                                <span className={`badge badge-${status}`}>{status.replace('_', ' ')}</span>
                                <strong>{count}</strong>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="card">
                    <h3 className="card-title mb-4">Requests by Category</h3>
                    <div className="flex flex-col gap-2">
                        {Object.entries(stats?.by_category || {}).map(([cat, count]) => (
                            <div key={cat} className="flex justify-between items-center p-2" style={{ background: 'var(--background)', borderRadius: 'var(--radius)' }}>
                                <span>{cat}</span>
                                <strong>{count}</strong>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

function RequestsManagement() {
    const [requests, setRequests] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({ status: '', category: '', priority: '' });
    const navigate = useNavigate();

    const fetchRequests = async () => {
        setLoading(true);
        const params = new URLSearchParams();
        if (filters.status) params.append('status', filters.status);
        if (filters.category) params.append('category', filters.category);
        if (filters.priority) params.append('priority', filters.priority);
        params.append('limit', '100');

        const res = await client.get(`/requests/?${params.toString()}`);
        setRequests(res.data);
        setLoading(false);
    };

    useEffect(() => { fetchRequests(); }, [filters]);

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h2>All Requests</h2>
                <button className="btn btn-outline" onClick={fetchRequests}>Refresh</button>
            </div>

            <div className="filters mb-4">
                <select className="filter-select" value={filters.status} onChange={e => setFilters({ ...filters, status: e.target.value })}>
                    <option value="">All Statuses</option>
                    <option value="new">New</option>
                    <option value="triaged">Triaged</option>
                    <option value="assigned">Assigned</option>
                    <option value="in_progress">In Progress</option>
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                </select>
                <select className="filter-select" value={filters.category} onChange={e => setFilters({ ...filters, category: e.target.value })}>
                    <option value="">All Categories</option>
                    <option value="pothole">Pothole</option>
                    <option value="water_leak">Water Leak</option>
                    <option value="trash">Trash</option>
                    <option value="lighting">Lighting</option>
                    <option value="sewage">Sewage</option>
                </select>
                <select className="filter-select" value={filters.priority} onChange={e => setFilters({ ...filters, priority: e.target.value })}>
                    <option value="">All Priorities</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                </select>
            </div>

            {loading ? (
                <div className="loading"><div className="spinner"></div> Loading...</div>
            ) : (
                <div className="table-container card p-0">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Category</th>
                                <th>Priority</th>
                                <th>Status</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {requests.map(req => (
                                <tr key={req.request_id}>
                                    <td><strong>{req.request_id}</strong></td>
                                    <td>{req.category}</td>
                                    <td><span className={`badge badge-${req.priority}`}>{req.priority}</span></td>
                                    <td><span className={`badge badge-${req.status}`}>{req.status.replace('_', ' ')}</span></td>
                                    <td className="text-sm">{new Date(req.timestamps?.created_at).toLocaleDateString()}</td>
                                    <td>
                                        <button className="btn btn-sm btn-outline" onClick={() => navigate(`/staff/requests/${req.request_id}`)}>View</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

function RequestDetail() {
    const { requestId } = useParams();
    const [request, setRequest] = useState(null);
    const [agents, setAgents] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    const fetchData = async () => {
        const [reqRes, agentRes] = await Promise.all([
            client.get(`/requests/${requestId}`),
            client.get('/agents/')
        ]);
        setRequest(reqRes.data);
        setAgents(agentRes.data);
        setLoading(false);
    };

    useEffect(() => { fetchData(); }, [requestId]);

    const handleTransition = async (newStatus) => {
        try {
            await client.patch(`/requests/${requestId}/transition`, { new_status: newStatus });
            fetchData();
        } catch (err) {
            alert(err.response?.data?.detail || 'Transition failed');
        }
    };

    const handleAssign = async (agentId) => {
        try {
            const params = agentId ? `?agent_id=${agentId}` : '';
            await client.post(`/agents/assign-request/${requestId}${params}`);
            fetchData();
        } catch (err) {
            alert(err.response?.data?.detail || 'Assignment failed');
        }
    };

    if (loading) return <div className="loading"><div className="spinner"></div> Loading...</div>;
    if (!request) return <div>Request not found</div>;

    const allowedNext = request.workflow?.allowed_next || [];

    return (
        <div>
            <button className="btn btn-ghost mb-4" onClick={() => navigate('/staff/requests')}>← Back to Requests</button>

            <div className="grid grid-3 gap-4">
                <div className="card" style={{ gridColumn: 'span 2' }}>
                    <div className="flex justify-between items-center mb-4">
                        <h2>{request.request_id}</h2>
                        <span className={`badge badge-${request.status}`} style={{ fontSize: '1rem', padding: '0.5rem 1rem' }}>{request.status.replace('_', ' ')}</span>
                    </div>

                    <div className="grid grid-2 gap-4 mb-4">
                        <div>
                            <span className="text-muted text-sm">Category</span>
                            <p className="font-medium">{request.category}</p>
                        </div>
                        <div>
                            <span className="text-muted text-sm">Priority</span>
                            <p><span className={`badge badge-${request.priority}`}>{request.priority}</span></p>
                        </div>
                        <div>
                            <span className="text-muted text-sm">Created</span>
                            <p>{new Date(request.timestamps?.created_at).toLocaleString()}</p>
                        </div>
                        <div>
                            <span className="text-muted text-sm">Citizen ID</span>
                            <p>{request.citizen_id || 'Anonymous'}</p>
                        </div>
                    </div>

                    <div className="mb-4">
                        <span className="text-muted text-sm">Description</span>
                        <p className="mt-1">{request.description}</p>
                    </div>

                    {request.location && (
                        <div className="map-container mb-4">
                            <MapDisplay coordinates={request.location.coordinates} />
                        </div>
                    )}

                    <h4 className="mb-2">Actions</h4>
                    <div className="flex gap-2 flex-wrap">
                        {allowedNext.map(status => (
                            <button key={status} className="btn btn-outline" onClick={() => handleTransition(status)}>
                                Move to {status.replace('_', ' ')}
                            </button>
                        ))}
                    </div>
                </div>

                <div>
                    <div className="card mb-4">
                        <h3 className="card-title mb-4">Assignment</h3>
                        {request.assigned_agent_id ? (
                            <div className="p-2" style={{ background: 'var(--background)', borderRadius: 'var(--radius)' }}>
                                <p className="text-sm text-muted">Assigned to:</p>
                                <p className="font-medium">{agents.find(a => a._id === request.assigned_agent_id)?.name || request.assigned_agent_id}</p>
                            </div>
                        ) : (
                            <p className="text-muted">Not assigned</p>
                        )}

                        <div className="mt-4">
                            <button className="btn btn-primary btn-sm mb-2 w-100" onClick={() => handleAssign(null)} style={{ width: '100%' }}>Auto-Assign</button>
                            <select className="form-select" onChange={e => e.target.value && handleAssign(e.target.value)}>
                                <option value="">Manual assign...</option>
                                {agents.map(a => <option key={a._id} value={a._id}>{a.name}</option>)}
                            </select>
                        </div>
                    </div>

                    <div className="card">
                        <h3 className="card-title mb-4">Timeline</h3>
                        <div className="timeline">
                            {(() => {
                                const STATUS_ORDER = {
                                    'new': 0, 'triaged': 1, 'assigned': 2, 'in_progress': 3, 'resolved': 4, 'closed': 5
                                };
                                const currentStep = STATUS_ORDER[request.status] || 0;

                                return ['created_at', 'triaged_at', 'assigned_at', 'work_started_at', 'resolved_at', 'closed_at'].map((key) => {
                                    // Custom label mapping
                                    const labels = {
                                        'created_at': 'New',
                                        'triaged_at': 'Triaged',
                                        'assigned_at': 'Assigned',
                                        'work_started_at': 'In Progress',
                                        'resolved_at': 'Resolved',
                                        'closed_at': 'Closed'
                                    };

                                    // Map timestamp key to status key for order check
                                    const statusKeyMap = {
                                        'created_at': 'new',
                                        'triaged_at': 'triaged',
                                        'assigned_at': 'assigned',
                                        'work_started_at': 'in_progress',
                                        'resolved_at': 'resolved',
                                        'closed_at': 'closed'
                                    };

                                    const statusKey = statusKeyMap[key];
                                    const stepIndex = STATUS_ORDER[statusKey];
                                    const isCompleted = stepIndex <= currentStep;

                                    // Special handling for work_started which is mapped from milestones
                                    let timestamp = request.timestamps?.[key];
                                    if (key === 'work_started_at' && !timestamp) {
                                        // Try to find in milestone
                                        const m = request.milestones?.find(m => m.type === 'work_started');
                                        if (m) timestamp = m.timestamp;
                                    }

                                    return (
                                        <div key={key} className={`timeline-item ${isCompleted ? 'completed' : ''}`}>
                                            <strong>{labels[key]}</strong>
                                            <p className="text-xs text-muted">
                                                {timestamp ? new Date(timestamp).toLocaleString() : (isCompleted ? '' : 'Pending')}
                                            </p>
                                        </div>
                                    );
                                });
                            })()}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function AgentsManagement() {
    const [agents, setAgents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState({
        agent_code: '',
        name: '',
        department: 'Public Works',
        skills: [],
        zone_ids: ['ZONE-DT-01'],
        geo_fence: null,
        days: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
        start_time: '08:00',
        end_time: '17:00',
        on_call: false
    });

    const fetchAgents = async () => {
        const res = await client.get('/agents/?active_only=false');
        setAgents(res.data);
        setLoading(false);
    };

    useEffect(() => { fetchAgents(); }, []);

    const handleCreate = async (e) => {
        e.preventDefault();

        // Construct shifts
        const shifts = form.days.map(day => ({
            day,
            start: form.start_time,
            end: form.end_time
        }));

        try {
            await client.post('/agents/', {
                agent_code: form.agent_code,
                name: form.name,
                department: form.department,
                skills: form.skills,
                coverage: {
                    zone_ids: form.zone_ids,
                    geo_fence: {
                        type: "Polygon",
                        coordinates: [[[35.19, 31.89], [35.22, 31.89], [35.22, 31.92], [35.19, 31.92], [35.19, 31.89]]]
                    }
                },
                schedule: {
                    shifts: shifts,
                    on_call: form.on_call
                }
            });
            setShowForm(false);
            fetchAgents();
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to create agent');
        }
    };

    const toggleDay = (day) => {
        if (form.days.includes(day)) {
            setForm({ ...form, days: form.days.filter(d => d !== day) });
        } else {
            setForm({ ...form, days: [...form.days, day] });
        }
    };

    if (loading) return <div className="loading"><div className="spinner"></div> Loading...</div>;

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h2>Service Agents</h2>
                <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Add Agent</button>
            </div>

            {showForm && (
                <div className="card mb-4">
                    <h3 className="mb-4">Create New Agent</h3>
                    <form onSubmit={handleCreate}>
                        <div className="grid grid-2 gap-4">
                            <div className="form-group">
                                <label className="form-label">Agent Code</label>
                                <input className="form-input" value={form.agent_code} onChange={e => setForm({ ...form, agent_code: e.target.value })} placeholder="AG-XX-01" required />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Name</label>
                                <input className="form-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Team Name" required />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Department</label>
                                <select className="form-select" value={form.department} onChange={e => setForm({ ...form, department: e.target.value })}>
                                    <option>Public Works</option>
                                    <option>Water & Sewage</option>
                                    <option>Waste Management</option>
                                    <option>Traffic & Roads</option>
                                </select>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Skills (comma-separated)</label>
                                <input className="form-input" onChange={e => setForm({ ...form, skills: e.target.value.split(',').map(s => s.trim()) })} placeholder="road, water, general" />
                            </div>
                        </div>

                        <div className="form-group mt-2">
                            <label className="form-label mb-2">Shift Schedule</label>
                            <div className="flex gap-2 flex-wrap mb-2">
                                {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
                                    <button
                                        type="button"
                                        key={day}
                                        className={`btn btn-sm ${form.days.includes(day) ? 'btn-primary' : 'btn-outline'}`}
                                        onClick={() => toggleDay(day)}
                                    >
                                        {day}
                                    </button>
                                ))}
                            </div>
                            <div className="flex gap-2 items-center">
                                <input type="time" className="form-input" style={{ width: 'auto' }} value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })} />
                                <span>to</span>
                                <input type="time" className="form-input" style={{ width: 'auto' }} value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })} />
                                <label className="flex items-center gap-2 ml-4">
                                    <input type="checkbox" checked={form.on_call} onChange={e => setForm({ ...form, on_call: e.target.checked })} />
                                    <span>On Call (24/7)</span>
                                </label>
                            </div>
                        </div>

                        <div className="flex gap-2 mt-4">
                            <button type="submit" className="btn btn-primary">Create Agent</button>
                            <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Cancel</button>
                        </div>
                    </form>
                </div>
            )}

            <div className="grid grid-3 gap-4">
                {agents.map(agent => (
                    <div key={agent._id} className="card">
                        <div className="flex justify-between items-start mb-2">
                            <h4>{agent.name}</h4>
                            <span className={`badge ${agent.active ? 'badge-resolved' : 'badge-closed'}`}>{agent.active ? 'Active' : 'Inactive'}</span>
                        </div>
                        <p className="text-sm text-muted mb-2">{agent.agent_code}</p>
                        <p className="text-sm mb-2">{agent.department}</p>
                        <div className="flex gap-1 flex-wrap mb-2">
                            {agent.skills?.map(s => <span key={s} className="badge" style={{ background: '#e0e7ff', color: '#4f46e5', fontSize: '0.7rem' }}>{s}</span>)}
                        </div>
                        <div className="text-sm mb-2">
                            <span className="text-muted">Shift:</span> {agent.schedule?.on_call ? 'On Call' : `${agent.schedule?.shifts?.[0]?.start} - ${agent.schedule?.shifts?.[0]?.end}`}
                        </div>
                        <div className="text-sm">
                            <span className="text-muted">Workload:</span> <strong>{agent.current_workload || 0}</strong> active
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function ZonesManagement() {
    const [zones, setZones] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState({
        zone_id: '',
        name: '',
        coordinates: '[[[35.19, 31.89], [35.22, 31.89], [35.22, 31.92], [35.19, 31.92], [35.19, 31.89]]]'
    });

    const fetchZones = async () => {
        const res = await client.get('/agents/zones');
        setZones(res.data);
        setLoading(false);
    };

    useEffect(() => { fetchZones(); }, []);

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            await client.post('/agents/zones', {
                zone_id: form.zone_id,
                name: form.name,
                boundary: {
                    type: "Polygon",
                    coordinates: JSON.parse(form.coordinates)
                }
            });
            setShowForm(false);
            fetchZones();
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to create zone');
        }
    };

    if (loading) return <div className="loading"><div className="spinner"></div> Loading zones...</div>;

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h2>Municipal Zones</h2>
                <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Define New Zone</button>
            </div>

            {showForm && (
                <div className="card mb-4">
                    <h3 className="mb-4">Create Service Zone</h3>
                    <form onSubmit={handleCreate}>
                        <div className="grid grid-2 gap-4">
                            <div className="form-group">
                                <label className="form-label">Zone Unique ID</label>
                                <input className="form-input" value={form.zone_id} onChange={e => setForm({ ...form, zone_id: e.target.value })} placeholder="ZONE-XX-01" required />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Zone Name</label>
                                <input className="form-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Downtown Core" required />
                            </div>
                        </div>
                        <div className="form-group mt-4">
                            <label className="form-label">Boundary Coordinates (GeoJSON Polygon [[[lng, lat], ...]])</label>
                            <textarea className="form-input" style={{ height: '100px', fontFamily: 'monospace' }} value={form.coordinates} onChange={e => setForm({ ...form, coordinates: e.target.value })} required />
                            <p className="text-xs text-muted mt-1">Provide a closed array of coordinates for the zone boundary.</p>
                        </div>
                        <div className="flex gap-2 mt-4">
                            <button type="submit" className="btn btn-primary">Define Zone</button>
                            <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Cancel</button>
                        </div>
                    </form>
                </div>
            )}

            <div className="grid grid-3 gap-4">
                {zones.map(zone => (
                    <div key={zone.zone_id} className="card">
                        <div className="flex justify-between items-start mb-2">
                            <h4>{zone.name}</h4>
                            <span className="badge badge-outline">{zone.zone_id}</span>
                        </div>
                        <div className="map-preview mb-4" style={{ height: '150px', borderRadius: '4px', overflow: 'hidden' }}>
                            <MapDisplay coordinates={zone.boundary.coordinates[0][0].reverse()} />
                        </div>
                        <button className="btn btn-sm btn-ghost text-danger" onClick={() => client.delete(`/agents/zones/${zone.zone_id}`).then(fetchZones)}>Delete Zone</button>
                    </div>
                ))}
                {zones.length === 0 && <p className="text-center p-8 text-muted" style={{ gridColumn: 'span 3' }}>No zones defined yet.</p>}
            </div>
        </div>
    );
}

export default StaffDashboard;
