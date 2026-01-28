# Advanced Triage Logic Implementation

## ✅ Implementation Complete

### Features Implemented:

#### 1. **Category Validation**
- Validates all incoming requests against a whitelist of valid categories
- Valid categories: `pothole`, `water_leak`, `trash`, `lighting`, `sewage`, `signage`, `other`
- Returns HTTP 400 error if invalid category is provided

#### 2. **High-Impact Location Detection**
- Detects if a request is within 500 meters of sensitive locations:
  - **Hospitals**: Hadassah Hospital, Shaare Zedek Medical Center
  - **Schools**: Hebrew University, Jerusalem College, Bezalel Academy
- Uses Haversine formula for accurate distance calculation
- Stores nearby sensitive locations in request metadata

#### 3. **Automatic Priority Escalation**
- **Low/Medium → High**: When near any sensitive location (school/hospital)
- **High → Critical**: When specifically near a hospital
- Records escalation reason and original priority in metadata
- Updates SLA policy based on new priority

#### 4. **SLA Policy Computation**
- Automatically assigns SLA based on final priority:
  - **Critical**: 24h target, 36h breach
  - **High**: 48h target, 72h breach
  - **Medium**: 96h target, 120h breach
  - **Low**: 168h target, 240h breach

---

## Backend Changes

### File: `/backend/app/routers/requests.py`

**Added Constants:**
```python
VALID_CATEGORIES = ["pothole", "water_leak", "trash", "lighting", "sewage", "signage", "other"]
SENSITIVE_LOCATIONS = [
    {"coordinates": [35.2137, 31.7683], "name": "Hadassah Hospital", "type": "hospital"},
    # ... more locations
]
```

**New Functions:**
1. `calculate_distance(lon1, lat1, lon2, lat2)` - Haversine distance calculation
2. `check_high_impact_location(coordinates)` - Find nearby sensitive locations
3. `compute_triage(request_data)` - Main triage logic with validation & escalation

**Modified Endpoints:**
- `POST /requests/` - Now applies automatic triage on request creation
  - Validates category
  - Checks location proximity
  - Escalates priority if needed
  - Stores triage metadata

**New Endpoint:**
- `POST /requests/{request_id}/triage` - Manual re-triage by staff
  - Re-runs triage logic
  - Allows staff to override priority
  - Updates request with new triage data

**Metadata Stored:**
```json
{
  "triage_metadata": {
    "original_priority": "medium",
    "priority_escalated": true,
    "escalation_reason": "Near hospital: Hadassah Hospital",
    "high_impact_flag": true,
    "nearby_sensitive_locations": [
      {"name": "Hadassah Hospital", "type": "hospital", "distance_km": 0.15}
    ],
    "triaged_at": "2026-01-24T...",
    "manual_triage": false
  }
}
```

---

## Frontend Changes

### File: `/frontend/src/pages/CitizenPortal.jsx`

**ReportIssue Component:**
- Shows priority escalation alert when request is auto-triaged
- Displays warning badge with escalation reason
- Shows high-impact flag if near sensitive location
- Updated success screen to show:
  - Final priority (after escalation)
  - Escalation notification with reason
  - High-impact indicator

**Visual Indicators:**
- Yellow warning box for escalated priorities
- ⚠️ emoji for visual attention
- Explanation of why priority was changed

### File: `/frontend/src/pages/StaffDashboard.jsx`

**RequestDetail Component:**
- Displays triage metadata in yellow info box
- Shows:
  - Original priority → Final priority
  - Escalation reason
  - High-impact location flag
  - Nearby sensitive locations
- Only shown when priority was escalated

---

## Test Results

✓ **Category Validation**: Invalid categories rejected
✓ **Distance Calculation**: Haversine formula working correctly
✓ **Priority Escalation**: 
  - Low/Medium → High when near school ✓
  - High → Critical when near hospital ✓
✓ **No False Positives**: Requests far from sensitive locations not escalated
✓ **SLA Policy**: Correctly computed based on final priority
✓ **Syntax**: All Python and JSX code passes validation

---

## Usage Examples

### Example 1: Normal Request
```json
{
  "category": "pothole",
  "priority": "low",
  "location": {"coordinates": [35.0, 31.5]}
}
```
**Result**: No escalation, SLA = 168h

### Example 2: Request Near Hospital
```json
{
  "category": "water_leak",
  "priority": "medium",
  "location": {"coordinates": [35.2137, 31.7683]}
}
```
**Result**: Escalated to **critical**, SLA = 24h, Reason: "Near hospital: Hadassah Hospital"

### Example 3: Request Near School
```json
{
  "category": "lighting",
  "priority": "low",
  "location": {"coordinates": [35.2433, 31.7890]}
}
```
**Result**: Escalated to **high**, SLA = 48h, Reason: "Near school: Hebrew University"

### Example 4: Invalid Category
```json
{
  "category": "invalid_thing",
  "priority": "high"
}
```
**Result**: HTTP 400 Error - "Invalid category 'invalid_thing'. Must be one of: pothole, water_leak, trash, lighting, sewage, signage, other"

---

## API Endpoints

### Automatic Triage (on creation)
```
POST /requests/
Body: ServiceRequestCreate
→ Automatically applies triage logic
→ Returns request with triage_metadata
```

### Manual Re-Triage
```
POST /requests/{request_id}/triage
Body: { "override_priority": "critical" } (optional)
→ Re-runs triage with current location
→ Staff can override auto-computed priority
→ Returns updated request with new triage data
```

---

## Configuration

### Proximity Threshold
- Currently set to **0.5 km (500 meters)**
- Can be adjusted in `check_high_impact_location()` function

### Sensitive Locations
- Currently includes 5 hardcoded locations (2 hospitals, 3 schools)
- Can be expanded by adding to `SENSITIVE_LOCATIONS` array
- Format: `{"coordinates": [lon, lat], "name": "...", "type": "hospital|school"}`

### Escalation Rules
- Low/Medium + Near sensitive location → High
- High + Near hospital → Critical
- Can be customized in `compute_triage()` function

---

## Benefits

1. **Safety**: Critical infrastructure issues get immediate attention
2. **Efficiency**: Automatic classification reduces manual triage work
3. **Transparency**: Citizens see why their priority was changed
4. **Flexibility**: Staff can override auto-triage if needed
5. **Auditability**: All escalations are logged with reasons

---

## Next Steps (Optional Enhancements)

1. Load sensitive locations from database instead of hardcoded
2. Add more location types (parks, government buildings, etc.)
3. Implement machine learning for category auto-correction
4. Add time-based escalation (e.g., night time lighting issues)
5. Create admin UI to manage sensitive locations
6. Add analytics dashboard for triage patterns
