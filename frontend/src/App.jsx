import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import CitizenPortal from './pages/CitizenPortal';
import StaffDashboard from './pages/StaffDashboard';
import AgentInterface from './pages/AgentInterface';
import Analytics from './pages/Analytics';
import './App.css';

function Navbar() {
  const location = useLocation();
  const isActive = (path) => location.pathname.startsWith(path);

  return (
    <nav className="navbar">
      <div className="container navbar-content">
        <Link to="/" className="logo">🛡️ CST</Link>
        <div className="nav-links">
          <Link to="/citizen" className={`nav-link ${isActive('/citizen') ? 'active' : ''}`}>Citizen Portal</Link>
          <Link to="/staff" className={`nav-link ${isActive('/staff') ? 'active' : ''}`}>Staff Console</Link>
          <Link to="/agent" className={`nav-link ${isActive('/agent') ? 'active' : ''}`}>Agent Tasks</Link>
          <Link to="/analytics" className={`nav-link ${isActive('/analytics') ? 'active' : ''}`}>Analytics</Link>
        </div>
      </div>
    </nav>
  );
}

function Home() {
  return (
    <div className="home-page">
      <div className="hero">
        <h1>Citizen Services Tracker</h1>
        <p>Advanced Municipal Service Tracking System with Real-time Geo-feeds</p>
        <div className="hero-actions">
          <Link to="/citizen" className="btn btn-primary btn-lg">Report an Issue</Link>
          <Link to="/staff" className="btn btn-outline btn-lg">Staff Login</Link>
        </div>
      </div>

      <div className="features container">
        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-icon">📍</div>
            <h3>Geo-Enabled Reporting</h3>
            <p>Report issues with precise location on interactive maps</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3>Real-time Tracking</h3>
            <p>Track your requests from submission to resolution</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Analytics Dashboard</h3>
            <p>View live heatmaps and performance metrics</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⏱️</div>
            <h3>SLA Monitoring</h3>
            <p>Automated escalation and breach prevention</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="app">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/citizen/*" element={<CitizenPortal />} />
            <Route path="/staff/*" element={<StaffDashboard />} />
            <Route path="/agent/*" element={<AgentInterface />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
