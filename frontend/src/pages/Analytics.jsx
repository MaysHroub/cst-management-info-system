import React, { useState, useEffect } from 'react';
import client from '../api/client';
import HeatMap from '../components/HeatMap';

function Analytics() {
    const [kpis, setKpis] = useState(null);
    const [agentStats, setAgentStats] = useState([]);
    const [cohorts, setCohorts] = useState([]);
    const [zones, setZones] = useState([]);
    const [agents, setAgents] = useState([]);
    const [zoneGeoJson, setZoneGeoJson] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');
    const [filters, setFilters] = useState({
        start_date: '',
        end_date: '',
        zone: '',
        category: '',
        priority: '',
        agent_id: ''
    });

    const fetchData = async () => {
        setLoading(true);
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([k, v]) => {
            if (v) {
                if (k.includes('date')) {
                    params.append(k, new Date(v).toISOString());
                } else {
                    params.append(k, v);
                }
            }
        });

        try {
            const [kpiRes, agentRes, cohortRes, zoneRes, zoneGeoRes, agentsListRes] = await Promise.all([
                client.get(`/analytics/kpis?${params.toString()}`),
                client.get('/analytics/agents'),
                client.get('/analytics/cohorts'),
                client.get('/agents/zones'),
                client.get('/analytics/zones/geojson'),
                client.get('/agents')
            ]);
            setKpis(kpiRes.data);
            setAgentStats(agentRes.data);
            setCohorts(cohortRes.data);
            setZones(zoneRes.data);
            setZoneGeoJson(zoneGeoRes.data);
            setAgents(agentsListRes.data);
        } catch (err) {
            console.error("Fetch error", err);
        }
        setLoading(false);
    };

    useEffect(() => { fetchData(); }, [filters]);

    const handleExport = async () => {
        const res = await client.get('/analytics/export/csv', { responseType: 'blob' });
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `cst_report_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
    };

    const simulateBreach = async () => {
        if (confirm("This will artificially age requests to simulate SLA breaches for dashboard verification. Proceed?")) {
            await client.get('/analytics/simulate-breach');
            fetchData();
        }
    };

    if (loading && !kpis) return <div className="loading"><div className="spinner"></div> Loading analytics...</div>;

    return (
        <div>
            <div className="page-header">
                <div className="container">
                    <div className="flex justify-between items-center">
                        <div>
                            <h1 className="page-title">Analytics Dashboard</h1>
                            <p className="text-muted">Real-time governance and performance insights</p>
                        </div>
                        <div className="flex gap-2">
                            <button className="btn btn-outline" onClick={simulateBreach}>Simulate SLA Breach</button>
                            <button className="btn btn-primary" onClick={handleExport}>Download CSV Report</button>
                        </div>
                    </div>
                </div>
            </div>
            <div className="page-content container">
                <div className="tabs">
                    <button className={`tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>Performance KPIs</button>
                    <button className={`tab ${activeTab === 'map' ? 'active' : ''}`} onClick={() => setActiveTab('map')}>Live Geo Feed</button>
                    <button className={`tab ${activeTab === 'agents' ? 'active' : ''}`} onClick={() => setActiveTab('agents')}>Agent Productivity</button>
                    <button className={`tab ${activeTab === 'cohorts' ? 'active' : ''}`} onClick={() => setActiveTab('cohorts')}>Repeat Hotspots</button>
                </div>

                {activeTab === 'overview' && (
                    <OverviewTab
                        kpis={kpis}
                        filters={filters}
                        setFilters={setFilters}
                        zones={zones}
                        agents={agents}
                    />
                )}
                {activeTab === 'map' && <MapTab geojson={kpis?.heatmap} zoneGeoJson={zoneGeoJson} />}
                {activeTab === 'agents' && <AgentsTab stats={agentStats} />}
                {activeTab === 'cohorts' && <CohortsTab cohorts={cohorts} />}
            </div>
        </div>
    );
}

function OverviewTab({ kpis, filters, setFilters, zones, agents }) {
    return (
        <div>
            <div className="filters card mb-6 p-4">
                <h4 className="mb-2">Advanced Analytics Filters</h4>
                <div className="grid grid-3 gap-4">
                    <div className="form-group">
                        <label className="text-xs text-muted">Date Range</label>
                        <div className="flex gap-2">
                            <input type="date" className="form-input" value={filters.start_date} onChange={e => setFilters({ ...filters, start_date: e.target.value })} placeholder="Start" />
                            <input type="date" className="form-input" value={filters.end_date} onChange={e => setFilters({ ...filters, end_date: e.target.value })} placeholder="End" />
                        </div>
                    </div>
                    <div className="form-group">
                        <label className="text-xs text-muted">Zone</label>
                        <select className="form-select" value={filters.zone} onChange={e => setFilters({ ...filters, zone: e.target.value })}>
                            <option value="">All Zones</option>
                            {zones.map(z => <option key={z.zone_id} value={z.zone_id}>{z.name}</option>)}
                        </select>
                    </div>
                    <div className="form-group">
                        <label className="text-xs text-muted">Category</label>
                        <select className="form-select" value={filters.category} onChange={e => setFilters({ ...filters, category: e.target.value })}>
                            <option value="">All Categories</option>
                            <option value="pothole">Pothole</option>
                            <option value="water_leak">Water Leak</option>
                            <option value="trash">Trash</option>
                            <option value="lighting">Lighting</option>
                            <option value="sewage">Sewage</option>
                        </select>
                    </div>
                    <div className="form-group">
                        <label className="text-xs text-muted">Priority</label>
                        <select className="form-select" value={filters.priority} onChange={e => setFilters({ ...filters, priority: e.target.value })}>
                            <option value="">All Priorities</option>
                            <option value="critical">Critical</option>
                            <option value="high">High</option>
                            <option value="medium">Medium</option>
                            <option value="low">Low</option>
                        </select>
                    </div>
                    <div className="form-group">
                        <label className="text-xs text-muted">Assigned Agent</label>
                        <select className="form-select" value={filters.agent_id} onChange={e => setFilters({ ...filters, agent_id: e.target.value })}>
                            <option value="">All Agents</option>
                            {agents.map(a => <option key={a._id} value={a._id}>{a.name}</option>)}
                        </select>
                    </div>
                    <div className="flex items-end">
                        <button className="btn btn-outline" style={{ width: '100%' }} onClick={() => setFilters({ start_date: '', end_date: '', zone: '', category: '', priority: '', agent_id: '' })}>Clear All Filters</button>
                    </div>
                </div>
            </div>

            <div className="grid grid-5 gap-4 mb-6">
                <div className="stat-card">
                    <div className="stat-value">{kpis?.total_requests || 0}</div>
                    <div className="stat-label">Total Volume</div>
                </div>
                <div className="stat-card warning">
                    <div className="stat-value">{kpis?.sla_breach_percentage || 0}%</div>
                    <div className="stat-label">SLA Breach Rate</div>
                </div>
                <div className="stat-card danger">
                    <div className="stat-value text-danger">{kpis?.critical_breach_count || 0}</div>
                    <div className="stat-label">Critical Breaches</div>
                </div>
                <div className="stat-card warning">
                    <div className="stat-value text-warning">{kpis?.at_risk_count || 0}</div>
                    <div className="stat-label">At Risk</div>
                </div>
                <div className="stat-card success">
                    <div className="stat-value">{kpis?.avg_rating || 0}★</div>
                    <div className="stat-label">Citizen Satisfaction</div>
                </div>
            </div>

            <div className="grid grid-2 gap-4">
                <div className="card">
                    <h3 className="card-title mb-4">Rating Distribution</h3>
                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', height: '150px' }}>
                        {['1', '2', '3', '4', '5'].map(star => {
                            const count = kpis?.rating_distribution?.[star] || 0;
                            const total = Object.values(kpis?.rating_distribution || {}).reduce((a, b) => a + b, 0) || 1;
                            const height = (count / total) * 120;
                            const color = parseInt(star) >= 4 ? 'var(--success)' : parseInt(star) <= 2 ? 'var(--danger)' : 'var(--warning)';
                            return (
                                <div key={star} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                    <span className="text-xs mb-1">{count}</span>
                                    <div style={{
                                        width: '100%',
                                        height: `${height}px`,
                                        background: color,
                                        borderRadius: '4px 4px 0 0',
                                        opacity: 0.8
                                    }}></div>
                                    <span className="text-xs mt-1">{star}★</span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="card">
                    <h3 className="card-title mb-4">Backlog by Zone</h3>
                    <div className="flex flex-col gap-2">
                        {Object.entries(kpis?.by_zone || {}).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([zone, count]) => (
                            <div key={zone} className="flex justify-between items-center p-2 rounded" style={{ background: 'var(--background)' }}>
                                <span className="text-sm font-medium">{zone}</span>
                                <span className="badge badge-outline">{count}</span>
                            </div>
                        ))}
                        {Object.keys(kpis?.by_zone || {}).length === 0 && <p className="text-muted text-center py-4">No zone data available</p>}
                    </div>
                </div>
            </div>
        </div>
    );
}

function MapTab({ zoneGeoJson }) {
    const [heatmapData, setHeatmapData] = useState(null);
    const [mapFilters, setMapFilters] = useState({ category: '', priority: '', status: 'all' });

    useEffect(() => {
        const params = new URLSearchParams();
        if (mapFilters.category) params.append('category', mapFilters.category);
        if (mapFilters.priority) params.append('priority', mapFilters.priority);
        
        // Always include the include_closed parameter
        params.append('include_closed', mapFilters.status === 'all' ? 'true' : 'false');
        
        // Add cache busting
        params.append('_t', Date.now().toString());

        console.log('Fetching heatmap with params:', params.toString());
        client.get(`/analytics/heatmap?${params.toString()}`).then(res => {
            console.log('Heatmap response features count:', res.data?.features?.length || 0);
            setHeatmapData(res.data);
        }).catch(err => {
            console.error('Heatmap fetch error:', err);
        });
    }, [mapFilters]);

    return (
        <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
            <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)' }} className="flex justify-between items-center">
                <div>
                    <h3 className="card-title">Live Geo Intelligence</h3>
                    <p className="text-sm text-muted">Point Clustering + Zone Choropleth (Intensity by request density)</p>
                </div>
                <div className="flex gap-2">
                    <select className="filter-select" value={mapFilters.status} onChange={e => setMapFilters({ ...mapFilters, status: e.target.value })}>
                        <option value="open">Open Requests Only</option>
                        <option value="all">All Requests (incl. Closed)</option>
                    </select>
                    <select className="filter-select" value={mapFilters.priority} onChange={e => setMapFilters({ ...mapFilters, priority: e.target.value })}>
                        <option value="">All Priorities</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>
            </div>
            <div style={{ height: '550px' }}>
                <HeatMap geojson={heatmapData} zoneJson={zoneGeoJson} />
            </div>
            <div className="p-4 bg-light flex gap-4 text-xs">
                <div className="flex items-center gap-1"><span style={{ width: '12px', height: '12px', background: '#991b1b', borderRadius: '2px', opacity: 0.6 }}></span> High Density Zone (10+ requests)</div>
                <div className="flex items-center gap-1"><span style={{ width: '12px', height: '12px', background: '#f97316', borderRadius: '2px', opacity: 0.6 }}></span> Medium Density Zone (5-10 requests)</div>
                <div className="flex items-center gap-1"><span style={{ width: '12px', height: '12px', background: '#fbbf24', borderRadius: '2px', opacity: 0.6 }}></span> Low Density Zone (1-5 requests)</div>
                <div className="flex items-center gap-1"><span style={{ width: '12px', height: '12px', background: '#dc2626', border: '2px solid #fff', borderRadius: '50%' }}></span> Critical Priority Request</div>
                <div className="flex items-center gap-1"><span style={{ width: '12px', height: '12px', background: '#ea580c', border: '2px solid #fff', borderRadius: '50%' }}></span> High Priority Request</div>
            </div>
        </div>
    );
}

function AgentsTab({ stats }) {
    return (
        <div className="table-container card p-0">
            <table>
                <thead>
                    <tr>
                        <th>Service Agent</th>
                        <th>Active Load</th>
                        <th>LTD Completed</th>
                        <th>Avg Resolution</th>
                        <th>Productivity Score</th>
                    </tr>
                </thead>
                <tbody>
                    {stats.map(agent => (
                        <tr key={agent.agent_id}>
                            <td>
                                <div className="flex flex-col">
                                    <strong>{agent.agent_name}</strong>
                                    <span className="text-xs text-muted">ID: {agent.agent_id.slice(-6)}</span>
                                </div>
                            </td>
                            <td><span className="badge badge-assigned">{agent.active_tasks} items</span></td>
                            <td><span className="badge badge-resolved">{agent.completed_tasks} resolved</span></td>
                            <td>{agent.avg_resolution_hours > 0 ? `${agent.avg_resolution_hours} hrs` : '--'}</td>
                            <td>
                                <div className="flex items-center gap-2">
                                    <div style={{ flex: 1, height: '6px', background: 'var(--border)', borderRadius: '3px' }}>
                                        <div style={{ width: `${Math.min((agent.score || 0) * 20, 100)}%`, height: '100%', background: 'var(--primary)', borderRadius: '3px' }}></div>
                                    </div>
                                    <span className="text-xs">{agent.score || 0}</span>
                                </div>
                            </td>
                        </tr>
                    ))}
                    {stats.length === 0 && <tr><td colSpan="5" className="text-center p-4 text-muted">No agent activity recorded yet.</td></tr>}
                </tbody>
            </table>
        </div>
    );
}

function CohortsTab({ cohorts }) {
    return (
        <div className="grid grid-2 gap-4">
            <div className="card">
                <h3 className="card-title mb-4">Recurring Issue Hotspots</h3>
                <p className="text-sm text-muted mb-4">Neighborhoods and intersections with multiple reported incidents.</p>
                <div className="flex flex-col gap-3">
                    {cohorts.map((cohort, i) => (
                        <div key={i} className="p-3 border rounded hover-bg" style={{ position: 'relative' }}>
                            <div className="flex justify-between items-start">
                                <div>
                                    <strong className="block text-primary">{cohort._id || 'General Location'}</strong>
                                    <div className="flex gap-1 mt-1">
                                        {cohort.categories.map(c => <span key={c} className="badge text-xs" style={{ fontSize: '0.6rem' }}>{c}</span>)}
                                    </div>
                                </div>
                                <span className="badge badge-danger" style={{ fontSize: '1rem', fontWeight: 'bold' }}>{cohort.count} reports</span>
                            </div>
                            <div className="mt-2 text-xs text-muted flex justify-between">
                                <span>Average Rating: {cohort.avg_rating?.toFixed(1) || 'N/A'}★</span>
                                <span>Latest Incident: {new Date(cohort.last_incident).toLocaleDateString()}</span>
                            </div>
                        </div>
                    ))}
                    {cohorts.length === 0 && <p className="text-center p-4 text-muted">No recurring hotspots identified.</p>}
                </div>
            </div>
            <div className="card">
                <div className="alert alert-info mb-4" style={{ background: 'var(--info-bg)', padding: '1rem' }}>
                    <h4 className="text-sm mb-2">Service Quality Insights</h4>
                    <p className="text-xs">These metrics help our municipal teams track how effectively issues are being addressed and where attention is most needed.</p>
                </div>
                <div className="mt-2">
                    <h4 className="text-sm mb-3">Governance Policy Tracking:</h4>
                    <div className="grid grid-2 gap-2">
                        <div className="p-2 border rounded">
                            <span className="text-xs text-muted block uppercase">BREACH CALCULATION</span>
                            <span className="text-xs">Based on specific category timelines.</span>
                        </div>
                        <div className="p-2 border rounded">
                            <span className="text-xs text-muted block uppercase">HOTSPOT DETECTION</span>
                            <span className="text-xs">Identifies repeated issues at the same address.</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Analytics;
