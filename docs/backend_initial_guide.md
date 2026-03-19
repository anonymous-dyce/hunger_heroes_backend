## **Overview**
This is a **food donation platform backend** built with **Flask (Python)** using SQLAlchemy ORM. Despite the README mentioning "Poway Auto," the actual application is **Hunger Heroes** — a system for managing food donations, tracking them, and connecting donors with organizations.

---

## **Technology Stack**

| Component | Technology |
|-----------|-----------|
| **Framework** | Flask (Python) |
| **Database** | SQLite (dev) / MySQL (production) |
| **Authentication** | JWT + Flask-Login |
| **Payment** | Stripe API |
| **Deployment** | Docker + Gunicorn (port 8288) |
| **Reverse Proxy** | Nginx |
| **Background Jobs** | APScheduler |
| **ORM** | SQLAlchemy |

---

## **Database Models & Structure**

### **Core Donation System**
- **Donation** (donation.py)
  - Food details: name, category, quantity, unit, description
  - Safety: expiry date, storage type, allergens, dietary tags
  - Donor info: name, email, phone, zip code
  - Status tracking: active → accepted → delivered → expired/cancelled
  - Auto-generated donation IDs (format: `HH-XXXXXX-XXXX`)
  - Scan counting and delivery tracking

### **User & Authentication**
- **User** (user.py)
  - Username, email, password (hashed)
  - Roles: Admin, User
  - Profile picture, car info
  - Flask-Login integration

### **Subscription System**
- **Subscription** (subscription.py)
  - Tiers: Free, Plus ($4.99/mo), Pro ($9.99/mo)
  - Stripe integration for payments
  - Status tracking (active, pending, cancelled, expired)
  - Billing intervals: monthly/yearly

- **PaymentHistory** - Tracks all payment transactions
- **RouteUsage** - Tracks route planning usage per tier
  - Free: 5 routes/day
  - Plus: 50 routes/day  
  - Pro: Unlimited

### **Community & Discussion**
- **Section** - Top-level community categories
- **Group** - Groups within sections with moderators
- **Channel** - Discussion channels within groups
- **Post** (post.py) - Posts within channels
- **NestPost** - Nested/threaded posts
- **Vote** - Upvotes/downvotes on posts
- **Feedback** - Comments on posts

### **User Features**
- **SavedLocations** - Favorite locations (limited by tier)
- **CarChat**, **CarPhoto** - Car-related features (legacy)
- **Preferences** - User preferences storage

---

## **API Endpoints**

### **Donation Management** (`/api/donation`)
```
POST   /api/donation          → Create new donation (no auth required)
GET    /api/donation          → Get user's donations (auth required)
DELETE /api/donation/<id>     → Cancel donation
GET    /api/donation/<id>/accept  → Accept donation
GET    /api/donation/<id>/deliver → Mark as delivered
```

### **User Management** (`/api/user`)
```
POST   /api/user              → Create user
GET    /api/users             → Get all users (auth required)
PUT    /api/user/<id>         → Update user
DELETE /api/user/<id>         → Delete user
```

### **Route Planning** (`/api/routes`)
```
POST   /api/routes            → Get optimized route with traffic data
                                 (tier-gated daily limits apply)
```

### **Traffic Data** (`/api/traffic`)
```
GET    /api/traffic/<street>  → Get traffic level for street
                                 (uses San Diego traffic counts CSV)
```

### **Community** (api)
```
GET    /api/channels          → List channels
GET    /api/groups            → List groups
GET    /api/sections          → List sections
POST   /api/post              → Create post
GET    /api/post              → Get posts (filtered by channel)
POST   /api/vote              → Upvote/downvote post
PORT   /api/feedback          → Add feedback to post
```

### **Favorites & Locations** (`/api/savedLocations`)
```
POST   /api/savedLocations    → Save a location (tier-limited)
GET    /api/savedLocations    → Get user's saved locations
PUT    /api/savedLocations    → Update saved location
DELETE /api/savedLocations    → Delete saved location
```

### **Incidents** (`/api/incidents`)
```
POST   /api/incidents         → Report incident/hazard
GET    /api/incidents         → Get all incidents
```

### **Subscription & Payments** (api)
```
GET    /api/subscription      → Get user's subscription
POST   /api/subscription/upgrade → Upgrade tier
POST   /api/stripe/payment    → Create Stripe payment
POST   /api/stripe/webhook    → Handle Stripe callbacks
```

### **Businesses** (`/api/businesses`)
```
GET    /api/businesses        → Get local business directory (public)
POST   /api/businesses/spotlight → Spotlight business
```

### **Other**
```
GET    /api/messages          → Get messages from file
POST   /api/messages          → Append message
GET    /api/chat              → Get chat messages (dummy)
GET    /api/pfp/<user_id>     → Get profile picture
POST   /api/nestImg           → Upload nested image
```

---

## **File Structure & Connections**

```
main.py
├─ Registers all API blueprints
├─ Sets up authentication (Flask-Login)
├─ Defines HTML routes (/login, /logout, /)
└─ Initializes db models and schedulers

__init__.py
├─ Initializes Flask app
├─ Configures database (SQLite/MySQL based on env)
├─ Sets up CORS for frontend (localhost:4887, GitHub Pages)
├─ Loads environment variables (.env file)
└─ Configures JWT, session cookies, upload settings

api/
├─ donation.py      ──→ model/donation.py
├─ user.py          ──→ model/user.py
├─ route.py         ──→ api/traffic.py (depends on)
├─ subscription.py  ──→ model/subscription.py
├─ stripe_api.py    ──→ model/subscription.py (payment processing)
├─ businesses.py    ──→ In-memory data
├─ chat.py          ──→ Dummy data
├─ savedLocations.py ──→ model/savedLocations.py
├─ post.py          ──→ model/post.py
├─ feedback.py      ──→ model/feedback.py
├─ vote.py          ──→ model/vote.py
├─ jwt_authorize.py ──→ Authorization decorator
└─ traffic.py       ──→ Reads api/data/traffic_counts_datasd.csv

model/
├─ user.py          ──→ Has relationship to Post
├─ donation.py      ──→ References User (foreign key)
├─ subscription.py  ──→ References User (foreign key)
├─ post.py          ──→ References User, Channel
├─ channel.py       ──→ References Group
├─ group.py         ──→ References Section, has many-to-many with User (moderators)
├─ feedback.py      ──→ References User, Post
├─ vote.py          ──→ References User, Post
├─ savedLocations.py ──→ References User
└─ cleanup.py       ──→ Background scheduler for donation cleanup
```

---

## **How It Works - User Flow**

### **1. Donation Flow**
```
User creates donation → API validates → Generates donation ID
→ Stores in database → Organization sees in feed
→ Org accepts donation → Marked "accepted"
→ Org delivers/uses → Marked "delivered"
→ Auto-deleted after 24 hours (cleanup scheduler)
```

### **2. Route Planning (Subscription-Gated)**
```
User requests route → JWT auth validates tier
→ Checks daily usage limit → Calls Google Maps API
→ Adds traffic adjustments from CSV data
→ Returns optimized route with ETA
```

### **3. Subscription Tier System**
```
Free User:
  - 5 routes/day
  - Can view 1 saved location
  - Basic donation posting

Plus User ($4.99/mo):
  - 50 routes/day
  - 10 saved locations
  - All community features

Pro User ($9.99/mo):
  - Unlimited routes
  - Unlimited saved locations
  - Full feature access
```

### **4. Authentication**
```
User logs in → Flask-Login creates session
User makes API request → JWT token in cookie
Decorator @token_required() → Validates JWT
→ Decodes token → Retrieves User from DB
→ Sets g.current_user → Request proceeds
```

---

## **Deployment Setup**

### **Docker Deployment**
```dockerfile
FROM python:3.12
WORKDIR /
RUN pip install -r requirements.txt && pip install gunicorn
ENV GUNICORN_CMD_ARGS="--workers=1 --bind=0.0.0.0:8288"
EXPOSE 8288
CMD [ "gunicorn", "main:app" ]
```

### **Docker Compose** (docker-compose.yml)
```yaml
Services:
  web:
    image: hunger
    ports: 8288:8288
    volumes: ./instance:/instance
    env_file: .env
    restart: unless-stopped
```

### **Production Database**
- Uses **MySQL** when `DB_ENDPOINT`, `DB_USERNAME`, `DB_PASSWORD` environment variables are set
- Production runs on port **8288** behind Nginx reverse proxy
- Nginx config file exists: litconnect.stu.nginx_file

### **Background Processes**
- **APScheduler** runs every 30 minutes to clean up donations marked "delivered" older than 24 hours

---

## **Frontend Integration**

The backend serves:
- **API endpoints** in JSON format for React/Vue frontend
- **HTML templates** for server-side rendering (login page, user tables)
- **Static files** (CSS, JS, images in static directory)
- **Profile picture uploads** to `/instance/uploads/<user_folder>/`

**CORS Configuration:**
```python
origins=['localhost:4887', '127.0.0.1:4887', 'https://ahaanv19.github.io']
```