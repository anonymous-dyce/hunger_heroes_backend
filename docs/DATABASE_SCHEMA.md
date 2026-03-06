# Hunger Heroes Database Schema

## Entity Relationship Diagram (ERD)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATABASE ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────────┐
                                    │    USERS     │
                                    └──────┬───────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
            ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
            │ DONATIONS    │      │ SUBSCRIPTIONS│      │ORGANIZATIONS │
            └──────┬───────┘      └──────────────┘      └──────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
   ┌─────────┐ ┌──────────┐ ┌─────────────────┐
   │ALLERGEN │ │FOOD      │ │DONATION_FEEDBACK│
   │PROFILE  │ │SAFETY_LOG│ └─────────────────┘
   └─────────┘ └──────────┘

        ┌───────────────────────────────────┐
        │   COMMUNITY/DISCUSSION MODELS     │
        └───────────────────────────────────┘
        │
        ├─ SECTIONS ─────→ GROUPS ────→ CHANNELS ────→ POSTS
        │                                              │
        │                                              ├─→ VOTES
        │                                              └─→ FEEDBACK
        │
        └─ Other Models: SavedLocations, Vote, Feedback, etc.
```

---

## Core Models

### 1. **USERS**
```
users (id, _name, _uid, _email, _password, _role, _pfp, _car, created_at, updated_at)

Attributes:
  ├─ id: Integer, Primary Key
  ├─ _name: String(255), NOT NULL - Full name
  ├─ _uid: String(255), UNIQUE, NOT NULL - Username/login identifier
  ├─ _email: String(255), NOT NULL - Email address
  ├─ _password: String(255), NOT NULL - Hashed password
  ├─ _role: String(20), DEFAULT='User' - Role type
  │  ├─ 'Admin' - Full system access
  │  ├─ 'Donor' - Can create/manage donations
  │  ├─ 'Receiver' - Can accept donations (organizations)
  │  ├─ 'Volunteer' - Can help transport donations
  │  └─ 'User' - Basic user
  ├─ _pfp: String(255), NULLABLE - Profile picture path
  ├─ _car: String(255), NULLABLE - Vehicle information
  ├─ created_at: DateTime, DEFAULT=now()
  └─ updated_at: DateTime, DEFAULT=now()

Relationships:
  ├─ donated → Donation (user created donation)
  ├─ received_donations → Donation (user received donation)
  ├─ volunteered_donations → Donation (user transported)
  ├─ subscription → Subscription (1:1)
  ├─ moderated_groups → Group (many-to-many)
  ├─ food_safety_logs → FoodSafetyLog (inspector)
  ├─ reviews → DonationFeedback (reviewer)
  └─ posts → Post (authored)
```

---

### 2. **DONATIONS** - Food donation listings
```
donations (
  id, food_name, category, food_type, quantity, unit, serving_count, weight_lbs,
  description, expiry_date, storage, allergens, allergen_info, dietary_tags,
  temperature_at_pickup, storage_method,
  donor_name, donor_email, donor_phone, donor_zip,
  special_instructions, pickup_location, zip_code,
  pickup_window_start, pickup_window_end,
  user_id, donor_id, receiver_id, volunteer_id,
  status, is_archived, accepted_by, accepted_at,
  delivered_by, delivered_at, scan_count,
  created_at, updated_at
)

Status Flow: active → accepted → delivered → (archived or expired/cancelled)

Foreign Keys:
  ├─ user_id → users.id (legacy creator)
  ├─ donor_id → users.id (donor user account)
  ├─ receiver_id → users.id (receiving organization)
  └─ volunteer_id → users.id (volunteer transporter)

Referenced By:
  ├─ AllergenProfile (1:1)
  ├─ FoodSafetyLog (1:many)
  └─ DonationFeedback (1:many)
```

---

### 3. **ORGANIZATIONS** - Food banks, shelters, restaurants, temples
```
organizations (
  id, name, type, address, zip_code, capacity,
  accepted_food_types, operating_hours, contact_info,
  is_verified, verification_date, verified_by,
  phone, email, website, latitude, longitude,
  storage_capacity_lbs, refrigeration_available,
  dietary_restrictions_servable,
  created_at, updated_at, is_active
)

Attributes:
  ├─ id: Integer, Primary Key
  ├─ name: String(255), NOT NULL
  ├─ type: String(50), NOT NULL
  │  ├─ 'shelter' - Homeless shelter
  │  ├─ 'food_bank' - Food bank/distribution center
  │  ├─ 'restaurant' - Food business
  │  ├─ 'temple' - Religious organization
  │  └─ 'community_org' - Community center
  ├─ address: String(500), NOT NULL - Full address
  ├─ zip_code: String(10), NOT NULL
  ├─ capacity: Integer, NULLABLE - People it can serve
  ├─ accepted_food_types: JSON - List of food types accepted
  ├─ operating_hours: JSON - Opening/closing times
  │  └─ Format: {"monday": {"open": "09:00", "close": "17:00"}, ...}
  ├─ contact_info: JSON
  │  └─ Format: {"phone": "...", "email": "...", "manager": "..."}
  ├─ is_verified: Boolean, DEFAULT=False
  ├─ storage_capacity_lbs: Float - Max storage capacity
  ├─ refrigeration_available: Boolean - Has cold storage
  ├─ dietary_restrictions_servable: JSON - Special diets (vegan, halal, etc.)
  ├─ phone: String(20)
  ├─ email: String(255)
  ├─ website: String(500)
  ├─ latitude: Float - For mapping
  ├─ longitude: Float - For mapping
  ├─ is_active: Boolean, DEFAULT=True
  ├─ created_at: DateTime
  └─ updated_at: DateTime
```

---

### 4. **ALLERGEN_PROFILE** - Detailed allergen information for donations
```
allergen_profiles (
  id, donation_id, contains_nuts, contains_dairy, contains_gluten,
  contains_soy, contains_shellfish, contains_eggs, other_allergens,
  is_vegetarian, is_vegan, is_halal, is_kosher,
  created_at, updated_at
)

Attributes:
  ├─ id: Integer, Primary Key
  ├─ donation_id: String(50), UNIQUE, NOT NULL, FK→donations.id
  ├─ contains_nuts: Boolean, DEFAULT=False
  ├─ contains_dairy: Boolean, DEFAULT=False
  ├─ contains_gluten: Boolean, DEFAULT=False
  ├─ contains_soy: Boolean, DEFAULT=False
  ├─ contains_shellfish: Boolean, DEFAULT=False
  ├─ contains_eggs: Boolean, DEFAULT=False
  ├─ other_allergens: JSON, NULLABLE - Custom allergen list
  ├─ is_vegetarian: Boolean, DEFAULT=False
  ├─ is_vegan: Boolean, DEFAULT=False
  ├─ is_halal: Boolean, DEFAULT=False
  ├─ is_kosher: Boolean, DEFAULT=False
  ├─ created_at: DateTime
  └─ updated_at: DateTime

Foreign Keys:
  └─ donation_id → donations.id (1:1 relationship)

Purpose: Provide detailed allergen/dietary information for each donation
```

---

### 5. **FOOD_SAFETY_LOG** - Compliance and safety tracking
```
food_safety_logs (
  id, donation_id, temperature_reading, storage_method,
  handling_notes, inspector_id, logged_at, passed_inspection,
  inspection_date, notes, created_at
)

Attributes:
  ├─ id: Integer, Primary Key
  ├─ donation_id: String(50), NOT NULL, FK→donations.id
  ├─ temperature_reading: Float - Celsius or Fahrenheit
  ├─ storage_method: String(50) - cooler-with-ice, refrigerator, etc.
  ├─ handling_notes: Text - How food was handled
  ├─ inspector_id: Integer, FK→users.id - User who inspected
  ├─ logged_at: DateTime - When inspection happened
  ├─ passed_inspection: Boolean - Pass/fail status
  ├─ inspection_date: DateTime
  ├─ notes: Text - Additional inspection notes
  └─ created_at: DateTime

Foreign Keys:
  ├─ donation_id → donations.id (many:1)
  └─ inspector_id → users.id (many:1)

Purpose: Track food safety compliance, temperatures, and inspections
```

---

### 6. **DONATION_FEEDBACK** - Reviews and ratings
```
donation_feedbacks (
  id, donation_id, reviewer_id, food_quality_rating,
  timeliness_rating, overall_rating, comments,
  reported_issues, created_at, updated_at
)

Attributes:
  ├─ id: Integer, Primary Key
  ├─ donation_id: String(50), NOT NULL, FK→donations.id
  ├─ reviewer_id: Integer, NOT NULL, FK→users.id
  ├─ food_quality_rating: Integer (1-5 stars)
  ├─ timeliness_rating: Integer (1-5 stars) - On-time delivery
  ├─ overall_rating: Integer (1-5 stars)
  ├─ comments: Text - Feedback comments
  ├─ reported_issues: JSON - List of issues encountered
  ├─ created_at: DateTime
  └─ updated_at: DateTime

Foreign Keys:
  ├─ donation_id → donations.id (many:1, unique constraint on pair)
  └─ reviewer_id → users.id (many:1)

Purpose: Rate and review donations for quality assurance
```

---

### 7. **SUBSCRIPTIONS** - Payment and tier management
```
subscriptions (
  id, user_id, tier, status, billing_interval,
  created_at, updated_at, expires_at,
  stripe_customer_id, stripe_subscription_id
)

Attributes:
  ├─ id: Integer, Primary Key
  ├─ user_id: Integer, UNIQUE, NOT NULL, FK→users.id
  ├─ tier: String(20), DEFAULT='free'
  │  ├─ 'free' - Basic tier (5 routes/day)
  │  ├─ 'plus' - $4.99/month (50 routes/day)
  │  └─ 'pro' - $9.99/month (unlimited routes)
  ├─ status: String(20) - active, pending, cancelled, expired
  ├─ billing_interval: String(20) - monthly, yearly
  ├─ created_at: DateTime
  ├─ updated_at: DateTime
  ├─ expires_at: DateTime, NULLABLE
  ├─ stripe_customer_id: String(100)
  └─ stripe_subscription_id: String(100)

Foreign Keys:
  └─ user_id → users.id (1:1)
```

---

## Supporting Models (Existing)

### 8. **SECTIONS** - Top-level community categories
```
sections (id, _name, _image, _color, created_at, updated_at)
└─ Relationship: 1 section → many groups
```

### 9. **GROUPS** - Groups within sections
```
groups (id, _name, _section_id, created_at, updated_at)
├─ Foreign Key: _section_id → sections.id
├─ Relationship: many-to-many with users (moderators)
└─ Relationship: 1 group → many channels
```

### 10. **CHANNELS** - Discussion channels within groups
```
channels (id, _name, _attributes, _group_id, created_at, updated_at)
├─ Foreign Key: _group_id → groups.id
└─ Relationship: 1 channel → many posts
```

### 11. **POSTS** - Discussion posts
```
posts (id, _title, _comment, _content, _user_id, _channel_id, created_at, updated_at)
├─ Foreign Keys: _user_id → users.id, _channel_id → channels.id
├─ Relationship: 1 post → many votes
├─ Relationship: 1 post → many feedbacks
└─ Relationship: 1 post → many nest_posts (threaded)
```

### 12. **VOTES** - Upvotes/downvotes
```
votes (id, _vote_type, _user_id, _post_id, created_at)
├─ Foreign Keys: _user_id → users.id, _post_id → posts.id
└─ Types: 'upvote', 'downvote'
```

### 13. **FEEDBACKS** - Comments on posts
```
feedbacks (id, _content, _user_id, _post_id, created_at, updated_at)
└─ Foreign Keys: _user_id → users.id, _post_id → posts.id
```

### 14. **SAVED_LOCATIONS** - User's favorite locations
```
saved_locations (id, _user_id, _user_name, _address, _name, created_at, updated_at)
└─ Foreign Key: _user_id → users.id
```

---

## Relationships Summary

| From | To | Type | Description |
|------|-----|------|-------------|
| User | Donation | 1:N | Donor creates donations |
| User | Donation | 1:N | User receives donations |
| User | Donation | 1:N | Volunteer transports donations |
| User | Subscription | 1:1 | User has one subscription |
| User | Group | N:N | User can moderate groups |
| User | Post | 1:N | User author posts |
| User | Vote | 1:N | User votes on posts |
| User | Feedback | 1:N | User leaves feedback |
| User | DonationFeedback | 1:N | User reviews donations |
| User | FoodSafetyLog | 1:N | User inspects donations |
| Donation | AllergenProfile | 1:1 | Each donation has allergen info |
| Donation | FoodSafetyLog | 1:N | Multiple safety logs per donation |
| Donation | DonationFeedback | 1:N | Multiple feedback submissions |
| Organization | Donation | 1:N | Org receives donations |
| Section | Group | 1:N | Multiple groups per section |
| Group | Channel | 1:N | Multiple channels per group |
| Channel | Post | 1:N | Multiple posts per channel |
| Post | Vote | 1:N | Multiple votes per post |
| Post | Feedback | 1:N | Multiple comments per post |