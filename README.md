# Hunger Heroes — Backend

Small, maintainable backend for the Hunger Heroes project (API + data layer).

## Overview
This repository provides the HTTP API and persistence for Hunger Heroes: user accounts, donation flows, meal records, and basic admin operations.

## Features
- REST JSON API for users, donations, meals
- Authentication (JWT)
- Database migrations & seed helpers
- Tests and linting

## Tech stack (recommended)
- Node.js (LTS) + npm or yarn
- Express / Fastify (or similar)
- PostgreSQL (or compatible SQL DB)
- Optional: Redis for caching, Docker for local dev

## Quick start
1. Clone
   ```bash
   git clone <repo> && cd hunger_heroes_backend
   ```
2. Copy env
   ```bash
   cp .env.example .env
   ```
3. Install
   ```bash
   npm install
   # or
   yarn
   ```
4. Create DB and run migrations
   ```bash
   # example with a migration tool
   npm run db:migrate
   npm run db:seed
   ```
5. Start dev server
   ```bash
   npm run dev
   ```

## Environment variables (example)
```
PORT=3000
NODE_ENV=development
DATABASE_URL=postgres://user:pass@localhost:5432/hunger_heroes
JWT_SECRET=replace_with_secure_secret
LOG_LEVEL=info
REDIS_URL=redis://localhost:6379
```

## Typical scripts
- npm run dev — start development server with hot-reload
- npm start — start production server
- npm test — run test suite
- npm run lint — run linters
- npm run db:migrate / db:seed — database tasks

## Minimal API examples
- Register: POST /api/auth/register { "email", "password" }
- Login: POST /api/auth/login { "email", "password" } → returns JWT
- Get user: GET /api/users/:id (auth)
- Create donation: POST /api/donations (auth) { "amount", "note" }
- List meals: GET /api/meals

Example curl:
```bash
curl -H "Authorization: Bearer $TOKEN" https://api.example.com/api/donations
```

## Testing
- Write unit & integration tests.
- Use an isolated test database; run migrations before tests.
- CI should run lint, tests, and (optional) security checks.

## Contributing
- Follow the repository's code style and tests.
- Open issues or PRs with clear descriptions and reproducible steps.

