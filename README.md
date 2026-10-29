# Assets Management API

A REST API for managing organizational assets with secure authentication, role-based authorization, user management, and asset lifecycle management.

## Tech Stack

* **Python 3.12+**
* **FastAPI** — REST API framework
* **PostgreSQL** — relational database
* **Redis** — access-token blacklisting
* **SQLAlchemy 2.0** — asynchronous ORM
* **Alembic** — database migrations
* **Pydantic v2** — request/response validation
* **PyJWT** — JWT access-token handling
* **pwdlib[argon2]** — password hashing
* **pytest** — testing
* **pytest-asyncio** — asynchronous test support
* **Ruff** — linting and formatting
* **uv** — dependency and project management
* **FastAPI Cloud** — deployment

---

# Project Structure

```text
assets-management-api/
│
├── alembic/
│   ├── env.py
│   └── versions/
│       └── ...
│
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   ├── exception_handlers.py
│   │   ├── responses.py
│   │   ├── router.py
│   │   │
│   │   ├── health/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   │
│   │   └── v1/
│   │       ├── dependencies.py
│   │       ├── router.py
│   │       ├── responses.py
│   │       │
│   │       ├── schemas/
│   │       │   ├── assets.py
│   │       │   └── auth.py
│   │       │
│   │       └── endpoints/
│   │           ├── assets.py
│   │           ├── auth.py
│   │           └── users.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── security.py
│   │
│   ├── infrastructure/
│   │   ├── database.py
│   │   ├── lifespan.py
│   │   └── redis.py
│   │
│   ├── modules/
│   │   ├── asset/
│   │   │   ├── models.py
│   │   │   ├── repositories.py
│   │   │   ├── services.py
│   │   │   ├── exceptions.py
│   │   │   ├── tag/
│   │   │   │   ├── model.py
│   │   │   │   ├── repository.py
│   │   │   │   └── generator.py
│   │   │   └── validators/
│   │   │       └── serial_number.py
│   │   │
│   │   ├── auth/
│   │   │   ├── models.py
│   │   │   ├── repositories.py
│   │   │   ├── services.py
│   │   │   ├── exceptions.py
│   │   │   ├── jwt_blacklist.py
│   │   │   └── validators/
│   │   │       ├── full_name.py
│   │   │       └── password.py
│   │   │
│   │   └── user/
│   │       ├── models.py
│   │       ├── repositories.py
│   │       ├── services.py
│   │       └── exceptions.py
│   │
│   ├── shared/
│   │   ├── models/
│   │   │   ├── base.py
│   │   │   ├── enums.py
│   │   │   └── mixins.py
│   │   │
│   │   ├── schemas/
│   │   │   └── common.py
│   │   │
│   │   └── utils/
│   │       └── query.py
│   │
│   └── main.py
│
├── scripts/
│   └── seed.py
│
├── tests/
│   ├── config.py
│   ├── conftest.py
│   │
│   ├── api/
│   │   ├── conftest.py
│   │   └── v1/
│   │       ├── test_auth.py
│   │       ├── test_users.py
│   │       └── test_assets.py
│   │
│   └── modules/
│       ├── conftest.py
│       ├── auth/
│       │   └── test_services.py
│       ├── user/
│       │   └── test_services.py
│       └── asset/
│           └── test_services.py
│
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml
├── README.md
└── uv.lock
```

## Directory Overview

| Directory/File           | Purpose                                                                        |
| ------------------------ | ------------------------------------------------------------------------------ |
| `app/api/`               | API routing, shared API dependencies, responses, and exception handlers        |
| `app/api/health/`        | Health-check endpoint, schemas, and health-check service                       |
| `app/api/v1/`            | Version 1 API routes, schemas, dependencies, and response definitions          |
| `app/api/v1/endpoints/`  | Endpoint implementations for authentication, users, and assets                 |
| `app/api/v1/schemas/`    | Pydantic request and response schemas                                          |
| `app/core/`              | Application configuration, core exceptions, and security utilities             |
| `app/infrastructure/`    | Database, Redis, and application lifespan configuration                        |
| `app/modules/auth/`      | Authentication, JWT, refresh-token, session, and authentication business logic |
| `app/modules/user/`      | User models, repositories, services, and user-related exceptions               |
| `app/modules/asset/`     | Asset models, repositories, services, and asset business logic                 |
| `app/modules/asset/tag/` | Asset-tag generation and counter management                                    |
| `app/shared/models/`     | Shared database models, enums, base classes, and mixins                        |
| `app/shared/schemas/`    | Shared Pydantic schemas                                                        |
| `app/shared/utils/`      | Shared utility functions such as query helpers                                 |
| `scripts/`               | Standalone project scripts                                                     |
| `scripts/seed.py`        | Seeds the database with initial development data                               |
| `tests/`                 | Test configuration and test suites                                             |
| `tests/config.py`        | Test-specific configuration, including the test database configuration         |
| `tests/api/`             | API endpoint/integration tests                                                 |
| `tests/modules/`         | Module/service-level tests                                                     |
| `alembic/`               | Database migration configuration and migration files                           |

---

# Features

## Authentication

* User registration
* Case-insensitive email uniqueness
* Password validation
* Argon2 password hashing
* User login
* JWT-based access tokens
* HTTP-only refresh-token cookies
* Refresh-token hashing before database storage
* Refresh-token rotation
* Refresh-token family tracking
* Refresh-token reuse detection
* Logout of the current session
* Access-token family invalidation using Redis
* Logout of all sessions
* Token-version based access-token invalidation
* Change password
* Automatic session invalidation after password change
* Inactive-user protection
* Current-user endpoint

### Authentication Endpoints

| Method  | Endpoint                           | Description                                           |
| ------- | ---------------------------------- | ----------------------------------------------------- |
| `POST`  | `/api/v1/auth/register`            | Register a new user                                   |
| `POST`  | `/api/v1/auth/login`               | Authenticate and issue access/refresh tokens          |
| `POST`  | `/api/v1/auth/refresh`             | Rotate the refresh token and issue a new access token |
| `POST`  | `/api/v1/auth/logout`              | Logout the current session                            |
| `POST`  | `/api/v1/auth/logout-all`          | Invalidate all user sessions                          |

Access tokens contain the user's identity, role, token version, JWT ID, issued-at time, and expiration time.

Refresh tokens are stored as hashes and rotated when refreshed. Reuse of a revoked refresh token triggers refresh-token reuse handling.

---

# Authorization

* Role-based access control (RBAC)
* Support for `user` and `admin` roles
* Reusable `require_admin` dependency
* Admin-only collection endpoints
* Unauthenticated requests return `401 Unauthorized`
* Insufficient permissions return `403 Forbidden`
* Resource access can return `404 Not Found` where resource existence should be hidden

---

# Assets

* Full CRUD operations
* Automatically generated asset tags
* Race-safe asset-tag generation
* Unique `asset_tag` and `serial_number` constraints
* Pagination
* Filtering
* Searching
* Sorting
* Asset assignment and unassignment
* Asset status transitions
* Asset statistics
* Warranty-expiry filtering
* Role-based asset visibility

## Asset Tags

Asset tags follow the format:

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

Asset-tag numbers are maintained using a dedicated counter table to support race-safe concurrent asset creation.

## Asset Types

```text
laptop
monitor
phone
accessory
```

## Asset Statuses

```text
in_stock
assigned
repair
retired
```

Status transitions are controlled by a centralized transition map, with `retired` treated as a terminal state.

## Asset Endpoints

| Method   | Endpoint                       | Description                              |
| -------- | ------------------------------ | ---------------------------------------- |
| `POST`   | `/api/v1/assets`               | Create an asset                          |
| `GET`    | `/api/v1/assets`               | List assets                              |
| `GET`    | `/api/v1/assets/stats`         | Get asset statistics                     |
| `GET`    | `/api/v1/assets/{id}`          | Get an asset by ID                       |
| `PATCH`  | `/api/v1/assets/{id}`          | Update an asset                          |
| `DELETE` | `/api/v1/assets/{id}`          | Delete an asset                          |
| `POST`   | `/api/v1/assets/{id}/assign`   | Assign an asset to a user                |
| `POST`   | `/api/v1/assets/{id}/unassign` | Unassign an asset                        |
| `POST`   | `/api/v1/assets/{id}/status`   | Change asset status                      |
| `GET`    | `/api/v1/users/me/assets`      | List assets assigned to the current user |

## Asset Listing

The asset list supports:

* `page`
* `size`
* `type`
* `status`
* `assigned_to`
* `warranty_expiring_before`
* `search`
* `sort`
* `order`

Filters are combined using `AND`.

Search performs a case-insensitive partial match against:

* asset tag
* serial number
* notes

Supported sort fields include:

* `created_at`
* `purchase_date`
* `asset_tag`

The default ordering is:

```text
created_at desc
```

Pagination defaults to 20 items per page and supports a maximum page size of 100.

Duplicate asset tags and serial numbers are handled using database unique constraints and returned as `409 Conflict` responses.

---

# Users

* Admin user listing
* Case-insensitive user search
* Pagination
* Current-user information
* Current-user asset listing
* Password change

## User Endpoints

| Method  | Endpoint                           | Access        | Description                         |
| ------- | ---------------------------------- | ------------- | ----------------------------------- |
| `GET`   | `/api/v1/users/me`                 | Authenticated | Get current user                    |
| `PATCH` | `/api/v1/users/me/password`        | Authenticated | Change password                     |
| `GET`   | `/api/v1/users`                    | Admin         | List users                          |
| `GET`   | `/api/v1/users/me/assets`          | Authenticated | List current user's assigned assets |

The admin user list supports:

* `page`
* `size`
* `search`

The response exposes user information without sensitive fields such as password hashes.

---

# API Response Format

## Successful Response

Successful non-paginated responses use:

```json
{
  "data": {}
}
```

## Paginated Response

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

The paginated endpoints are:

* `GET /api/v1/assets`
* `GET /api/v1/users`
* `GET /api/v1/users/me/assets`

## Error Response

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

Validation errors can include additional `details`:

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

* `400 Bad Request`
* `401 Unauthorized`
* `403 Forbidden`
* `404 Not Found`
* `409 Conflict`
* `422 Unprocessable Content`
* `500 Internal Server Error`
* `503 Service Unavailable`

---

# Project Setup

## 1. Clone the Repository

```bash
git clone <repository-url>
cd assets-management-api
```

## 2. Install Dependencies

This project uses `uv` for dependency and project management.

```bash
uv sync
```

## 3. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Example configuration:

```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/database_name
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
ASSET_TAG_COMPANY_PREFIX=IL
```

## 4. Start PostgreSQL and Redis

Make sure PostgreSQL and Redis are running and the configured database exists.

## 5. Run Database Migrations

```bash
uv run alembic upgrade head
```

## 6. Seed Development Data

The project includes a database seeding script:

```bash
uv run python scripts/seed.py
```

The seed script populates the database with the initial development data required by the application.

---

# Running the Application

Start the development server:

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

---

# Testing

The project uses `pytest` and `pytest-asyncio`.

The test suite uses a dedicated test configuration defined in:

```text
tests/config.py
```

This keeps test-database configuration separate from the application's runtime configuration.

## Run All Tests

```bash
uv run pytest
```

## Verbose Output

```bash
uv run pytest -v
```

## API Tests

```bash
uv run pytest tests/api -v
```

## Module Tests

```bash
uv run pytest tests/modules -v
```

## Authentication Tests

```bash
uv run pytest tests/api/v1/test_auth.py -v
```

## User Tests

```bash
uv run pytest tests/api/v1/test_users.py -v
```

## Asset Tests

```bash
uv run pytest tests/api/v1/test_assets.py -v
```

## Specific Test File

```bash
uv run pytest tests/modules/auth/test_services.py -v
```

## Specific Test

```bash
uv run pytest \
  tests/modules/auth/test_services.py::test_valid_registration \
  -v
```

## Run Tests by Keyword

```bash
uv run pytest tests/api/v1/test_assets.py \
  -k "duplicate_serial or duplicate_asset_tag" \
  -v
```

---

# Code Coverage

`pytest-cov` can be used to generate coverage reports.

Install it as a development dependency:

```bash
uv add --dev pytest-cov
```

## Terminal Coverage

```bash
uv run pytest --cov=app --cov-report=term-missing
```

## HTML Coverage

```bash
uv run pytest --cov=app --cov-report=html
```

The HTML report will be available at:

```text
htmlcov/index.html
```

---

# Database Migrations

## Create a Migration

```bash
uv run alembic revision --autogenerate -m "describe migration"
```

## Apply Migrations

```bash
uv run alembic upgrade head
```

## Downgrade One Migration

```bash
uv run alembic downgrade -1
```

## Check Current Migration

```bash
uv run alembic current
```

---

# Code Quality

## Lint

```bash
uv run ruff check .
```

## Format

```bash
uv run ruff format .
```

## Check Formatting

```bash
uv run ruff format --check .
```

---

# Deployment

The application is deployed using **FastAPI Cloud**.

## Production API

```text
https://assets-management-api-e53d626f.fastapicloud.dev/
```

## API Documentation

Swagger UI:

```text
https://assets-management-api-e53d626f.fastapicloud.dev/docs
```

ReDoc:

```text
https://assets-management-api-e53d626f.fastapicloud.dev/redoc
```
