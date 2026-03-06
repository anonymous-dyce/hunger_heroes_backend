# Donation API Endpoints

> **Blueprint prefix:** `/api`
> **File:** `api/donation.py`
> **Last updated:** 2026-03-04

---

## Endpoints Overview

| Method | Route | Auth | Description | Request Params |
|--------|-------|------|-------------|----------------|
| `POST` | `/api/donation` | Optional (JWT cookie) | Create a new donation | Body JSON (see below) |
| `GET` | `/api/donation` | **Required** | List current user's donations (paginated) | Query: `status`, `page`, `per_page` |
| `GET` | `/api/donation/stats` | Optional | Get aggregate donation statistics | — |
| `GET` | `/api/donation/<id>` | None | Get a single donation by ID (barcode scan) | Path: `donation_id` |
| `POST` | `/api/donation/<id>/accept` | Optional | Accept a donation | Body: `{ "accepted_by": "..." }` |
| `POST` | `/api/donation/<id>/deliver` | Optional | Mark a donation as delivered | Body: `{ "delivered_by": "..." }` |
| `POST` | `/api/donations/cleanup` | **Required** (Admin) | Archive donations older than N days | Body: `{ "days": 7 }` |

---

## Detailed Endpoint Reference

### 1. Create Donation

```
POST /api/donation
```

**Auth:** Optional — if a valid JWT cookie is present, `user_id` is auto-linked.

**Request Body (JSON):**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `food_name` | string | **Yes** | Name of the food item |
| `category` | string | **Yes** | Must be one of: `canned`, `fresh-produce`, `dairy`, `bakery`, `meat-protein`, `grains`, `beverages`, `frozen`, `snacks`, `baby-food`, `prepared-meals`, `other` |
| `quantity` | integer | **Yes** | Must be ≥ 1 |
| `unit` | string | **Yes** | Must be one of: `items`, `lbs`, `kg`, `oz`, `cans`, `boxes`, `bags`, `trays`, `servings` |
| `expiry_date` | string | **Yes** | `YYYY-MM-DD`, cannot be in the past |
| `storage` | string | **Yes** | Must be one of: `room-temp`, `refrigerated`, `frozen`, `cool-dry` |
| `donor_name` | string | **Yes** | |
| `donor_email` | string | **Yes** | |
| `donor_zip` | string | **Yes** | |
| `food_type` | string | No | `cooked`, `raw`, `packaged`, `perishable`, `non-perishable`, `baked`, `frozen-prepared`, `canned-goods`, `beverage`, `other` |
| `serving_count` | integer | No | Estimated servings, must be ≥ 1 |
| `weight_lbs` | float | No | Weight in pounds, must be > 0 |
| `description` | string | No | Free text |
| `allergens` | string[] | No | Array of: `gluten`, `dairy`, `nuts`, `soy`, `eggs`, `shellfish`, `fish`, `none` |
| `allergen_info` | string | No | Free-text allergen notes |
| `dietary_tags` | string[] | No | Array of: `vegetarian`, `vegan`, `halal`, `kosher`, `gluten-free`, `organic` |
| `temperature_at_pickup` | float | No | Temperature in °F at time of pickup |
| `storage_method` | string | No | `cooler-with-ice`, `insulated-bag`, `refrigerator`, `freezer`, `room-temperature-shelf`, `heated-container`, `other` |
| `donor_phone` | string | No | |
| `special_instructions` | string | No | |
| `pickup_location` | string | No | Full pickup address |
| `zip_code` | string | No | Pickup zip code (may differ from `donor_zip`) |
| `pickup_window_start` | string | No | ISO 8601 datetime, e.g. `2026-03-05T09:00:00` |
| `pickup_window_end` | string | No | ISO 8601 datetime, must be after `start` |
| `donor_id` | integer | No | FK → `users.id` |
| `receiver_id` | integer | No | FK → `users.id` |
| `volunteer_id` | integer | No | FK → `users.id` |

**Response `201`:**
```json
{
  "id": "HH-M3X7K9-AB2F",
  "message": "Donation created successfully",
  "donation": { ... }
}
```

**Error responses:** `400` (validation), `500` (server error)

---

### 2. List User's Donations

```
GET /api/donation
```

**Auth:** Required (JWT cookie)

**Query Parameters:**

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `status` | string | `all` | Filter by status: `active`, `accepted`, `delivered`, `expired`, `cancelled`, `archived` |
| `page` | integer | `1` | Page number |
| `per_page` | integer | `20` | Items per page |

**Response `200`:**
```json
{
  "donations": [ ... ],
  "total": 42,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

Each item uses `to_dict_short()` (14 fields — see Model Schema doc).

**Note:** Expired donations (past `expiry_date`) are automatically marked `expired` on each list request.

---

### 3. Get Donation by ID (Barcode Scan)

```
GET /api/donation/<donation_id>
```

**Auth:** None required

**Path Parameter:**

| Param | Type | Notes |
|-------|------|-------|
| `donation_id` | string | The `HH-XXXXXX-XXXX` formatted ID |

**Side Effects:**
- Increments `scan_count` by 1
- Auto-expires if `expiry_date` is in the past

**Response `200`:** Full `to_dict()` payload (38 fields)

**Error:** `404` if not found

---

### 4. Accept Donation

```
POST /api/donation/<donation_id>/accept
```

**Auth:** Optional — if JWT present, `accepted_by` auto-fills from user name.

**Path Parameter:**

| Param | Type | Notes |
|-------|------|-------|
| `donation_id` | string | The donation ID |

**Request Body (JSON, optional):**

| Field | Type | Notes |
|-------|------|-------|
| `accepted_by` | string | Name/org accepting (auto-filled if authed) |

**Response `200`:**
```json
{
  "message": "Donation accepted",
  "donation_id": "HH-M3X7K9-AB2F",
  "status": "accepted",
  "accepted_by": "Food Bank #3"
}
```

**Errors:**
- `404` — Not found
- `409` — Already accepted/delivered
- `400` — Expired or cancelled

---

### 5. Mark Donation as Delivered

```
POST /api/donation/<donation_id>/deliver
```

**Auth:** Optional — if JWT present, `delivered_by` auto-fills from user name.

**Path Parameter:**

| Param | Type | Notes |
|-------|------|-------|
| `donation_id` | string | The donation ID |

**Request Body (JSON, optional):**

| Field | Type | Notes |
|-------|------|-------|
| `delivered_by` | string | Name/org delivering (auto-filled if authed) |

**Response `200`:**
```json
{
  "message": "Donation marked as delivered — will be auto-removed in 24 hours",
  "donation_id": "HH-M3X7K9-AB2F",
  "status": "delivered",
  "delivered_at": "2026-03-04T14:30:00",
  "auto_remove_at": "2026-03-05T14:30:00"
}
```

**Errors:**
- `404` — Not found
- `409` — Already delivered
- `400` — Expired or cancelled

---

### 6. Donation Statistics

```
GET /api/donation/stats
```

**Auth:** Optional — if JWT present, returns personal stats; otherwise global.

**Response `200`:**
```json
{
  "total": 100,
  "active": 42,
  "accepted": 30,
  "delivered": 20,
  "expired": 5,
  "cancelled": 3,
  "scanned": 278
}
```

**Note:** Archived donations are excluded from stats.

---

### 7. Cleanup (Archive Old Donations)

```
POST /api/donations/cleanup
```

**Auth:** Required (JWT cookie, Admin role only)

**Request Body (JSON, optional):**

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `days` | integer | `7` | Archive donations older than this many days |

**Behavior:**
- Finds donations with `created_at ≤ (now - days)` that are NOT already archived AND have status `active`, `expired`, or `cancelled`
- Sets `is_archived = true` and `status = 'archived'`
- Does **not** hard-delete any data (soft-delete only)

**Response `200`:**
```json
{
  "message": "Archived 12 donation(s) older than 7 day(s)",
  "archived_count": 12,
  "cutoff": "2026-02-25T12:00:00"
}
```

**Errors:**
- `403` — Non-admin user
- `400` — Invalid `days` value

---

## Authentication Model

Endpoints use JWT tokens stored in a cookie named `jwt_python_flask` (configurable via `JWT_TOKEN_NAME` env var).

| Level | Behavior |
|-------|----------|
| **None** | Endpoint works without any auth |
| **Optional** | If cookie present, uses it to auto-fill fields (e.g. `user_id`, `accepted_by`) |
| **Required** | Returns `401` if not authenticated |
| **Admin** | Returns `403` if authenticated user does not have `Admin` role |

---

## Status Lifecycle

```
                  ┌──────────┐
                  │  active   │
                  └────┬──┬──┘
                       │  │
           POST /accept│  │ expiry_date < today
                       │  │ (auto on GET)
                       ▼  ▼
               ┌──────────┐  ┌─────────┐
               │ accepted  │  │ expired │
               └─────┬─────┘  └─────────┘
                     │
          POST /deliver
                     │
                     ▼
               ┌───────────┐
               │ delivered  │
               └───────────┘

  Any active/expired/cancelled → archived  (via POST /donations/cleanup)
  Any active → cancelled                   (manual status change)
```
