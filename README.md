# Assets Management API

A REST API for managing organizational assets with secure authentication and role-based authorization.

## Tech Stack

* **Python 3.12+**
* **FastAPI** — REST API framework
* **PostgreSQL** — relational database
* **SQLAlchemy 2.0** — async ORM
* **Alembic** — database migrations
* **Pydantic v2** — request/response validation
* **PyJWT** — JWT access-token handling
* **passlib[argon2id]** - Password hash handling
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

| Directory            | Purpose                                          |
| -------------------- | ------------------------------------------------ |
| `app/core/`          | Application configuration and security utilities |
| `app/db/`            | Database configuration and SQLAlchemy setup      |
| `app/dependencies/`  | Authentication and authorization dependencies    |
| `app/exceptions/`    | Application exceptions and exception handlers    |
| `app/models/`        | SQLAlchemy models and enums                      |
| `app/repositories/`  | Database access and persistence logic            |
| `app/routers/`       | API route definitions                            |
| `app/schemas/`       | Pydantic request and response schemas            |
| `app/services/`      | Business and application logic                   |
| `app/validators/`    | Reusable input validators                        |
| `tests/unit/`        | Unit tests                                       |
| `tests/api/`         | API endpoint tests                               |
| `tests/integration/` | Integration and authentication flow tests        |
| `alembic/`           | Database migrations                              |


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
* Logout current session
* Logout all sessions
* Change password
* Automatic session invalidation after password change
* Current-user endpoint (`/auth/me`)
* Inactive-user protection
* Password hashing and verification

### Authorization

* Role-based access control (RBAC)
* Support for `user` and `admin` roles
* Protected endpoints using a reusable `require_role` dependency
* Unauthenticated requests return `401 Unauthorized`
* Role-gated collection endpoints return `403 Forbidden` when the user's role is insufficient
* Access to an existing resource without permission returns `404 Not Found` to hide resource existence (existence hiding)


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

Update `.env` with your local configuration, including the database connection and JWT settings.

Example:

```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/database_name
TEST_DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/test_databse_name

JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 4. Start PostgreSQL

Make sure PostgreSQL is running and the configured databases exist.

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

```
htmlcov/index.html
```
Then open it in your browser

---

## Deployment

The application is deployed using **FastAPI Cloud**.

### Production API

**Deployment URL:** `https://assets-management-api-e53d626f.fastapicloud.dev/`

**API Documentation:**

* `https://assets-management-api-e53d626f.fastapicloud.dev/docs`
* `https://assets-management-api-e53d626f.fastapicloud.dev/redoc`


