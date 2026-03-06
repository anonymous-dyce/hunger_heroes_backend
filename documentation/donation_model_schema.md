# Donation Model Schema

> **Table name:** `donations`
> **File:** `model/donation.py`
> **Last updated:** 2026-03-04

---

## Entity Relationship Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                          donations                                │
├───────────────────┬───────────────┬───────────────────────────────┤
│  Column           │  Type         │  Constraints                  │
├───────────────────┼───────────────┼───────────────────────────────┤
│  id (PK)          │  String(50)   │  PRIMARY KEY                  │
│                   │               │  e.g. "HH-M3X7K9-AB2F"       │
├───────────────────┴───────────────┴───────────────────────────────┤
│  ── FOOD DETAILS ──                                               │
├───────────────────┬───────────────┬───────────────────────────────┤
│  food_name        │  String(200)  │  NOT NULL                     │
│  category         │  String(50)   │  NOT NULL (enum)              │
│  food_type        │  String(50)   │  nullable                     │
│  quantity         │  Integer      │  NOT NULL                     │
│  unit             │  String(30)   │  NOT NULL (enum)              │
│  serving_count    │  Integer      │  nullable                     │
│  weight_lbs       │  Float        │  nullable                     │
│  description      │  Text         │  nullable                     │
├───────────────────┴───────────────┴───────────────────────────────┤
│  ── SAFETY & HANDLING ──                                          │
├───────────────────┬───────────────┬───────────────────────────────┤
│  expiry_date      │  Date         │  NOT NULL                     │
│  storage          │  String(30)   │  NOT NULL (enum)              │
│  allergens        │  JSON         │  nullable (array)             │
│  allergen_info    │  Text         │  nullable (free-text notes)   │
│  dietary_tags     │  JSON         │  nullable (array)             │
├───────────────────┴───────────────┴───────────────────────────────┤
│  ── FOOD SAFETY COMPLIANCE ──                                     │
├───────────────────┬───────────────┬───────────────────────────────┤
│  temperature_at   │  Float        │  nullable (°F at pickup)      │
│    _pickup        │               │                               │
│  storage_method   │  String(50)   │  nullable (enum)              │
├───────────────────┴───────────────┴───────────────────────────────┤
│  ── DONOR INFO ──                                                 │
├───────────────────┬───────────────┬───────────────────────────────┤
│  donor_name       │  String(200)  │  NOT NULL                     │
│  donor_email      │  String(200)  │  NOT NULL                     │
│  donor_phone      │  String(30)   │  nullable                     │
│  donor_zip        │  String(10)   │  NOT NULL                     │
│  special_         │  Text         │  nullable                     │
│    instructions   │               │                               │
├───────────────────┴───────────────┴───────────────────────────────┤
│  ── PICKUP DETAILS ──                                             │
├───────────────────┬───────────────┬───────────────────────────────┤
│  pickup_location  │  String(500)  │  nullable (full address)      │
│  zip_code         │  String(10)   │  nullable (pickup zip)        │
│  pickup_window    │  DateTime     │  nullable (ISO 8601)          │
│    _start         │               │                               │
│  pickup_window    │  DateTime     │  nullable (ISO 8601)          │
│    _end           │               │                               │
├───────────────────┴───────────────┴───────────────────────────────┤
│  ── FOREIGN KEYS → users.id ──                                    │
├───────────────────┬───────────────┬───────────────────────────────┤
│  user_id          │  Integer (FK) │  nullable (legacy creator)    │
│  donor_id         │  Integer (FK) │  nullable (donor account)     │
│  receiver_id      │  Integer (FK) │  nullable (receiving org)     │
│  volunteer_id     │  Integer (FK) │  nullable (courier)           │
├───────────────────┴───────────────┴───────────────────────────────┤
│  ── TRACKING ──                                                   │
├───────────────────┬───────────────┬───────────────────────────────┤
│  status           │  String(20)   │  default 'active' (enum)      │
│  is_archived      │  Boolean      │  default False                │
│  accepted_by      │  String(200)  │  nullable                     │
│  accepted_at      │  DateTime     │  nullable                     │
│  delivered_by     │  String(200)  │  nullable                     │
│  delivered_at     │  DateTime     │  nullable                     │
│  scan_count       │  Integer      │  default 0                    │
├───────────────────┴───────────────┴───────────────────────────────┤
│  ── TIMESTAMPS ──                                                 │
├───────────────────┬───────────────┬───────────────────────────────┤
│  created_at       │  DateTime     │  default utcnow               │
│  updated_at       │  DateTime     │  default utcnow, on-update    │
└───────────────────┴───────────────┴───────────────────────────────┘


                ┌──────────┐
                │  users   │
                │  (id PK) │
                └────┬─────┘
                     │
        ┌────────────┼───────────────┬──────────────┐
        │ FK         │ FK            │ FK           │ FK
        ▼            ▼               ▼              ▼
   user_id       donor_id       receiver_id    volunteer_id
   (legacy)      (donor)        (org/user)     (courier)
        └────────────┴───────────────┴──────────────┘
                     │
              ┌──────┴──────┐
              │  donations  │
              └─────────────┘
```

---

## Enum / Allowed Values Reference

### `category`
```
canned | fresh-produce | dairy | bakery | meat-protein | grains |
beverages | frozen | snacks | baby-food | prepared-meals | other
```

### `unit`
```
items | lbs | kg | oz | cans | boxes | bags | trays | servings
```

### `storage`
```
room-temp | refrigerated | frozen | cool-dry
```

### `food_type`
```
cooked | raw | packaged | perishable | non-perishable |
baked | frozen-prepared | canned-goods | beverage | other
```

### `storage_method` (transit)
```
cooler-with-ice | insulated-bag | refrigerator | freezer |
room-temperature-shelf | heated-container | other
```

### `allergens`
```
gluten | dairy | nuts | soy | eggs | shellfish | fish | none
```

### `dietary_tags`
```
vegetarian | vegan | halal | kosher | gluten-free | organic
```

### `status`
```
active | accepted | delivered | expired | cancelled | archived
```

---

## Serialization

### `to_dict()` — Full response (38 keys)

Returns all fields. Used by detail/scan endpoints.

```json
{
  "id": "HH-M3X7K9-AB2F",
  "food_name": "Veggie Tray",
  "category": "fresh-produce",
  "food_type": "raw",
  "quantity": 10,
  "unit": "trays",
  "serving_count": 50,
  "weight_lbs": 15.5,
  "description": "Assorted raw veggies with hummus",
  "expiry_date": "2026-03-06",
  "storage": "refrigerated",
  "allergens": ["nuts"],
  "allergen_info": "Contains tree nuts in hummus.",
  "dietary_tags": ["vegan", "gluten-free"],
  "temperature_at_pickup": 38.0,
  "storage_method": "cooler-with-ice",
  "donor_name": "Green Garden",
  "donor_email": "info@greengarden.com",
  "donor_phone": "555-0100",
  "donor_zip": "92101",
  "special_instructions": "Keep cold",
  "pickup_location": "100 Veggie St, San Diego, CA",
  "zip_code": "92101",
  "pickup_window_start": "2026-03-05T09:00:00",
  "pickup_window_end": "2026-03-05T17:00:00",
  "user_id": null,
  "donor_id": null,
  "receiver_id": null,
  "volunteer_id": null,
  "status": "active",
  "is_archived": false,
  "scan_count": 0,
  "accepted_by": null,
  "accepted_at": null,
  "delivered_by": null,
  "delivered_at": null,
  "created_at": "2026-03-04T12:00:00",
  "updated_at": "2026-03-04T12:00:00"
}
```

### `to_dict_short()` — Compact response (14 keys)

Used by list/paginated endpoints for faster payloads.

```json
{
  "id": "HH-M3X7K9-AB2F",
  "food_name": "Veggie Tray",
  "category": "fresh-produce",
  "food_type": "raw",
  "quantity": 10,
  "unit": "trays",
  "serving_count": 50,
  "weight_lbs": 15.5,
  "expiry_date": "2026-03-06",
  "status": "active",
  "is_archived": false,
  "pickup_location": "100 Veggie St, San Diego, CA",
  "zip_code": "92101",
  "created_at": "2026-03-04T12:00:00"
}
```

---

## ID Generation

IDs are generated with `generate_donation_id()` in the format:

```
HH-{6-char base36 timestamp}-{4-char random suffix}
```

Example: `HH-M3X7K9-AB2F`

These are human-readable barcode labels suitable for QR/Code128 encoding.

---

## Relationships

| Relationship  | Field          | Target       | Backref on User            |
|---------------|----------------|--------------|----------------------------|
| Legacy creator| `user_id`      | `users.id`   | *(none — raw FK)*          |
| Donor         | `donor_id`     | `users.id`   | `user.donated`             |
| Receiver      | `receiver_id`  | `users.id`   | `user.received_donations`  |
| Volunteer     | `volunteer_id` | `users.id`   | `user.volunteered_donations`|
