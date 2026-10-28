# Assets Management API

A REST API for managing organizational assets with secure authentication, role-based authorization, user management, asset lifecycle management, assignment history, background processing, CSV exports, and S3-based asset file storage.

## Features

- Secure authentication and session management
- Role-based access control (RBAC)
- User management and asset visibility rules
- Asset CRUD operations, search, filtering, sorting, and pagination
- Race-safe asset-tag generation
- Asset assignment, unassignment, and status transitions
- Asset assignment history
- Warranty-expiry filtering and asset statistics
- Asynchronous CSV export jobs
- Celery background workers and scheduled tasks
- S3-compatible asset file storage using presigned URLs
- Automatic cleanup of expired pending uploads
- Consistent API responses and exception handling
- Automated API and service-level tests
- Docker Compose development environment
- Database migrations managed by Alembic

## Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.12+ | Programming language |
| FastAPI | REST API framework |
| Uvicorn / ASGI | Application server and asynchronous interface |
| PostgreSQL | Relational database |
| SQLAlchemy 2.0 | Asynchronous ORM and database access |
| Alembic | Database schema migrations |
| Pydantic v2 | Request validation and response schemas |
| PyJWT | JWT access-token handling |
| pwdlib[argon2] | Password hashing |
| Redis | Token-family invalidation and Celery infrastructure |
| Celery | Background task processing |
| Celery Beat | Scheduled task execution |
| boto3 | S3-compatible object storage integration |
| pytest | Automated testing |
| pytest-asyncio | Asynchronous test support |
| HTTPX | API integration testing |
| Moto | S3 mocking for tests |
| Ruff | Linting and formatting |
| uv | Dependency and project management |
| Docker Compose | Local development infrastructure |
| FastAPI Cloud | Production API hosting |

## Architecture

The application separates API handling, business logic, persistence, and infrastructure responsibilities.

```text
Client
  |
  v
FastAPI
  |
  +-- API routers and dependencies
  |
  +-- Authentication and authorization
  |
  +-- Module services
  |     |
  |     +-- Repositories
  |     |
  |     +-- SQLAlchemy AsyncSession
  |              |
  |              v
  |          PostgreSQL
  |
  +-- Redis
  |
  +-- Celery task queue
  |     |
  |     +-- Celery workers
  |     |
  |     +-- Celery Beat
  |
  +-- S3-compatible object storage
```

### Architectural responsibilities

- **API layer:** Routes HTTP requests, validates input, applies dependencies, and constructs responses.
- **Service layer:** Implements business rules, authorization decisions, and transaction workflows.
- **Repository layer:** Encapsulates database queries and persistence operations.
- **Infrastructure layer:** Configures the database, Redis, Celery, object storage, and application lifecycle.
- **Background workers:** Execute long-running and scheduled tasks outside the request-response cycle.
- **Object storage:** Stores uploaded files independently of the API server.

## Project Structure

The following is a high-level view of the project. Individual modules may contain additional files as the application evolves.

```text
assets-management-api/
├── alembic/
│   ├── env.py
│   └── versions/
│
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   ├── exception_handlers.py
│   │   ├── responses.py
│   │   ├── router.py
│   │   ├── health/
│   │   └── v1/
│   │       ├── dependencies.py
│   │       ├── router.py
│   │       ├── schemas/
│   │       └── endpoints/
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── security.py
│   │
│   ├── infrastructure/
│   │   ├── database.py
│   │   ├── lifespan.py
│   │   ├── redis.py
│   │   ├── celery/
│   │   └── storage/
│   │
│   ├── modules/
│   │   ├── asset/
│   │   │   ├── models.py
│   │   │   ├── repositories.py
│   │   │   ├── services.py
│   │   │   ├── exceptions.py
│   │   │   ├── tag/
│   │   │   ├── validators/
│   │   │   ├── csv_export/
│   │   │   └── files/
│   │   │
│   │   ├── asset_assignment/
│   │   ├── asset_files/
│   │   ├── auth/
│   │   └── user/
│   │
│   ├── shared/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── utils/
│   │
│   └── main.py
│
├── scripts/
│   └── seed.py
│
├── tests/
│   ├── config.py
│   ├── conftest.py
│   ├── api/
│   └── modules/
│
├── .env.example
├── .gitignore
├── alembic.ini
├── compose.yaml
├── Dockerfile
├── pyproject.toml
├── README.md
└── uv.lock
```

### Directory responsibilities

| Directory | Purpose |
|---|---|
| `app/api/` | Shared API infrastructure, routers, response handling, and exception handlers |
| `app/api/health/` | Health-check endpoint and related logic |
| `app/api/v1/` | Versioned API routes, dependencies, schemas, and endpoints |
| `app/core/` | Configuration, security utilities, and core exceptions |
| `app/infrastructure/` | Database, Redis, Celery, storage, and lifecycle configuration |
| `app/modules/asset/` | Asset business logic, repositories, models, tagging, and export functionality |
| `app/modules/asset_assignment/` | Asset assignment-history functionality, where separated into its own module |
| `app/modules/asset_files/` | Asset file metadata and file-management workflows |
| `app/modules/auth/` | Authentication, JWTs, refresh-token rotation, and session invalidation |
| `app/modules/user/` | User models, repositories, services, and user-related business logic |
| `app/shared/models/` | Shared SQLAlchemy models, enums, and mixins |
| `app/shared/schemas/` | Reusable Pydantic schemas |
| `app/shared/utils/` | Shared utilities and query helpers |
| `scripts/` | Development and database seeding scripts |
| `tests/api/` | API integration tests |
| `tests/modules/` | Service and unit tests |
| `alembic/` | Database migrations |

## Authentication

The API supports secure authentication and session management.

### Features

- User registration
- Case-insensitive email uniqueness
- Password validation and Argon2 hashing
- User login
- JWT access tokens
- HTTP-only refresh-token cookies
- Hashed refresh-token storage
- Refresh-token rotation
- Refresh-token family tracking
- Refresh-token reuse detection
- Logout of the current session
- Logout of all sessions
- Redis-based access-token family invalidation
- Token-version-based access-token invalidation
- Password changes with session invalidation
- Inactive-user protection
- Current-user information

Access tokens contain identity and authorization-related claims, including the user's role, token version, JWT ID, issued-at time, and expiration time.

Refresh tokens are rotated during refresh operations. Reuse of a revoked token triggers reuse handling for the associated token family.

### Authentication endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register a user |
| `POST` | `/api/v1/auth/login` | Authenticate and issue tokens |
| `POST` | `/api/v1/auth/refresh` | Rotate the refresh token |
| `POST` | `/api/v1/auth/logout` | Log out the current session |
| `POST` | `/api/v1/auth/logout-all` | Invalidate all user sessions |
| `GET` | `/api/v1/users/me` | Retrieve the authenticated user |
| `PATCH` | `/api/v1/users/me/password` | Change the current user's password |

## Authorization

The API uses role-based access control (RBAC).

Supported roles:

- `user`
- `admin`

Authorization is enforced through reusable dependencies and service-level business rules.

- Unauthenticated requests return `401 Unauthorized`.
- Authenticated users without the required permissions receive `403 Forbidden`.
- `404 Not Found` may be used when resource existence should be concealed.
- Resource-level authorization prevents users from accessing assets belonging to other users when they lack permission.

Admin-only operations include user administration, asset management operations restricted to administrators, and privileged export and file-management workflows.

## Asset Management

The API supports the asset lifecycle from creation through assignment, repair, and retirement.

### Features

- Create, retrieve, update, and delete assets
- Automatically generated asset tags
- Race-safe asset-tag generation
- Unique asset-tag and serial-number constraints
- Pagination
- Filtering, searching, and sorting
- Asset assignment and unassignment
- Controlled status transitions
- Asset statistics
- Warranty-expiry filtering
- Role-based asset visibility
- Current-user assigned-asset listing
- Assignment-history tracking

### Asset types

```text
laptop
monitor
phone
accessory
```

### Asset statuses

```text
in_stock
assigned
repair
retired
```

Status transitions are validated through a centralized transition map. The `retired` status is treated as terminal.

### Asset tags

Asset tags follow this format:

```text
{COMPANY_PREFIX}-{TYPE}-{NUMBER}
```

Examples:

```text
IL-LAP-0001
IL-MON-0001
IL-PHN-0001
IL-ACC-0001
```

A dedicated counter table maintains tag numbers by asset type. Database transactions and appropriate locking protect tag generation against concurrent asset creation.

### Asset endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/assets` | Create an asset |
| `GET` | `/api/v1/assets` | List and filter assets |
| `GET` | `/api/v1/assets/stats` | Retrieve asset statistics |
| `GET` | `/api/v1/assets/{id}` | Retrieve an asset |
| `PATCH` | `/api/v1/assets/{id}` | Update an asset |
| `DELETE` | `/api/v1/assets/{id}` | Delete an asset |
| `POST` | `/api/v1/assets/{id}/assign` | Assign an asset |
| `POST` | `/api/v1/assets/{id}/unassign` | Unassign an asset |
| `POST` | `/api/v1/assets/{id}/status` | Change an asset's status |
| `GET` | `/api/v1/users/me/assets` | List the current user's assigned assets |

### Asset listing

The asset list supports the following query parameters:

- `page`
- `size`
- `type`
- `status`
- `assigned_to`
- `warranty_expiring_before`
- `search`
- `sort`
- `order`

Filters are combined using `AND`.

Search performs a case-insensitive partial match against:

- Asset tag
- Serial number
- Notes

Supported sort fields include `created_at`, `purchase_date`, and `asset_tag`.

Default ordering:

```text
created_at desc
```

Pagination defaults to 20 items per page and allows a maximum page size of 100.

Duplicate asset tags and serial numbers are protected by database unique constraints and are returned as `409 Conflict` responses.

## Asset Assignment History

Assignment history records when an asset is assigned to a user and when it is returned or unassigned.

History records can capture:

- Asset and user references
- The administrator who performed the assignment
- The administrator who performed the unassignment
- Assignment timestamp
- Return or unassignment timestamp

### Consistency and concurrency

- Assignment history is updated in the same database transaction as the corresponding asset operation.
- A partial unique index prevents multiple open assignment records for the same asset.
- Appropriate row locking helps prevent conflicting concurrent assignments.
- Existing assignments can be backfilled during migration from the asset's current assignment state.

History endpoints should enforce administrator or self-access permissions according to the requested resource.

## Background Jobs and CSV Export

The API uses Celery to process background tasks outside the HTTP request-response cycle.

### Components

- **Redis broker:** Carries queued task messages.
- **Celery worker:** Executes queued tasks.
- **Celery Beat:** Schedules periodic tasks.
- **PostgreSQL:** Stores persistent application records and background-job metadata.

### CSV export

CSV export supports an asynchronous workflow:

1. An authorized client submits an export request.
2. The API creates a background job and returns an accepted response.
3. A Celery worker queries the applicable asset records and generates the CSV file.
4. The job's status and export metadata are updated.
5. The client checks the job status and retrieves the completed export using the applicable download endpoint.

Export functionality includes the asset data, applicable filters, and CSV column definitions.

### CSV security

Exported user-controlled text is sanitized against CSV formula injection. Values beginning with spreadsheet formula characters, such as `=`, `+`, `-`, or `@`, require careful handling before being written to a CSV file.

CSV quoting alone is not sufficient to prevent spreadsheet formula execution.

### Scheduled tasks

Celery Beat is configured for scheduled background work, including warranty-related processing, weekly summaries, and expired pending asset-file cleanup.

The exact schedule is configured in the application's Celery settings.

## Asset File Storage

The asset file feature uses S3-compatible object storage and presigned URLs.

Files are uploaded directly to object storage rather than being streamed through the API server. This reduces application-server bandwidth and memory overhead.

### Supported file types

| Content type | Format |
|---|---|
| `application/pdf` | PDF |
| `image/jpeg` | JPEG |
| `image/png` | PNG |
| `image/webp` | WebP |

Maximum upload size: **5 MB**.

### Upload workflow

1. An authorized administrator requests a presigned upload URL.
2. The API validates the filename, content type, and file size.
3. The API creates file metadata and returns the presigned PUT URL and file identifier.
4. The client uploads the file directly to S3-compatible storage.
5. The storage service can notify the configured event handler when an object is created.
6. The file metadata can be checked against the stored object.

Object keys follow this general pattern:

```text
assets/{asset_id}/{uuid}-{filename}
```

### File access and deletion

- Administrators and users assigned to the relevant asset can access files according to authorization rules.
- Presigned download URLs are short-lived.
- The configured download URL lifetime is 15 minutes.
- Administrators can delete asset files.
- Pending uploads that remain incomplete beyond the configured expiry period can be cleaned up by a scheduled task.

The file metadata and object storage are separate systems. Deletion and cleanup workflows must account for failures in either the database or object storage, with retries for unsuccessful object deletion.

### Local S3 testing

The storage integration can be tested using Moto for isolated tests and a local S3-compatible environment for integration workflows. The local environment should be configured with the correct endpoint, bucket, credentials, and region.

## API Response Format

Use the application's response schemas as the source of truth for the exact response structure.

### Successful response

A non-paginated response uses the application's standard success envelope. A simplified example is:

```json
{
  "data": {}
}
```

### Paginated response

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "size": 20,
    "total_items": 100,
    "total_pages": 5
  }
}
```

Paginated resources include asset and user listings and the current user's assigned-asset listing, where pagination is supported by the endpoint.

### Error response

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

Validation errors may include additional details:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": []
  }
}
```

Common HTTP status codes include:

| Status | Meaning |
|---|---|
| `400` | Bad Request |
| `401` | Unauthorized |
| `403` | Forbidden |
| `404` | Not Found |
| `409` | Conflict |
| `422` | Unprocessable Content |
| `500` | Internal Server Error |
| `503` | Service Unavailable |

Refer to the configured response schemas for the complete envelope and metadata fields.

## Project Setup

### Prerequisites

Install the following tools:

- Python 3.12 or later
- `uv`
- Docker and Docker Compose

The Docker Compose environment provides the local PostgreSQL and Redis services and the application services used for development.

### 1. Clone the repository

```bash
git clone <repository-url>
cd assets-management-api
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment variables

Create a local environment file:

```bash
cp .env.example .env
```

Configure the required settings for your environment. Example values:

```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/assets_management_dev
REDIS_URL=redis://localhost:6379/0

JWT_SECRET_KEY=replace-with-a-secure-secret-of-at-least-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

ASSET_TAG_COMPANY_PREFIX=IL
```

These are illustrative values, not production credentials. Use a securely generated JWT secret and never commit real secrets to Git.

Additional configuration may be required for email, Celery, S3-compatible storage, and test execution.

**Important:** When running the application inside Docker Compose, use the Compose service hostname for PostgreSQL, for example:

```env
DATABASE_URL=postgresql+asyncpg://username:password@db:5432/assets_management_dev
```

When running the application directly on your host, use the host-accessible database address and port configured in Compose.

### 4. Start the local environment

Start the services defined in `compose.yaml`:

```bash
docker compose up -d --build
```

Check the service status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat
```

The local Compose environment includes services for PostgreSQL, Redis, database migrations, the API, Celery workers, and Celery Beat.

### 5. Apply database migrations

When using the Compose migration service:

```bash
docker compose run --rm migrate
```

Alternatively, when running the application directly in your local environment:

```bash
uv run alembic upgrade head
```

Use the method appropriate to your configured database connection. Do not accidentally apply migrations to a production database while working locally.

### 6. Seed development data

```bash
uv run python scripts/seed.py
```

Run this script only against the intended development database.

## Running the Application

### Local development server

If your environment variables point to a running, accessible PostgreSQL and Redis instance:

```bash
uv run fastapi dev app/main.py
```

Application:

```text
http://localhost:8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

### Docker Compose

When running the API in Docker Compose, use the API service's published port from `compose.yaml` to access the application.

Useful commands:

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat
docker compose down
```

`docker compose down` stops and removes the Compose containers and network. Persistent data volumes are not removed unless explicitly requested with an appropriate volume-removal command.

## Testing

The project uses pytest, pytest-asyncio, and HTTPX for automated tests.

- **API integration tests:** Exercise HTTP endpoints, dependency overrides, authorization, request validation, and response behavior.
- **Module/service tests:** Test business logic independently, often using mocks for repositories and external services.
- **Database tests:** Validate persistence behavior, constraints, and transactional workflows.
- **Storage tests:** Use S3 mocks or a local S3-compatible environment to validate storage integration.

Test configuration is maintained separately from runtime application configuration.

### Run all tests

```bash
uv run pytest
```

### Verbose output

```bash
uv run pytest -v
```

### API tests

```bash
uv run pytest tests/api -v
```

### Module tests

```bash
uv run pytest tests/modules -v
```

### Run a specific test file

```bash
uv run pytest tests/modules/auth/test_services.py -v
```

### Run a specific test

```bash
uv run pytest \
  tests/modules/auth/test_services.py::test_valid_registration \
  -v
```

### Run tests by keyword

```bash
uv run pytest tests/api/v1/test_assets.py \
  -k "duplicate_serial or duplicate_asset_tag" \
  -v
```

### Test database configuration

The test suite uses `tests/config.py` and the test fixtures in `tests/conftest.py` to configure test execution.

Always verify that test settings point to a dedicated test database before running tests that create, update, or delete database records.

## Code Coverage

Install coverage support as a development dependency if it is not already installed:

```bash
uv add --dev pytest-cov
```

### Terminal report

```bash
uv run pytest --cov=app --cov-report=term-missing
```

### HTML report

```bash
uv run pytest --cov=app --cov-report=html
```

The HTML report is generated at:

```text
htmlcov/index.html
```

## Database Migrations

Alembic manages database schema changes.

### Create a migration

```bash
uv run alembic revision --autogenerate -m "describe migration"
```

Review autogenerated migrations before applying them. Autogeneration does not guarantee that every schema change is detected or represented correctly.

### Apply migrations

```bash
uv run alembic upgrade head
```

### Check the current revision

```bash
uv run alembic current
```

### Inspect migration history

```bash
uv run alembic history
```

### Downgrade one revision

```bash
uv run alembic downgrade -1
```

Run migration commands against the intended database. Review destructive changes and downgrade behavior before applying migrations to important environments.

## Code Quality

### Lint

```bash
uv run ruff check .
```

### Format

```bash
uv run ruff format .
```

### Check formatting without modifying files

```bash
uv run ruff format --check .
```

## Deployment[PHASE-1]

The existing production API is hosted on FastAPI Cloud.

### Production API

https://ams-api.fieldops.shop

### API documentation

- Swagger UI: https://ams-api.fieldops.shop/docs
- ReDoc: https://ams-api.fieldops.shop/redoc


Production deployment requires appropriate configuration for secrets, database connectivity, Redis, migrations, CORS, and any enabled background workers or storage integrations.

## Security Considerations

- Keep secrets and production credentials out of source control.
- Use a strong JWT signing secret.
- Store passwords using Argon2 password hashing.
- Store refresh-token hashes rather than plaintext refresh tokens.
- Use HTTP-only cookies for refresh tokens and configure secure cookie settings appropriately for the environment.
- Enforce authorization at the resource level, not just at the route level.
- Validate uploaded file types and sizes on the server.
- Keep presigned URLs short-lived.
- Treat CSV exports as potentially dangerous when opened in spreadsheet applications.
- Run automated tests against a dedicated test database.
- Review migrations before production deployment.
- Ensure failed object-storage cleanup operations can be retried.


