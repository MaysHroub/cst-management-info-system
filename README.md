# Citizen Services Tracker (CST)

Advanced Municipal Service Tracking System with Real-time Geo-feeds.

## Team Contribution

This project was developed collaboratively by **Bailasan Qa’dan** and **Mays Hroub**.  
While the system was designed, reviewed, and integrated jointly, the primary module responsibilities were divided to organize development work as follows:

- **Bailasan Qa’dan**
  - Module 1: Service Request Management
  - Module 3: Service Agents & Assignment

- **Mays Hroub**
  - Module 2: Citizen Portal & Profiles
  - Module 4: Data Analysis & Visualization

Despite this division, **both team members actively collaborated across all modules**, contributing to system design, API integration, debugging, testing, and overall architectural decisions. All components were reviewed together to ensure consistency, correctness, and alignment with the project requirements.

## Overview

CST is a comprehensive platform for municipalities to receive, triage, assign, and resolve citizen-reported service failures. It features:

- **Workflow-driven lifecycle** (new → triaged → assigned → in_progress → resolved → closed)
- **Geo-enabled location tracking** with interactive maps
- **SLA monitoring** with automated escalation
- **Agent assignment** based on coverage zones and workload
- **Real-time analytics** and heatmap visualization
- **Citizen feedback** and rating system

## Tech Stack

- **Backend**: FastAPI (Python) + MongoDB (PyMongo)
- **Frontend**: React (Vite) + Leaflet Maps
- **Database**: MongoDB with GeoJSON support

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app entry
│   │   ├── database.py       # MongoDB connection
│   │   ├── models/
│   │   │   └── schemas.py    # Pydantic models
│   │   ├── routers/
│   │   │   ├── requests.py   # Service Requests API
│   │   │   ├── citizens.py   # Citizens API
│   │   │   ├── agents.py     # Agents API
│   │   │   └── analytics.py  # Analytics API
│   │   └── utils/
│   │       └── common.py     # Helpers
│   ├── requirements.txt
│   └── test_workflow.py      # E2E test script
│
└── frontend/
    ├── src/
    │   ├── App.jsx           # Main app with routing
    │   ├── App.css           # Global styles
    │   ├── api/
    │   │   └── client.js     # Axios setup
    │   ├── components/
    │   │   ├── MapPicker.jsx # Location selector
    │   │   ├── MapDisplay.jsx# Single location view
    │   │   └── HeatMap.jsx   # Multi-point heatmap
    │   └── pages/
    │       ├── CitizenPortal.jsx
    │       ├── StaffDashboard.jsx
    │       ├── AgentInterface.jsx
    │       └── Analytics.jsx
    └── package.json
```

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- MongoDB running on localhost:27017

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
./venv/bin/uvicorn app.main:app --reload --port 8000
```

The API will be available at http://localhost:8000

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at http://localhost:5173

## API Endpoints

### Service Requests

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/requests/` | Create new request |
| GET | `/requests/` | List all requests |
| GET | `/requests/{id}` | Get request details |
| PATCH | `/requests/{id}/transition` | Change status |
| POST | `/requests/{id}/comment` | Add comment |
| POST | `/requests/{id}/rating` | Rate service |
| PATCH | `/requests/{id}/milestone` | Add milestone |

### Citizens

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/citizens/` | Create citizen |
| GET | `/citizens/` | List citizens |
| GET | `/citizens/{id}` | Get profile |
| POST | `/citizens/{id}/verify` | Verify account |

### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agents/` | Create agent |
| GET | `/agents/` | List agents |
| GET | `/agents/{id}` | Get agent details |
| GET | `/agents/{id}/tasks` | Get assigned tasks |
| POST | `/agents/assign-request/{id}` | Auto-assign request |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/stats` | General statistics |
| GET | `/analytics/kpis` | Key performance indicators |
| GET | `/analytics/heatmap` | GeoJSON for map |
| GET | `/analytics/agents` | Agent productivity |
| GET | `/analytics/timeline` | Requests over time |
| GET | `/analytics/zones` | Zone aggregates |

## User Interfaces

### 1. Citizen Portal (`/citizen`)
- Report new issues with map location
- Track request by ID
- View status timeline
- Rate completed services

### 2. Staff Console (`/staff`)
- Dashboard with KPIs
- Request management table
- Triage and assign requests
- Manage agents

### 3. Agent Interface (`/agent`)
- View assigned tasks
- Update milestones (arrived, work_started, resolved)
- Track progress

### 4. Analytics (`/analytics`)
- Overview with charts
- Live heatmap of open requests
- Agent performance metrics
- Zone analysis

## Workflow (Annex B)

1. **Citizen reports issue** → Status: `new`
2. **Staff triages** → Status: `triaged`
3. **Auto-assign to agent** → Status: `assigned`
4. **Agent works on issue** → Status: `in_progress`
5. **Agent completes work** → Status: `resolved`
6. **Citizen rates service** → Status: `closed`

## Testing

Run the full workflow test:

```bash
cd backend
./venv/bin/python3 test_workflow.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| MONGO_URL | mongodb://localhost:27017 | MongoDB connection |
| DB_NAME | cst_db | Database name |

## License

MIT License - COMP4382 Final Project 2025/2026
