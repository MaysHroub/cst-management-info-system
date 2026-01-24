import React, { useState, useEffect } from 'react';
import client from '../api/client';
import MapDisplay from '../components/MapDisplay';

function AgentInterface() {
    const [agents, setAgents] = useState([]);
    const [selectedAgent, setSelectedAgent] = useState(null);
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        client.get('/agents/').then(res => {
            setAgents(res.data);
            if (res.data.length > 0) {
                setSelectedAgent(res.data[0]);
            }
            setLoading(false);
        });
    }, []);

    useEffect(() => {
        if (selectedAgent) {
            client.get(`/agents/${selectedAgent._id}/tasks`).then(res => {
                setTasks(res.data);
            });
        }
    }, [selectedAgent]);

    const handleMilestone = async (requestId, milestoneType) => {
        try {
            await client.patch(`/requests/${requestId}/milestone`, {
                milestone_type: milestoneType,
                notes: `Marked by agent at ${new Date().toLocaleString()}`
            });
            // Refresh tasks
            const res = await client.get(`/agents/${selectedAgent._id}/tasks`);
            setTasks(res.data);
            alert(`Milestone "${milestoneType}" recorded!`);
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to update milestone');
        }
    };

    if (loading) return <div className="loading"><div className="spinner"></div> Loading...</div>;

    return (
        <div>
            <div className="page-header">
                <div className="container">
                    <h1 className="page-title">Agent Interface</h1>
                    <p className="text-muted">View and execute assigned tasks</p>
                </div>
            </div>
            <div className="page-content container">
                <div className="mb-4">
                    <label className="form-label">Select Agent</label>
                    <select className="form-select" style={{ maxWidth: '300px' }} value={selectedAgent?._id || ''} onChange={e => setSelectedAgent(agents.find(a => a._id === e.target.value))}>
                        {agents.map(a => <option key={a._id} value={a._id}>{a.name} ({a.agent_code})</option>)}
                    </select>
                </div>

                {selectedAgent && (
                    <div className="grid grid-3 gap-4 mb-6">
                        <div className="stat-card">
                            <div className="stat-value">{tasks.length}</div>
                            <div className="stat-label">Active Tasks</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{selectedAgent.skills?.length || 0}</div>
                            <div className="stat-label">Skills</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{selectedAgent.coverage?.zone_ids?.length || 0}</div>
                            <div className="stat-label">Coverage Zones</div>
                        </div>
                    </div>
                )}

                <h2 className="mb-4">My Tasks</h2>

                {tasks.length === 0 ? (
                    <div className="empty-state card">
                        <div className="empty-state-icon">✅</div>
                        <p>No active tasks assigned</p>
                    </div>
                ) : (
                    <div className="flex flex-col gap-4">
                        {tasks.map(task => (
                            <TaskCard key={task.request_id} task={task} onMilestone={handleMilestone} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

function TaskCard({ task, onMilestone }) {
    const [expanded, setExpanded] = useState(false);

    const milestones = task.milestones || [];
    const hasArrived = milestones.some(m => m.type === 'arrived');
    const hasStarted = milestones.some(m => m.type === 'work_started');
    const hasResolved = milestones.some(m => m.type === 'resolved');

    return (
        <div className="card">
            <div className="flex justify-between items-start">
                <div>
                    <h3 className="flex items-center gap-2">
                        {task.request_id}
                        <span className={`badge badge-${task.priority}`}>{task.priority}</span>
                        <span className={`badge badge-${task.status}`}>{task.status.replace('_', ' ')}</span>
                    </h3>
                    <p className="text-sm text-muted mt-1">{task.category}</p>
                </div>
                <button className="btn btn-ghost" onClick={() => setExpanded(!expanded)}>
                    {expanded ? '▲' : '▼'}
                </button>
            </div>

            {expanded && (
                <div className="mt-4">
                    <p className="mb-4">{task.description}</p>

                    {task.location && (
                        <div className="map-container mb-4" style={{ height: '200px' }}>
                            <MapDisplay coordinates={task.location.coordinates} />
                        </div>
                    )}

                    <h4 className="mb-2">Milestones</h4>
                    <div className="flex gap-2 flex-wrap mb-4">
                        <button
                            className={`btn ${hasArrived ? 'btn-success' : 'btn-outline'}`}
                            onClick={() => !hasArrived && onMilestone(task.request_id, 'arrived')}
                            disabled={hasArrived}
                        >
                            {hasArrived ? '✓ Arrived' : 'Mark Arrived'}
                        </button>
                        <button
                            className={`btn ${hasStarted ? 'btn-success' : 'btn-outline'}`}
                            onClick={() => !hasStarted && onMilestone(task.request_id, 'work_started')}
                            disabled={hasStarted || !hasArrived}
                        >
                            {hasStarted ? '✓ Work Started' : 'Start Work'}
                        </button>
                        <button
                            className={`btn ${hasResolved ? 'btn-success' : 'btn-primary'}`}
                            onClick={() => !hasResolved && onMilestone(task.request_id, 'resolved')}
                            disabled={hasResolved || !hasStarted}
                        >
                            {hasResolved ? '✓ Completed' : 'Mark Complete'}
                        </button>
                    </div>

                    {milestones.length > 0 && (
                        <div className="p-4" style={{ background: 'var(--background)', borderRadius: 'var(--radius)' }}>
                            <h5 className="text-sm font-medium mb-2">Progress Log</h5>
                            {milestones.map((m, i) => (
                                <div key={i} className="text-sm mb-1">
                                    <span className="text-success">✓</span> {m.type} - {new Date(m.timestamp).toLocaleString()}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default AgentInterface;
