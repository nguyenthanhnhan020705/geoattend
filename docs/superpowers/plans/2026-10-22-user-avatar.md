# User avatar upload

**Goal:** Each User can replace their own welcome avatar with an uploaded image, including animated GIFs.

**Architecture:** Authenticated GET/PUT `/api/account/avatar`, raw bounded image uploads, PostgreSQL bytea keyed by profile. Validate with Pillow; preserve original animation. Fetch through existing authenticated transport and display as a data URL (compatible with local CSP and Pages bearer authentication).

**Implementation:**
- [x] Add failing API tests for default, persistence, replacement, isolation, CSRF and invalid uploads.
- [x] Add migration, image validation and authenticated routes; cap uploads at 5 MB and dimensions at 4096 each, total decoded pixels at 80 million.
- [x] Add accessible file picker under welcome avatar, upload status, and reload persistence; mobile layout stays within existing card.
- [x] Run API and browser checks, Pages build checks; sync live checkout and apply migration/restart local service.

Verification: API persistence/isolation/CSRF/invalid upload/replacement tests passed on isolated PostgreSQL 55441. Browser upload+reload passed at mobile320, desktop1440 and Pages390. JPG/PNG/WebP/GIF and dimension validation passed. Reviewer found no important issues. Local migration006 applied and API reloaded on8000. Public deployment not performed in this task.
