# Assets Management API

A REST API for managing organizational assets with secure authentication and role-based authorization.

## Tech Stack

* **Python 3.12+**
* **FastAPI** — REST API framework
* **PostgreSQL** — relational database
* **Redis** — access-token blacklisting
* **SQLAlchemy 2.0** — async ORM
* **Alembic** — database migrations
* **Pydantic v2** — request/response validation
* **PyJWT** — JWT access-token handling
* **pwdlib[argon2id]** — password hash handling
* **pytest** — testing
* **pytest-asyncio** — asynchronous test support
* **Ruff** — linting and formatting
* **uv** — dependency and project management
* **FastAPI Cloud** — deployment

---

## Project Structure

```text
assets-management-api/
├── alembic/
│   ├── env.py
│   └── versions/
│       └── ...
│
├── app/
│   ├── asset_tag/
│   │   └── ...
│   ├── core/
│   │   └── ...
│   ├── db/
│   │   └── ...
│   ├── dependencies/
│   │   └── ...
│   ├── exceptions/
│   │   └── ...
│   ├── models/
│   │   └── ...
│   ├── repositories/
│   │   └── ...
│   ├── routers/
│   │   └── ...
│   ├── schemas/
│   │   └── ...
│   ├── services/
│   │   └── ...
│   ├── validators/
│   │   └── ...
│   └── main.py
│
├── tests/
│   ├── unit/
│   │   └── ...
│   ├── api/
│   │   └── ...
│   └── integration/
│       └── ...
│
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml
├── README.md
└── uv.lock
```

### Directory Overview

| Directory            | Purpose                                                  |
| --------------------- | --------------------------------------------------------- |
| `app/asset_tag/`      | Asset tag generation and the race-safe counter table      |
| `app/core/`           | Application configuration and security utilities          |
| `app/db/`             | Database and Redis client configuration                    |
| `app/dependencies/`   | Authentication and authorization dependencies               |
| `app/exceptions/`     | Application exceptions and exception handlers               |
| `app/models/`         | SQLAlchemy models and enums                                  |
| `app/repositories/`   | Database access and persistence logic                        |
| `app/routers/`        | API route definitions                                        |
| `app/schemas/`        | Pydantic request and response schemas                        |
| `app/services/`       | Business and application logic                               |
| `app/validators/`     | Reusable input validators                                     |
| `tests/unit/`         | Unit tests                                                     |
| `tests/api/`          | API endpoint tests                                             |
| `tests/integration/`  | Integration and authentication flow tests                       |
| `alembic/`            | Database migrations                                              |


## Features

### Authentication

* User registration
* User login
* JWT-based access tokens
* HTTP-only refresh-token cookies
* Refresh-token rotation
* Refresh-token hashing before database storage
* Refresh-token family tracking
* Refresh-token reuse detection
* Logout current session (blacklists the current access token in Redis)
* Logout all sessions (bumps the user's token version, invalidating every outstanding access token)
* Change password
* Automatic session invalidation after password change
* Current-user endpoint (`/auth/me`)
* Inactive-user protection
* Password hashing and verification

### Authorization

* Role-based access control (RBAC)
* Support for `user` and `admin` roles
* Admin-only endpoints protected using a reusable `require_admin` dependency
* Unauthenticated requests return `401 Unauthorized`
* Role-gated collection endpoints return `403 Forbidden` when the user's role is insufficient
* Access to an existing resource without permission returns `404 Not Found` to hide resource existence (existence hiding)

### Assets

* Full CRUD on assets (create, list, retrieve, update, delete)
* Auto-generated, unique asset tags (`{COMPANY_PREFIX}-{TYPE}-{NUMBER}`), race-safe under concurrent creation
* Pagination (`page`, `size`, capped at 100 per page)
* Filtering by `type`, `status`, `assigned_to`, and `warranty_expiring_before` (filters combine with AND)
* Case-insensitive partial-match `search` across asset tag, serial number, and notes
* Sorting by `created_at`, `purchase_date`, or `asset_tag`, ascending or descending (`sort` / `order` query params; defaults to `created_at desc`)
* Status transition rules enforced from a single transition map (`in_stock` ↔ `assigned` ↔ `repair` ↔ `retired`, with `retired` terminal)
* Assign / unassign endpoints, restricted to active target users
* Delete blocked unless status is `in_stock` or `retired`
* Duplicate `asset_tag` / `serial_number` handled via DB unique constraints (409, not a racy pre-check)
* Status summary endpoint (counts by status via a single `GROUP BY` query)
* Regular users can only view assets assigned to them (`/assets/my`); admins have full visibility

---

## Project Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd assets-management-api
```

### 2. Install dependencies

This project uses `uv` for dependency management.

```bash
uv sync
```

### 3. Configure environment variables

Create a `.env` file from the example configuration:

```bash
cp .env.example .env
```

Update `.env` with your local configuration, including the database, Redis, and JWT settings.

Example:

```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/database_name
REDIS_URL=redis://localhost:6379/0

JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

ASSET_TAG_COMPANY_PREFIX=IL
```

### 4. Start PostgreSQL and Redis

Make sure PostgreSQL and Redis are running and the configured databases exist.

### 5. Run database migrations

Apply the latest Alembic migrations:

```bash
uv run alembic upgrade head
```
## Testing

The project uses `pytest` and `pytest-asyncio` for automated testing.

### Run all tests

```bash
uv run pytest
```

### Run all tests with verbose output

```bash
uv run pytest -v
```

### Run unit tests

```bash
uv run pytest tests/unit -v
```

### Run API tests

```bash
uv run pytest tests/api -v
```

### Run integration tests

```bash
uv run pytest tests/integration -v
```


### Run a specific test file

```bash
uv run pytest tests/unit/service/test_register.py -v
```

### Run a specific test file's specific test function

Use the `::` syntax to run a single test function:

```bash
uv run pytest tests/unit/service/test_register.py::test_valid_registration -v
```

## Code Coverage

### Install pytest-cov

```bash
uv add --dev pytest-cov
```

### Run overall test code coverage

```bash
uv run pytest --cov=app --cov-report=term-missing
```

### View code coverage HTML report

```bash
uv run pytest --cov=app --cov-report=html
```
This generates the HTML coverage report in:
htmlcov/index.html

Then open it in your browser

---

## Deployment

The application is deployed using **FastAPI Cloud**.

### Production API

**Deployment URL:** `https://assets-management-api-e53d626f.fastapicloud.dev/`

**API Documentation:**

* `https://assets-management-api-e53d626f.fastapicloud.dev/docs`
* `https://assets-management-api-e53d626f.fastapicloud.dev/redoc`