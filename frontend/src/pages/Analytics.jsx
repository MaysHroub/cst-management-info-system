import React, { useState, useEffect } from 'react';
import client from '../api/client';
import HeatMap from '../components/HeatMap';

function Analytics() {
    const [kpis, setKpis] = useState(null);
    const [agentStats, setAgentStats] = useState([]);
    const [timeline, setTimeline] = useState([]);
    const [zoneStats, setZoneStats] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');

    useEffect(() => {
        Promise.all([
            client.get('/analytics/kpis'),
            client.get('/analytics/agents'),
            client.get('/analytics/timeline?days=14'),
            client.get('/analytics/zones')
        ]).then(([kpiRes, agentRes, timelineRes, zoneRes]) => {
            setKpis(kpiRes.data);
            setAgentStats(agentRes.data);
            setTimeline(timelineRes.data);
            setZoneStats(zoneRes.data);
            setLoading(false);
        });
    }, []);

    if (loading) return <div className="loading"><div className="spinner"></div> Loading analytics...</div>;

    return (
        <div>
            <div className="page-header">
                <div className="container">
                    <h1 className="page-title">Analytics Dashboard</h1>
                    <p className="text-muted">Real-time insights and performance metrics</p>
                </div>
            </div>
            <div className="page-content container">
                <div className="tabs">
                    <button className={`tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>Overview</button>
                    <button className={`tab ${activeTab === 'map' ? 'active' : ''}`} onClick={() => setActiveTab('map')}>Live Map</button>
                    <button className={`tab ${activeTab === 'agents' ? 'active' : ''}`} onClick={() => setActiveTab('agents')}>Agent Performance</button>
                    <button className={`tab ${activeTab === 'zones' ? 'active' : ''}`} onClick={() => setActiveTab('zones')}>Zone Analysis</button>
                </div>

                {activeTab === 'overview' && <OverviewTab kpis={kpis} timeline={timeline} />}
                {activeTab === 'map' && <MapTab />}
                {activeTab === 'agents' && <AgentsTab stats={agentStats} />}
                {activeTab === 'zones' && <ZonesTab stats={zoneStats} />}
            </div>
        </div>
    );
}

function OverviewTab({ kpis, timeline }) {
    return (
        <div>
            <div className="grid grid-4 gap-4 mb-6">
                <div className="stat-card">
                    <div className="stat-value">{kpis?.total_requests || 0}</div>
                    <div className="stat-label">Total Requests</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{kpis?.open_requests || 0}</div>
                    <div className="stat-label">Open Requests</div>
                </div>
                <div className="stat-card warning">
                    <div className="stat-value">{kpis?.sla_breach_percentage || 0}%</div>
                    <div className="stat-label">SLA Breach Rate</div>
                </div>
                <div className="stat-card success">
                    <div className="stat-value">{kpis?.avg_rating || 0}★</div>
                    <div className="stat-label">Avg Rating</div>
                </div>
            </div>

            <div className="grid grid-2 gap-4">
                <div className="card">
                    <h3 className="card-title mb-4">Requests Over Time (14 days)</h3>
                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: '200px' }}>
                        {timeline.map((d, i) => {
                            const maxCount = Math.max(...timeline.map(t => t.count), 1);
                            const height = (d.count / maxCount) * 180;
                            return (
                                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                    <div style={{
                                        width: '100%',
                                        height: `${height}px`,
                                        background: 'linear-gradient(to top, #2563eb, #60a5fa)',
                                        borderRadius: '4px 4px 0 0',
                                        minHeight: '4px'
                                    }} title={`${d.date}: ${d.count}`}></div>
                                    <span className="text-xs text-muted mt-1" style={{ fontSize: '0.6rem' }}>{d.date.slice(5)}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="card">
                    <h3 className="card-title mb-4">System Summary</h3>
                    <div className="flex flex-col gap-4">
                        <div className="flex justify-between">
                            <span className="text-muted">Total Agents</span>
                            <strong>{kpis?.total_agents || 0}</strong>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted">Total Citizens</span>
                            <strong>{kpis?.total_citizens || 0}</strong>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted">Avg Resolution Time</span>
                            <strong>{kpis?.avg_resolution_hours || 0} hours</strong>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted">At Risk</span>
                            <strong className="text-warning">{kpis?.at_risk_count || 0}</strong>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted">Breached</span>
                            <strong className="text-danger">{kpis?.breached_count || 0}</strong>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function MapTab() {
    const [heatmapData, setHeatmapData] = useState(null);
    const [filters, setFilters] = useState({ category: '', priority: '' });

    useEffect(() => {
        const params = new URLSearchParams();
        if (filters.category) params.append('category', filters.category);
        if (filters.priority) params.append('priority', filters.priority);

        client.get(`/analytics/heatmap?${params.toString()}`).then(res => {
            setHeatmapData(res.data);
        });
    }, [filters]);

    return (
        <div>
            <div className="filters mb-4">
                <select className="filter-select" value={filters.category} onChange={e => setFilters({ ...filters, category: e.target.value })}>
                    <option value="">All Categories</option>
                    <option value="pothole">Pothole</option>
                    <option value="water_leak">Water Leak</option>
                    <option value="trash">Trash</option>
                    <option value="lighting">Lighting</option>
                </select>
                <select className="filter-select" value={filters.priority} onChange={e => setFilters({ ...filters, priority: e.target.value })}>
                    <option value="">All Priorities</option>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                </select>
            </div>

            <div className="card">
                <h3 className="card-title mb-4">Live Request Heat Map</h3>
                <p className="text-sm text-muted mb-4">Showing {heatmapData?.features?.length || 0} open requests</p>
                <div style={{ height: '500px', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
                    <HeatMap geojson={heatmapData} />
                </div>
            </div>
        </div>
    );
}

function AgentsTab({ stats }) {
    return (
        <div>
            <h3 className="mb-4">Agent Productivity</h3>
            <div className="table-container card p-0">
                <table>
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Department</th>
                            <th>Skills</th>
                            <th>Active Tasks</th>
                            <th>Completed</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stats.map(agent => (
                            <tr key={agent.agent_id}>
                                <td><strong>{agent.agent_name}</strong></td>
                                <td>{agent.department}</td>
                                <td>
                                    <div className="flex gap-1 flex-wrap">
                                        {agent.skills?.map(s => (
                                            <span key={s} className="badge" style={{ background: '#e0e7ff', color: '#4f46e5', fontSize: '0.65rem' }}>{s}</span>
                                        ))}
                                    </div>
                                </td>
                                <td><span className="badge badge-assigned">{agent.active_tasks}</span></td>
                                <td><span className="badge badge-resolved">{agent.completed_tasks}</span></td>
                                <td><strong>{agent.total_tasks}</strong></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function ZonesTab({ stats }) {
    return (
        <div>
            <h3 className="mb-4">Zone Analysis</h3>
            <div className="grid grid-3 gap-4">
                {stats.map(zone => (
                    <div key={zone.zone_id} className="card">
                        <h4 className="mb-2">{zone.zone_id}</h4>
                        <div className="flex justify-between mb-2">
                            <span className="text-muted">Total</span>
                            <strong>{zone.total}</strong>
                        </div>
                        <div className="flex justify-between mb-2">
                            <span className="text-muted">Open</span>
                            <span className="badge badge-new">{zone.open}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted">Resolved</span>
                            <span className="badge badge-resolved">{zone.resolved}</span>
                        </div>
                        <div className="mt-2" style={{ height: '8px', background: 'var(--border)', borderRadius: '4px', overflow: 'hidden' }}>
                            <div style={{
                                width: `${zone.total > 0 ? (zone.resolved / zone.total) * 100 : 0}%`,
                                height: '100%',
                                background: 'var(--success)'
                            }}></div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default Analytics;
