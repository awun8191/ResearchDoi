# ResearchDoi Workspace Rules

## 1. FastAPI Route Ordering
When defining FastAPI routers, always place specific endpoints (e.g., `/search`) **before** catch-all or path-parameter endpoints (e.g., `/{doi:path}`). Catch-all routes will intercept and shadow specific routes if placed before them.

## 2. Frontend/Backend State Syncing
For core entities (like Projects) that exist across the stack, do not rely solely on `localStorage`. Always ensure that creation (`POST`) and update (`PATCH`) operations explicitly hit the backend API first, and only use `localStorage` as a cache or fallback.

## 3. Test Runner Separation (Vitest vs Playwright)
When a project uses both Vitest for unit testing and Playwright for E2E testing, ensure the `vite.config.js` explicitly excludes the E2E testing directories (`**/e2e/**`) from Vitest runs to prevent Vitest from attempting to execute Playwright tests.
