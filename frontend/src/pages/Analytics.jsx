import React, { useState, useEffect } from 'react';
import client from '../api/client';
import HeatMap from '../components/HeatMap';

function Analytics() {
    const [kpis, setKpis] = useState(null);
    const [agentStats, setAgentStats] = useState([]);
    const [cohorts, setCohorts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');
    const [filters, setFilters] = useState({
        start_date: '',
        end_date: '',
        zone: ''
    });

    const fetchData = async () => {
        setLoading(true);
        const params = new URLSearchParams();
        if (filters.start_date) params.append('start_date', new Date(filters.start_date).toISOString());
        if (filters.end_date) params.append('end_date', new Date(filters.end_date).toISOString());
        if (filters.zone) params.append('zone', filters.zone);

        const [kpiRes, agentRes, cohortRes] = await Promise.all([
            client.get(`/analytics/kpis?${params.toString()}`),
            client.get('/analytics/agents'),
            client.get('/analytics/cohorts')
        ]);
        setKpis(kpiRes.data);
        setAgentStats(agentRes.data);
        setCohorts(cohortRes.data);
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
                        <button className="btn btn-primary" onClick={handleExport}>Download CSV Report</button>
                    </div>
                </div>
            </div>
            <div className="page-content container">
                <div className="filters card mb-6 p-4">
                    <h4 className="mb-2">Advanced Filters</h4>
                    <div className="flex gap-4 items-center">
                        <div className="form-group flex-1">
                            <label className="text-xs text-muted">Start Date</label>
                            <input type="date" className="form-input" value={filters.start_date} onChange={e => setFilters({ ...filters, start_date: e.target.value })} />
                        </div>
                        <div className="form-group flex-1">
                            <label className="text-xs text-muted">End Date</label>
                            <input type="date" className="form-input" value={filters.end_date} onChange={e => setFilters({ ...filters, end_date: e.target.value })} />
                        </div>
                        <div className="form-group flex-1">
                            <label className="text-xs text-muted">Zone</label>
                            <select className="form-select" value={filters.zone} onChange={e => setFilters({ ...filters, zone: e.target.value })}>
                                <option value="">All Zones</option>
                                <option value="ZONE-DT-01">Downtown (DT-01)</option>
                                <option value="ZONE-NT-02">North (NT-02)</option>
                                <option value="ZONE-ST-03">South (ST-03)</option>
                            </select>
                        </div>
                        <button className="btn btn-outline mt-4" onClick={() => setFilters({ start_date: '', end_date: '', zone: '' })}>Clear</button>
                    </div>
                </div>

                <div className="tabs">
                    <button className={`tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>Performance KPIs</button>
                    <button className={`tab ${activeTab === 'map' ? 'active' : ''}`} onClick={() => setActiveTab('map')}>Live Heat Map</button>
                    <button className={`tab ${activeTab === 'agents' ? 'active' : ''}`} onClick={() => setActiveTab('agents')}>Agent Productivity</button>
                    <button className={`tab ${activeTab === 'cohorts' ? 'active' : ''}`} onClick={() => setActiveTab('cohorts')}>Repeat Hotspots</button>
                </div>

                {activeTab === 'overview' && <OverviewTab kpis={kpis} />}
                {activeTab === 'map' && <MapTab />}
                {activeTab === 'agents' && <AgentsTab stats={agentStats} />}
                {activeTab === 'cohorts' && <CohortsTab cohorts={cohorts} />}
            </div>
        </div>
    );
}

function OverviewTab({ kpis }) {
    return (
        <div>
            <div className="grid grid-4 gap-4 mb-6">
                <div className="stat-card">
                    <div className="stat-value">{kpis?.total_requests || 0}</div>
                    <div className="stat-label">Total Volume</div>
                </div>
                <div className="stat-card warning">
                    <div className="stat-value">{kpis?.sla_breach_percentage || 0}%</div>
                    <div className="stat-label">SLA Breach Rate</div>
                </div>
                <div className="stat-card danger">
                    <div className="stat-value">{kpis?.breached_count || 0}</div>
                    <div className="stat-label">Critical Breaches</div>
                </div>
                <div className="stat-card success">
                    <div className="stat-value">{kpis?.avg_rating || 0}★</div>
                    <div className="stat-label">User Satisfaction</div>
                </div>
            </div>

            <div className="grid grid-2 gap-4">
                <div className="card">
                    <h3 className="card-title mb-4">Rating Distribution</h3>
                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', height: '150px' }}>
                        {[1, 2, 3, 4, 5].map(star => {
                            const count = kpis?.rating_distribution?.[star] || 0;
                            const total = Object.values(kpis?.rating_distribution || {}).reduce((a, b) => a + b, 0) || 1;
                            const height = (count / total) * 120;
                            return (
                                <div key={star} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                    <span className="text-xs mb-1">{count}</span>
                                    <div style={{
                                        width: '100%',
                                        height: `${height}px`,
                                        background: star >= 4 ? 'var(--success)' : star <= 2 ? 'var(--danger)' : 'var(--warning)',
                                        borderRadius: '4px 4px 0 0'
                                    }}></div>
                                    <span className="text-xs mt-1">{star}★</span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="card">
                    <h3 className="card-title mb-4">Backlog by Category</h3>
                    <div className="flex flex-col gap-2">
                        {Object.entries(kpis?.by_category || {}).sort((a, b) => b[1] - a[1]).map(([cat, count]) => (
                            <div key={cat} className="flex justify-between items-center p-2 rounded" style={{ background: 'var(--background)' }}>
                                <span className="text-sm">{cat}</span>
                                <span className="badge badge-outline">{count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

function MapTab() {
    const [heatmapData, setHeatmapData] = useState(null);
    const [mapFilters, setMapFilters] = useState({ category: '', priority: '' });

    useEffect(() => {
        const params = new URLSearchParams();
        if (mapFilters.category) params.append('category', mapFilters.category);
        if (mapFilters.priority) params.append('priority', mapFilters.priority);

        client.get(`/analytics/heatmap?${params.toString()}`).then(res => {
            setHeatmapData(res.data);
        });
    }, [mapFilters]);

    return (
        <div className="card">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h3 className="card-title">Live Request Heat Map</h3>
                    <p className="text-sm text-muted">Weighted density based on priority and request age</p>
                </div>
                <div className="flex gap-2">
                    <select className="filter-select" value={mapFilters.category} onChange={e => setMapFilters({ ...mapFilters, category: e.target.value })}>
                        <option value="">All Categories</option>
                        <option value="pothole">Pothole</option>
                        <option value="water_leak">Water Leak</option>
                        <option value="trash">Trash</option>
                    </select>
                </div>
            </div>
            <div style={{ height: '500px', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
                <HeatMap geojson={heatmapData} />
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
                        <th>Agent</th>
                        <th>Active Workload</th>
                        <th>Completed (All Time)</th>
                        <th>Avg Resolution</th>
                        <th>Productivity Score</th>
                    </tr>
                </thead>
                <tbody>
                    {stats.map(agent => {
                        const score = agent.completed_tasks > 0 ? (agent.completed_tasks / (agent.active_tasks + 1)).toFixed(1) : 0;
                        return (
                            <tr key={agent._id}>
                                <td><strong>{agent.agent_name}</strong></td>
                                <td><span className="badge badge-assigned">{agent.active_tasks} tasks</span></td>
                                <td><span className="badge badge-resolved">{agent.completed_tasks} resolved</span></td>
                                <td>{agent.avg_resolution_hours?.toFixed(1) || '--'} hrs</td>
                                <td>
                                    <div className="flex items-center gap-2">
                                        <div style={{ flex: 1, height: '6px', background: 'var(--border)', borderRadius: '3px' }}>
                                            <div style={{ width: `${Math.min(score * 20, 100)}%`, height: '100%', background: 'var(--primary)', borderRadius: '3px' }}></div>
                                        </div>
                                        <span className="text-xs">{score}</span>
                                    </div>
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}

function CohortsTab({ cohorts }) {
    return (
        <div className="grid grid-2 gap-4">
            <div className="card">
                <h3 className="card-title mb-4">Repeat-Issue Hotspots</h3>
                <p className="text-sm text-muted mb-4">Locations with 2+ reported incidents</p>
                <div className="flex flex-col gap-3">
                    {cohorts.map((cohort, i) => (
                        <div key={i} className="p-3 border rounded">
                            <div className="flex justify-between items-start">
                                <div>
                                    <strong className="block">{cohort._id || 'Point Analysis'}</strong>
                                    <div className="flex gap-1 mt-1">
                                        {cohort.categories.map(c => <span key={c} className="badge text-xs" style={{ fontSize: '0.6rem' }}>{c}</span>)}
                                    </div>
                                </div>
                                <span className="badge badge-danger" style={{ fontSize: '1rem' }}>{cohort.count} incidents</span>
                            </div>
                            <div className="mt-2 text-xs text-muted">
                                Last Incident: {new Date(cohort.last_incident).toLocaleDateString()}
                            </div>
                        </div>
                    ))}
                    {cohorts.length === 0 && <p className="text-center p-4 text-muted">No recurring hotspots identified.</p>}
                </div>
            </div>
            <div className="card">
                <h3 className="card-title mb-4">Governance Notice</h3>
                <div className="alert alert-info" style={{ background: 'var(--info-bg)', padding: '1rem', borderRadius: 'var(--radius)' }}>
                    <p className="text-sm">These analytics use $lookup, $facet, and $group operators to compute high-integrity governance metrics. Data is generated real-time from the municipal database.</p>
                </div>
                <div className="mt-4">
                    <h4 className="text-sm mb-2">Metrics derived:</h4>
                    <ul className="text-sm text-muted">
                        <li>SLA Breach Derived: created_at vs today</li>
                        <li>Recurrence Metric: incident_count by location</li>
                        <li>Productivity: completion_ratio vs avg_resolution</li>
                    </ul>
                </div>
            </div>
        </div>
    );
}

export default Analytics;
