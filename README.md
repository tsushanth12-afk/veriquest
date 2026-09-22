# VeriQuest — Hardware Engineering Mastery Platform

> **The "LeetCode for Verilog HDL"** — High-performance, gamified hardware description language learning platform powered by container-sandboxed Icarus Verilog execution, cryptographic token verification, and server-authoritative gamification.

---

## 1. Architectural Philosophy & Resolved Invariants

VeriQuest is engineered with strict pedagogical and infrastructural guardrails:

- **Warm Neumorphic Aesthetics**: Designed with a bespoke, tactile warm light aesthetic (`#E8E0D3` background, `#F7F1E8` highlight, `#C5BBAA` soft shadow, `#C96F4A` terracotta accent, `#B65D45` copper, `#7D8765` sage, and `#302B27` ink text). All UI components, including the custom `veriquest-warm` Monaco code editor, reflect this tactile parchment direction.
- **Zero AI Functionality**: 100% deterministic hardware compilation and testbench assertion. No chatbots, no LLM hints, and no generative AI grading.
- **Strict Confidentiality by Construction**: Student-facing models, API endpoints, and network payloads never contain `official_solution` or `hidden_testbench`. Secrets reside strictly in isolated PostgreSQL `private` schemas accessible only to backend validation workers.
- **Server-Authoritative Progress & XP**: The frontend never calculates or transmits XP or level advancements. Submissions execute in isolated sandboxes, and XP is awarded via idempotent database transactions with row-level locks (`SELECT ... FOR UPDATE`).
- **Single Development Demo**: The platform launches with exactly one demo challenge (*"Two-Input AND Gate"*, `and-gate-demo`), explicitly labeled **"Development Demo"** across all surfaces. Fresh users start at Level 1 with 0 XP and zero fabricated statistics.

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph Client ["Frontend (Vite + React 19 + TypeScript)"]
        UI[Tactile Neumorphic UI]
        Monaco["Monaco Editor (veriquest-warm)"]
        APIClient["Typed API Client (src/api/client.ts)"]
    end

    subgraph Auth ["Identity & Auth Layer"]
        SupaAuth["Supabase Auth (GoTrue)"]
        JWKS["RS256 Asymmetric JWKS Public Keys"]
    end

    subgraph Backend ["Application Server (FastAPI + AsyncPG)"]
        FastAPI["FastAPI Gateway"]
        AuthMiddleware["JWT Verification (RS256 JWKS)"]
        RateLimiter["Redis Token-Bucket Limiter"]
        PublicAPI["Public Challenge Endpoints"]
        AdminAPI["Admin Authoring & Validation"]
        SubmissionsAPI["Submission Dispatcher"]
    end

    subgraph Queue ["Message Broker"]
        Redis[("Redis 7.0 (Celery Broker)")]
    end

    subgraph ExecutionWorker ["Execution Cluster (Celery Worker)"]
        HDLWorker["HDL Job Processor"]
        Evaluator["Deterministic Evaluator & Parser"]
        Sandbox["Hardened Docker Sandbox"]
        IVerilog["Icarus Verilog (iverilog + vvp)"]
    end

    subgraph Database ["PostgreSQL (Supabase)"]
        PublicSchema[("public Schema (Profiles, Submissions, Progress)")]
        PrivateSchema[("private Schema (Official Solutions, Hidden TBs)")]
        IdempotentLock["Row Lock: SELECT FOR UPDATE"]
    end

    %% Interactions
    UI --> Monaco
    UI --> APIClient
    APIClient -->|Authenticate| SupaAuth
    APIClient -->|Bearer JWT| FastAPI
    FastAPI --> AuthMiddleware
    AuthMiddleware -->|Fetch Public Keys| JWKS
    FastAPI --> RateLimiter
    RateLimiter --> Redis
    FastAPI --> PublicAPI
    FastAPI --> AdminAPI
    FastAPI --> SubmissionsAPI
    PublicAPI --> PublicSchema
    AdminAPI --> PrivateSchema
    AdminAPI --> PublicSchema
    SubmissionsAPI -->|Create Queued Record| PublicSchema
    SubmissionsAPI -->|Enqueue Task| Redis
    Redis --> HDLWorker
    HDLWorker --> Sandbox
    Sandbox --> IVerilog
    IVerilog --> Evaluator
    Evaluator -->|Idempotent Award| IdempotentLock
    IdempotentLock --> PublicSchema
```

---

## 3. Sandboxed Execution Hardening (Section 2)

Untrusted student Verilog code is isolated inside an ephemeral Docker container with multi-layered containment:

| Security Dimension | Implementation & Hardening Flag | Purpose |
| :--- | :--- | :--- |
| **Kernel Capabilities** | `--cap-drop=ALL` | Drops all root capabilities in the container |
| **Privilege Escalation** | `--security-opt no-new-privileges:true` | Prevents setuid binaries and child escalation |
| **Filesystem Security** | Read-only root (`/` is read-only) | Prevents modification of simulator runtime binaries |
| **RAM Workspace** | `--tmpfs /workspace:rw,noexec,nosuid,size=64m` | Single temporary workspace in RAM; auto-wiped |
| **Network Isolation** | `--network=none` | Zero network sockets; blocks exfiltration & C2 |
| **Container User** | Non-root `UID:GID 1000:1000` | Eliminates container breakouts via root UID 0 |
| **Resource Quotas** | `1.0 CPU`, `256 MB RAM`, `64 PIDs` | Prevents fork bombs and computational exhaustion |
| **Execution Timeout** | `5000ms compilation`, `5000ms simulation` | Hard wall-clock process termination |
| **Output Bound** | `65,536 bytes (64 KB)` max capture | Blocks terminal buffer flooding and memory bloat |
| **Workspace Lifecycle**| Ephemeral `mkdtemp` + `finally:` block | Unconditional deletion of files & containers |

---

## 4. Evaluator Rules & Error Boundaries (Section 7)

```
                       ┌─────────────────────────┐
                       │   Simulation Process    │
                       └────────────┬────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
        [Returncode != 0]                     [Returncode == 0]
                  │                                   │
                  ▼                                   ▼
       COMPILATION_ERROR                     Check Output Format
       (Counts as attempt)                            │
                                      ┌───────────────┴───────────────┐
                                      ▼                               ▼
                              [Valid Header]                  [Missing/Corrupt]
                                      │                               │
                        ┌─────────────┴─────────────┐                 ▼
                        ▼                           ▼            SYSTEM_ERROR
                    ACCEPTED                  WRONG_ANSWER     (0 attempt penalty,
               (Awards XP once)            (Counts as attempt)   auto-retry x1)
```

- **Section 7 Invariant**: If the simulation simulator crashes or emits malformed output without standard markers, it classifies strictly as `SYSTEM_ERROR`. This **does not penalize student attempts** (0 attempt consumed) and notifies course administrators of a testbench defect.

---

## 5. Challenge Authoring & Re-validation Lifecycle (Section 4)

Challenges progress through a strict state machine:

```
[DRAFT] ───► [VALIDATING] ───► [VALIDATED] ───► [PUBLISHED] ───► [ARCHIVED]
   ▲              │
   │              ▼ (Validation Failure)
   └────── [VALIDATION_FAILED]
```

### The Section 4 Re-Validation Invariant
1. Modifying the `official_solution`, `hidden_testbench`, or `execution_profile` of a `PUBLISHED` challenge triggers an automated database trigger (`on_secret_changed_invalidate`).
2. The challenge is immediately un-published (`is_published = false`, `validation_status = 'draft'`), hiding it from the student catalog until course staff re-run `VALIDATE`.
3. Existing student completions and XP transactions are preserved intact.

---

## 6. Rate Limiting Specifications (Section 6)

Implemented via a Redis sliding-window counter with automatic in-memory fallback:

| Action | Limit | Window | Scope | Response |
| :--- | :--- | :--- | :--- | :--- |
| **Login** | 5 attempts | 5 minutes (300s) | Client IP | `429 Too Many Requests` |
| **Signup** | 3 attempts | 1 hour (3600s) | Client IP | `429 Too Many Requests` |
| **Password Reset** | 3 requests | 1 hour (3600s) | Client IP | `429 Too Many Requests` |
| **Submission Creation** | 10 submissions | 1 minute (60s) | User ID | `429 Too Many Requests` |
| **Submission Polling** | Uncapped count | Max 60s total | Client Poller | Stop & surface pending |
| **Admin Actions** | 20 actions | 1 minute (60s) | Admin User ID | `429 Too Many Requests` |

---

## 7. Repository Structure

```
veriquest/
├── .github/
│   └── workflows/
│       └── ci.yml                 # GitHub Actions lint, test, build pipeline
├── backend/
│   ├── app/
│   │   ├── admin/                 # Challenge lifecycle & audit logging
│   │   ├── challenges/            # Public challenge API & schemas
│   │   ├── core/                  # Security (JWKS), Rate limits, Config
│   │   ├── db/                    # AsyncPG connection pooling
│   │   ├── gamification/          # Idempotent XP & level calculations
│   │   ├── profile/               # User stats & safe profile PATCH
│   │   ├── submissions/           # Non-blocking submission dispatcher
│   │   └── main.py                # FastAPI entrypoint & CORS configuration
│   ├── tests/                     # Pytest suite (security, schemas, limits)
│   └── requirements.txt           # Python dependencies
├── src/
│   ├── api/                       # Typed API client with 9 domain namespaces
│   ├── components/
│   │   ├── auth/                  # Neumorphic AuthModal with Escape dismissal
│   │   ├── common/                # Shared badges, toast notifications
│   │   ├── layout/                # Responsive Sidebar, Header, MobileNav
│   │   └── workspace/             # Monaco warm theme, ProblemPanel, SubmissionPanel
│   ├── styles/
│   │   ├── tokens.css             # Palette, fonts, tactile shadows, radii
│   │   └── neumorphic.css         # Neumorphic utility classes & focus rings
│   ├── views/                     # Dashboard, Challenges, Workspace, Admin, etc.
│   └── App.tsx                    # Route switcher & state orchestrator
├── supabase/
│   └── migrations/
│       ├── 001_initial_schema.sql # 11 tables, RLS policies, revalidation triggers
│       └── 002_seed_demo_challenge.sql # AND Gate Development Demo challenge
├── worker/
│   ├── execution/                 # Hardened Docker sandbox & parser
│   ├── tasks/                     # Celery background job runner
│   ├── celeryconfig.py            # Celery broker configuration
│   └── Dockerfile                 # Icarus Verilog execution container
└── tests/
    └── security_and_contracts.test.js # Local automated invariant test suite
```

---

## 8. Prerequisites & Environment Setup

### Required Tools
- **Node.js**: `v20.x` or `v22.x`
- **Python**: `3.11+`
- **Docker**: Engine `24+` with buildx
- **PostgreSQL**: `15+` (or Supabase Cloud instance)
- **Redis**: `7.0+`

### Environment Configuration (`.env`)
Create a `.env` file in the project root:

```env
# Supabase Configuration
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOi...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# Database Direct Connection (for FastAPI asyncpg pool)
DATABASE_URL=postgresql://postgres:yourpassword@db.your-project.supabase.co:5432/postgres

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Application Settings
ENVIRONMENT=development
PORT=8000
VITE_API_BASE_URL=http://localhost:8000
```

---

## 9. Running the Stack

### Option A: Local Development

```bash
# 1. Start Redis
docker run -d --name vq-redis -p 6379:6379 redis:7-alpine

# 2. Build the execution container image
docker build -t veriquest-runner worker/

# 3. Start the FastAPI Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. Start Celery HDL Execution Worker (in separate shell)
celery -A worker.tasks.hdl_task worker --loglevel=info --concurrency=2

# 5. Start Frontend Dev Server (in project root)
npm install
npm run dev
```

### Option B: Docker Compose Full Stack

```bash
docker-compose up --build -d
```

---

## 10. Database Migrations

Apply migrations to your Supabase project in order:

```bash
# Apply schema, tables, RLS, and revalidation triggers
psql "$DATABASE_URL" -f supabase/migrations/001_initial_schema.sql

# Seed demo challenge ("Two-Input AND Gate")
psql "$DATABASE_URL" -f supabase/migrations/002_seed_demo_challenge.sql
```

---

## 11. Bulk Problem-Set Import Guide (For Course Staff)

Faculty and course coordinators can import large problem sets using the standardized ingestion structure:

### Problem Set Manifest Directory Layout
```
problem-sets/ece241/
├── manifest.json
├── and_gate/
│   ├── spec.md
│   ├── starter.v
│   ├── solution.v
│   └── testbench.v
└── alu_8bit/
    ├── spec.md
    ├── starter.v
    ├── solution.v
    └── testbench.v
```

### `manifest.json` Structure
```json
{
  "course": "ECE 241",
  "category": "Combinational Logic",
  "challenges": [
    {
      "slug": "ece241-and-gate",
      "title": "Two-Input AND Gate",
      "difficulty": "Easy",
      "level_number": 1,
      "xp_reward": 50,
      "files": {
        "spec": "and_gate/spec.md",
        "starter": "and_gate/starter.v",
        "solution": "and_gate/solution.v",
        "testbench": "and_gate/testbench.v"
      }
    }
  ]
}
```

### Ingestion Script Workflow
1. For each entry in `manifest.json`, issue `POST /api/v1/admin/challenges` with `service_role` credentials.
2. Call `POST /api/v1/admin/challenges/{id}/validate`. The worker compiles `solution.v` against `testbench.v` in the Docker sandbox.
3. If validation succeeds (100% assertions pass), issue `POST /api/v1/admin/challenges/{id}/publish`.
4. All actions are immutably logged to `public.admin_audit_log`.

---

## 12. Environment Promotion Path

VeriQuest supports an automated three-tier deployment pipeline:

```
[Local Development] ──► [Staging (Supabase + Railway)] ──► [Production (AWS / Supabase Pro)]
```

1. **Local Development**:
   - Verification with `npm test` (security invariants), `npm run build`, and `pytest backend/tests`.
   - Local Docker sandbox execution.
2. **Staging Environment**:
   - Push to `develop` branch triggers GitHub Actions.
   - Migrations applied to staging Supabase database.
   - Integration testing against live Supabase Auth and Redis instance.
3. **Production Deployment**:
   - Release tagged on `main`.
   - Production Docker images built and pushed to AWS ECR / Docker Hub.
   - Zero-downtime rolling update on ECS / Railway.

---

## 13. Verification & Quality Gates

Run the comprehensive test suites locally:

```bash
# 1. Run Security Invariants and Contract Tests
npm test

# 2. Run Oxlint Code Quality Check
npm run lint

# 3. TypeScript Typecheck & Production Build
npm run build
```

---

## 14. License

Confidential & Proprietary — VeriQuest Project Team.
