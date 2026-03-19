# Food Safety Compliance API Documentation

## Overview

This document describes the Food Safety Compliance endpoints added to the Hunger Heroes backend. These endpoints enable tracking food safety, temperature monitoring, storage verification, and allergen information for all food donations.

---

## Features Implemented

### 1. **Food Safety Logging** 
- Record food safety inspections with temperature readings, storage method verification, and handling notes
- Tracks pass/fail inspection results
- Links inspections to volunteer/inspector IDs

### 2. **Safety Score Calculation**
- Computed 0-100 safety score based on:
  - Temperature compliance (±0.5 pts per °C deviation)
  - Storage method appropriateness (0-20 pt deduction)
  - Time since food preparation (0-50 pt deduction based on food type)
  - Allergen presence (1-5 pt deduction)
  - Failed inspections (20 pts per failed inspection)
- Automatically flags donations with score < 50 as `requires_review`

### 3. **Allergen Tracking**
- Track 6 major allergens: nuts, dairy, gluten, soy, shellfish, eggs
- Custom allergens support
- Dietary restrictions: vegetarian, vegan, halal, kosher

### 4. **Enhanced Donation Model**
- New required fields for food safety compliance:
  - `prepared_at` (ISO 8601, required)
  - `storage_method` (required)
- New nullable fields:
  - `safety_score` (0-100)
  - `requires_review` (boolean flag)

---

## API Endpoints

### 1. Create Safety Log
**Endpoint:** `POST /api/donations/{id}/safety-log`

**Description:** Record a food safety inspection for a donation.

**Request Body:**
```json
{
  "temperature_reading": 65.5,           // Temperature in Celsius (optional)
  "storage_method": "refrigerator",      // Must be from ALLOWED_STORAGE_METHODS
  "handling_notes": "Stored in sealed container",
  "passed_inspection": true,             // Pass/fail status (default: true)
  "notes": "Additional inspection notes"
}
```

**Allowed Storage Methods:**
- `cooler-with-ice`
- `insulated-bag`
- `refrigerator`
- `freezer`
- `room-temperature-shelf`
- `heated-container`
- `other`

**Response (Success):**
```json
{
  "message": "Safety log created successfully",
  "safety_log": {
    "id": 1,
    "donation_id": "HH-ABC123-DEFG",
    "temperature_reading": 65.5,
    "storage_method": "refrigerator",
    "handling_notes": "Stored in sealed container",
    "passed_inspection": true,
    "logged_at": "2026-03-18T10:30:00",
    "notes": "Additional inspection notes"
  },
  "updated_safety_score": 92,
  "requires_review": false
}
```

**Status Codes:**
- `201` - Safety log created successfully
- `400` - Invalid request data
- `404` - Donation not found
- `500` - Server error

---

### 2. Retrieve All Safety Logs
**Endpoint:** `GET /api/donations/{id}/safety-logs`

**Description:** Get all food safety inspection logs for a donation, ordered by most recent first.

**Query Parameters:** None

**Response (Success):**
```json
{
  "donation_id": "HH-ABC123-DEFG",
  "safety_logs": [
    {
      "id": 2,
      "donation_id": "HH-ABC123-DEFG",
      "temperature_reading": 62.0,
      "storage_method": "refrigerator",
      "handling_notes": "Checked condition - all good",
      "passed_inspection": true,
      "inspector_id": 5,
      "inspector_name": "John Volunteer",
      "logged_at": "2026-03-18T12:00:00",
      "notes": "Second inspection"
    },
    {
      "id": 1,
      "donation_id": "HH-ABC123-DEFG",
      "temperature_reading": 65.5,
      "storage_method": "refrigerator",
      "handling_notes": "Initial inspection",
      "passed_inspection": true,
      "inspector_id": 5,
      "inspector_name": "John Volunteer",
      "logged_at": "2026-03-18T10:30:00",
      "notes": null
    }
  ],
  "total": 2
}
```

**Status Codes:**
- `200` - Success
- `404` - Donation not found

---

### 3. Get Safety Status & Score
**Endpoint:** `GET /api/donations/{id}/safety-status`

**Description:** Get computed safety score with detailed breakdown of factors and warnings.

**Response (Success):**
```json
{
  "donation_id": "HH-ABC123-DEFG",
  "safety_score": 88,
  "requires_review": false,
  "factors": {
    "temperature": 3.0,      // Points deducted
    "storage": 0,            // Points deducted
    "time": 5.0,            // Points deducted
    "allergens": 4.0         // Points deducted
  },
  "warnings": [
    "Allergens present: dairy, nuts",
    "Food prepared 8.5 hours ago - freshness declining"
  ],
  "inspection_summary": {
    "total_inspections": 2,
    "passed_inspections": 2,
    "failed_inspections": 0,
    "last_inspection": "2026-03-18T12:00:00"
  },
  "food_details": {
    "food_type": "dairy",
    "prepared_at": "2026-03-18T02:00:00",
    "expiry_date": "2026-03-20",
    "temperature_at_pickup": 62.0,
    "storage_method": "refrigerator",
    "storage_type": "refrigerated"
  }
}
```

**Score Interpretation:**
- **90-100:** Excellent - No action needed
- **70-89:** Good - Minor concerns
- **50-69:** Fair - Increased monitoring recommended
- **Below 50:** Poor - Donation flagged for review

**Status Codes:**
- `200` - Success
- `404` - Donation not found

---

### 4. Create/Update Allergen Profile
**Endpoint:** `POST /api/donations/{id}/allergens`

**Description:** Create or update the allergen profile for a donation.

**Request Body:**
```json
{
  "contains_nuts": true,
  "contains_dairy": false,
  "contains_gluten": true,
  "contains_soy": false,
  "contains_shellfish": false,
  "contains_eggs": false,
  "other_allergens": ["sesame", "mustard"],
  "is_vegetarian": true,
  "is_vegan": false,
  "is_halal": true,
  "is_kosher": false
}
```

**Response (Success - Create):**
```json
{
  "message": "Allergen profile created successfully",
  "allergen_profile": {
    "id": 1,
    "donation_id": "HH-ABC123-DEFG",
    "allergens": {
      "contains_nuts": true,
      "contains_dairy": false,
      "contains_gluten": true,
      "contains_soy": false,
      "contains_shellfish": false,
      "contains_eggs": false,
      "other": ["sesame", "mustard"]
    },
    "dietary": {
      "is_vegetarian": true,
      "is_vegan": false,
      "is_halal": true,
      "is_kosher": false
    },
    "created_at": "2026-03-18T10:30:00",
    "updated_at": "2026-03-18T10:30:00"
  }
}
```

**Status Codes:**
- `201` - Allergen profile created
- `200` - Allergen profile updated
- `400` - Invalid request data
- `404` - Donation not found
- `500` - Server error

---

### 5. Get Allergen Profile
**Endpoint:** `GET /api/donations/{id}/allergens`

**Description:** Retrieve allergen information for a donation.

**Response (Success):**
```json
{
  "donation_id": "HH-ABC123-DEFG",
  "allergen_profile": {
    "id": 1,
    "donation_id": "HH-ABC123-DEFG",
    "allergens": {
      "contains_nuts": true,
      "contains_dairy": false,
      "contains_gluten": true,
      "contains_soy": false,
      "contains_shellfish": false,
      "contains_eggs": false,
      "other": ["sesame", "mustard"]
    },
    "dietary": {
      "is_vegetarian": true,
      "is_vegan": false,
      "is_halal": true,
      "is_kosher": false
    },
    "created_at": "2026-03-18T10:30:00",
    "updated_at": "2026-03-18T10:30:00"
  }
}
```

**Response (No Profile):**
```json
{
  "donation_id": "HH-ABC123-DEFG",
  "allergen_profile": null,
  "message": "No allergen profile found for this donation"
}
```

**Status Codes:**
- `200` - Success
- `404` - Donation not found or no allergen profile exists

---

## Updated Donation Creation

### Endpoint: `POST /api/donations`

Now requires two additional fields for food safety compliance:

**Request Body (Partial - New Required Fields):**
```json
{
  "food_name": "Pasta Carbonara",
  "category": "prepared-meals",
  "quantity": 10,
  "unit": "servings",
  "expiry_date": "2026-03-20",
  "storage": "refrigerated",
  "donor_name": "Jane Doe",
  "donor_email": "jane@example.com",
  "donor_zip": "92127",
  
  // NEW REQUIRED FIELDS FOR FOOD SAFETY:
  "prepared_at": "2026-03-18T10:00:00",           // ISO 8601, cannot be in future
  "storage_method": "refrigerator",               // From ALLOWED_STORAGE_METHODS
  
  // NEW OPTIONAL FIELD:
  "allergen_profile": {
    "contains_nuts": false,
    "contains_dairy": true,
    "contains_gluten": true,
    "contains_soy": false,
    "contains_shellfish": false,
    "contains_eggs": true,
    "other_allergens": [],
    "is_vegetarian": false,
    "is_vegan": false,
    "is_halal": false,
    "is_kosher": false
  },
  
  // ... other existing fields
}
```

**Response (Updated):**
```json
{
  "id": "HH-ABC123-DEFG",
  "message": "Donation created successfully",
  "status": "posted",
  "donation": { /* full donation object */ },
  "safety_score": 92,
  "requires_review": false,
  "safety_warnings": [
    "Allergens present: dairy, gluten, eggs"
  ]
}
```

---

## Safety Score Algorithm

### Score Calculation

**Base Score: 100 points**

#### 1. Temperature Compliance
- Calculates deviation from safe range per food type
- Deduction: 0.5 points per degree deviation
- **Maximum deduction: 25 points**

**Safe Temperature Ranges (Celsius):**
| Food Type | Min | Max | Note |
|-----------|-----|-----|------|
| Cooked | 15 | 74 | Room temp to hot |
| Raw vegetables | 5 | 15 | Cool storage |
| Dairy | 0 | 4 | Refrigerated |
| Meat/Protein | 0 | 4 | Refrigerated |
| Frozen items | -25 | -18 | Freezer |
| Packaged | 5 | 25 | Flexible |
| Baked goods | 15 | 25 | Room temp |
| Beverages | 0 | 10 | Cool storage |

#### 2. Storage Method Compliance
- Evaluates appropriateness of storage method
- **Point deductions:**
  - Cooler with ice: 0 pts ✓
  - Insulated bag: 0 pts ✓
  - Refrigerator: 0 pts ✓
  - Freezer: 0 pts ✓
  - Room temp shelf: 10 pts ⚠️
  - Heated container: 5 pts
  - Other: 15 pts ❌

#### 3. Time Since Preparation
- Progressive deduction based on food type and hours elapsed
- Different schedules for different food types

**Example Schedule - Cooked Foods:**
| Time Elapsed | Deduction |
|-------------|-----------|
| 0-2 hours | 0 pts |
| 2-4 hours | 5 pts |
| 4-8 hours | 15 pts |
| 8-24 hours | 30 pts |
| 24+ hours | 50 pts |

**Example Schedule - Frozen Prepared Foods:**
| Time Elapsed | Deduction |
|-------------|-----------|
| 0-24 hours | 0 pts |
| 24-72 hours | 0 pts |
| 3-7 days | 5 pts |
| 7+ days | 15 pts |

#### 4. Allergen Presence
- Minor deduction if allergens present
- 1 point per allergen type
- **Maximum deduction: 5 points**

#### 5. Failed Inspections
- Significant deduction for each failed inspection
- **Deduction: 20 points per failed inspection**

#### 6. Expiration Status
- Expired food: **50 points** (automatic maximum deduction)

### Score Thresholds

| Score | Status | Action |
|-------|--------|--------|
| 90-100 | ✓ Excellent | No action |
| 70-89 | ✓ Good | Monitor |
| 50-69 | ⚠️ Fair | Increased monitoring |
| < 50 | ❌ Poor | Flag for review |

---

## Code Examples

### Example 1: Create Donation with Safety Compliance

```bash
curl -X POST http://localhost:5000/api/donations \
  -H "Content-Type: application/json" \
  -d '{
    "food_name": "Homemade Lasagna",
    "category": "prepared-meals",
    "quantity": 12,
    "unit": "servings",
    "expiry_date": "2026-03-20",
    "storage": "refrigerated",
    "donor_name": "Maria Garcia",
    "donor_email": "maria@example.com",
    "donor_zip": "92127",
    "prepared_at": "2026-03-18T14:00:00",
    "storage_method": "refrigerator",
    "allergen_profile": {
      "contains_nuts": false,
      "contains_dairy": true,
      "contains_gluten": true,
      "contains_soy": false,
      "contains_shellfish": false,
      "contains_eggs": true,
      "other_allergens": [],
      "is_vegetarian": false,
      "is_vegan": false,
      "is_halal": false,
      "is_kosher": false
    }
  }'
```

### Example 2: Record Safety Inspection

```bash
curl -X POST http://localhost:5000/api/donations/HH-ABC123-DEFG/safety-log \
  -H "Content-Type: application/json" \
  -d '{
    "temperature_reading": 38.5,
    "storage_method": "refrigerator",
    "handling_notes": "Checked condition - food appears fresh and properly stored",
    "passed_inspection": true,
    "notes": "All safety checks passed"
  }'
```

### Example 3: Check Safety Score

```bash
curl http://localhost:5000/api/donations/HH-ABC123-DEFG/safety-status
```

### Example 4: Add Allergen Profile

```bash
curl -X POST http://localhost:5000/api/donations/HH-ABC123-DEFG/allergens \
  -H "Content-Type: application/json" \
  -d '{
    "contains_nuts": true,
    "contains_dairy": false,
    "contains_gluten": false,
    "contains_soy": false,
    "contains_shellfish": false,
    "contains_eggs": false,
    "other_allergens": ["peanuts", "tree nuts"],
    "is_vegetarian": true,
    "is_vegan": true,
    "is_halal": false,
    "is_kosher": false
  }'
```

---

## Database Schema Changes

### New/Modified Tables

#### donations (modifications)
```sql
ALTER TABLE donations ADD COLUMN prepared_at DATETIME;
ALTER TABLE donations ADD COLUMN requires_review BOOLEAN DEFAULT FALSE;
ALTER TABLE donations ADD COLUMN safety_score FLOAT DEFAULT 100;
```

#### food_safety_logs (already exists)
```sql
-- Already properly configured in model/food_safety_log.py
```

#### allergen_profiles (already exists)
```sql
-- Already properly configured in model/allergen_profile.py
```

---

## Validation Rules

### Food Safety Fields

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| `prepared_at` | DateTime | Yes | ISO 8601 format, cannot be future |
| `storage_method` | String | Yes | Must be from ALLOWED_STORAGE_METHODS |
| `temperature_reading` | Float | No | Must be numeric (°C) |
| `contains_nuts` | Boolean | No | True/False |
| ... (other allergen fields) | Boolean | No | True/False |

---

## Error Codes

| Code | Message | Cause |
|------|---------|-------|
| 400 | Missing required field | Food safety field missing |
| 400 | Invalid prepared_at format | Wrong datetime format |
| 400 | prepared_at cannot be in future | Preparation time in future |
| 400 | storage_method is required | Missing storage method |
| 400 | Invalid storage_method | Unsupported storage type |
| 404 | Donation not found | Non-existent donation ID |
| 404 | No allergen profile found | Allergen data not created |
| 500 | Failed to create donation | Database error |

---

## Testing Checklist

- [ ] Create donation with all safety fields
- [ ] Verify safety score is calculated on creation
- [ ] Create safety log for donation
- [ ] Verify safety score updates after log creation
- [ ] Create allergen profile
- [ ] Verify allergen data retrieval
- [ ] Test with failed inspection
- [ ] Verify requires_review flag triggers at < 50 score
- [ ] Test temperature deviation calculations
- [ ] Test expired food handling

---

## Future Enhancements

1. **ML-based risk prediction** - Use historical data to predict donations at risk
2. **Automated compliance reports** - Generate safety compliance reports
3. **Integration with local health department** - Share compliance data
4. **Mobile app integration** - QR code scanning for instant safety checks
5. **Donor reputation scores** - Track donor compliance history
6. **Batch temperature monitoring** - Real-time IoT temperature sensors

---

## Support & Contact

For questions or issues with these endpoints, please contact the backend development team.
