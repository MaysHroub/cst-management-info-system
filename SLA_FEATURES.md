# SLA Monitoring & Resolution Features

## ✅ Implemented Features

### 7. SLA Monitoring
Continuous monitoring of elapsed time and flagging requests at risk of SLA breach.

#### Backend Implementation (requests.py):
- **GET `/requests/sla/at-risk`**: Returns at-risk and breached requests
  - Response includes counts and lists of requests in each category
  - Categorizes based on priority-specific thresholds

- **GET `/requests/{id}/sla-status`**: Individual request SLA status
  - Returns: `sla_state` (on_time/at_risk/breached)
  - Provides: age_hours, target_hours, breach_hours, time_remaining_to_breach
  - For resolved requests: shows actual resolution_hours

#### SLA Policies:
- **Critical**: 24h target, 36h breach threshold
- **High**: 48h target, 72h breach threshold  
- **Medium**: 96h target, 120h breach threshold
- **Low**: 168h target, 192h breach threshold

#### Frontend Implementation:
1. **Dashboard View** (`/staff`):
   - KPI cards showing at-risk count and breached count
   - "SLA Monitor" button for detailed view

2. **SLA Monitoring Dashboard** (`/staff/sla`):
   - Dedicated view for SLA tracking
   - Two tables: Breached (red) and At Risk (yellow)
   - Shows: ID, category, priority, status, age, target, time remaining
   - Quick "View" buttons to jump to request detail

3. **Request Detail View** (`/staff/requests/:id`):
   - SLA Status card with colored badge:
     - ✓ Green = On Time
     - ⏰ Yellow = At Risk
     - ⚠️ Red = Breached
   - Shows time breakdown and remaining time to breach
   - Updates automatically when viewing any request

---

### 8. Resolution with Evidence
Marking requests as resolved and uploading evidence of completed work.

#### Backend Implementation (requests.py):
- **POST `/requests/{id}/resolve`**: Resolve request with evidence
  - Parameters:
    - `resolution_notes` (required): Description of work completed
    - `evidence_urls` (optional): Array of URLs to photos/documents
    - `resolved_by` (required): Staff member who resolved it
  - Actions:
    - Updates status to "resolved"
    - Sets resolved_at timestamp
    - Creates milestone for resolution
    - Logs to performance_logs collection
    - Validates workflow transitions

#### Frontend Implementation:
1. **Request Detail View** (`/staff/requests/:id`):
   - "✓ Mark as Resolved" button (shown when status is assigned/in_progress)
   - Resolution form with:
     - Text area for resolution notes (required)
     - Input field for comma-separated evidence URLs
     - Submit/Cancel buttons
   - Form posts to resolve endpoint
   - Shows success message and refreshes data after submission

---

## Usage Flow

### For Staff Monitoring SLA:
1. Go to Staff Dashboard (`/staff`)
2. See at-risk/breached counts in KPI cards
3. Click "SLA Monitor" button
4. View tables sorted by urgency (breached first)
5. Click "View" on any request to see details
6. Request detail page shows real-time SLA status

### For Staff Resolving Requests:
1. Navigate to request detail (`/staff/requests/:id`)
2. See SLA status card with current state
3. Click "✓ Mark as Resolved" button
4. Fill in resolution notes describing work completed
5. (Optional) Add evidence URLs (photos, documents)
6. Submit - request transitions to resolved status
7. Resolution appears in timeline with timestamp

---

## Data Flow

```
[MongoDB Collections]
    ↓
[FastAPI Backend Routes]
    ↓ /requests/sla/at-risk
    ↓ /requests/{id}/sla-status  
    ↓ /requests/{id}/resolve
    ↓
[React Frontend Components]
    ↓ StaffDashboard (shows KPIs)
    ↓ SLAMonitoring (dedicated view)
    ↓ RequestDetail (status card + resolve form)
```

---

## Testing Checklist

- [x] Backend endpoints respond correctly
- [x] SLA calculations accurate for all priorities
- [x] At-risk/breached categorization working
- [x] Frontend displays SLA data in dashboard
- [x] SLA Monitor page shows correct tables
- [x] Request detail shows SLA status card
- [x] Resolve button appears for eligible requests
- [x] Resolve form accepts notes and evidence
- [x] Resolution updates database and creates milestone
- [x] No syntax errors in code

---

## Next Steps for Production

1. **Authentication**: Add user authentication to track `resolved_by` automatically
2. **File Upload**: Implement actual file upload endpoint (currently using URLs)
3. **Notifications**: Email/SMS alerts when requests approach breach threshold
4. **Reports**: Export SLA reports as PDF/CSV
5. **History**: Track SLA compliance trends over time
