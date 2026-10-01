import asyncio
from datetime import date

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.infrastructure.database import AsyncSessionLocal, engine
from app.modules.asset.models import Asset
from app.modules.asset.tag.model import AssetTagCounter
from app.modules.auth.models import RefreshToken  # noqa: F401
from app.modules.user.models import User
from app.shared.models.enums import AssetStatus, AssetType, UserRole

COMPANY_PREFIX = settings.ASSET_TAG_COMPANY_PREFIX

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = settings.SEED_USER_PASSWORD
ADMIN_NAME = "Admin User"

USERS = [
    {
        "email": "user1@example.com",
        "password": settings.SEED_USER_PASSWORD,
        "full_name": "User One",
    },
    {
        "email": "user2@example.com",
        "password": settings.SEED_USER_PASSWORD,
        "full_name": "User Two",
    },
    {
        "email": "user3@example.com",
        "password": settings.SEED_USER_PASSWORD,
        "full_name": "User Three",
    },
]


ASSET_SEED_DATA = [
    # Laptops
    {
        "type": AssetType.LAPTOP,
        "status": AssetStatus.IN_STOCK,
        "serial_number": "SN-LAP-0001",
        "purchase_date": date(2026, 1, 10),
        "warranty_expiry": date(2029, 1, 10),
        "notes": "Dell Latitude laptop",
    },
    {
        "type": AssetType.LAPTOP,
        "status": AssetStatus.ASSIGNED,
        "serial_number": "SN-LAP-0002",
        "purchase_date": date(2026, 1, 11),
        "warranty_expiry": date(2029, 1, 11),
        "notes": "Lenovo ThinkPad laptop",
    },
    {
        "type": AssetType.LAPTOP,
        "status": AssetStatus.ASSIGNED,
        "serial_number": "SN-LAP-0003",
        "purchase_date": date(2026, 1, 12),
        "warranty_expiry": date(2029, 1, 12),
        "notes": "HP ProBook laptop",
    },
    {
        "type": AssetType.LAPTOP,
        "status": AssetStatus.REPAIR,
        "serial_number": "SN-LAP-0004",
        "purchase_date": date(2025, 8, 15),
        "warranty_expiry": date(2028, 8, 15),
        "notes": "Laptop sent for keyboard repair",
    },
    {
        "type": AssetType.LAPTOP,
        "status": AssetStatus.IN_STOCK,
        "serial_number": "SN-LAP-0005",
        "purchase_date": date(2022, 4, 20),
        "warranty_expiry": date(2025, 4, 20),
        "notes": "Retired laptop",
    },
    # Monitors
    {
        "type": AssetType.MONITOR,
        "status": AssetStatus.IN_STOCK,
        "serial_number": "SN-MON-0001",
        "purchase_date": date(2026, 2, 1),
        "warranty_expiry": date(2029, 2, 1),
        "notes": "24-inch IPS monitor",
    },
    {
        "type": AssetType.MONITOR,
        "status": AssetStatus.ASSIGNED,
        "serial_number": "SN-MON-0002",
        "purchase_date": date(2026, 2, 2),
        "warranty_expiry": date(2029, 2, 2),
        "notes": "27-inch QHD monitor",
    },
    {
        "type": AssetType.MONITOR,
        "status": AssetStatus.ASSIGNED,
        "serial_number": "SN-MON-0003",
        "purchase_date": date(2026, 2, 3),
        "warranty_expiry": date(2029, 2, 3),
        "notes": "27-inch IPS monitor",
    },
    {
        "type": AssetType.MONITOR,
        "status": AssetStatus.REPAIR,
        "serial_number": "SN-MON-0004",
        "purchase_date": date(2025, 5, 10),
        "warranty_expiry": date(2028, 5, 10),
        "notes": "Monitor with display issue",
    },
    {
        "type": AssetType.MONITOR,
        "status": AssetStatus.IN_STOCK,
        "serial_number": "SN-MON-0005",
        "purchase_date": date(2021, 3, 15),
        "warranty_expiry": date(2024, 3, 15),
        "notes": "Retired monitor",
    },
    # Phones
    {
        "type": AssetType.PHONE,
        "status": AssetStatus.IN_STOCK,
        "serial_number": "SN-PHN-0001",
        "purchase_date": date(2026, 3, 1),
        "warranty_expiry": date(2028, 3, 1),
        "notes": "Company mobile phone",
    },
    {
        "type": AssetType.PHONE,
        "status": AssetStatus.ASSIGNED,
        "serial_number": "SN-PHN-0002",
        "purchase_date": date(2026, 3, 2),
        "warranty_expiry": date(2028, 3, 2),
        "notes": "Company mobile phone",
    },
    {
        "type": AssetType.PHONE,
        "status": AssetStatus.ASSIGNED,
        "serial_number": "SN-PHN-0003",
        "purchase_date": date(2026, 3, 3),
        "warranty_expiry": date(2028, 3, 3),
        "notes": "Company mobile phone",
    },
    {
        "type": AssetType.PHONE,
        "status": AssetStatus.REPAIR,
        "serial_number": "SN-PHN-0004",
        "purchase_date": date(2025, 7, 1),
        "warranty_expiry": date(2027, 7, 1),
        "notes": "Phone with battery issue",
    },
    {
        "type": AssetType.PHONE,
        "status": AssetStatus.IN_STOCK,
        "serial_number": "SN-PHN-0005",
        "purchase_date": date(2021, 6, 1),
        "warranty_expiry": date(2023, 6, 1),
        "notes": "Retired mobile phone",
    },
    # Accessories
    {
        "type": AssetType.ACCESSORY,
        "status": AssetStatus.IN_STOCK,
        "serial_number": "SN-ACC-0001",
        "purchase_date": date(2026, 4, 1),
        "warranty_expiry": date(2028, 4, 1),
        "notes": "USB-C docking station",
    },
    {
        "type": AssetType.ACCESSORY,
        "status": AssetStatus.ASSIGNED,
        "serial_number": "SN-ACC-0002",
        "purchase_date": date(2026, 4, 2),
        "warranty_expiry": date(2028, 4, 2),
        "notes": "Wireless keyboard and mouse",
    },
    {
        "type": AssetType.ACCESSORY,
        "status": AssetStatus.ASSIGNED,
        "serial_number": "SN-ACC-0003",
        "purchase_date": date(2026, 4, 3),
        "warranty_expiry": date(2028, 4, 3),
        "notes": "USB-C docking station",
    },
    {
        "type": AssetType.ACCESSORY,
        "status": AssetStatus.REPAIR,
        "serial_number": "SN-ACC-0004",
        "purchase_date": date(2025, 9, 1),
        "warranty_expiry": date(2027, 9, 1),
        "notes": "Damaged docking station",
    },
    {
        "type": AssetType.ACCESSORY,
        "status": AssetStatus.IN_STOCK,
        "serial_number": "SN-ACC-0005",
        "purchase_date": date(2021, 8, 1),
        "warranty_expiry": date(2023, 8, 1),
        "notes": "Retired accessory",
    },
]


ASSET_TYPE_PREFIX = {
    AssetType.LAPTOP: "LAP",
    AssetType.MONITOR: "MON",
    AssetType.PHONE: "PHN",
    AssetType.ACCESSORY: "ACC",
}


async def get_or_create_user(
    session,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is not None:
        return user

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=True,
        token_version=0,
    )

    session.add(user)
    await session.flush()

    return user


async def get_or_create_counter(
    session,
    *,
    asset_type: AssetType,
) -> AssetTagCounter:
    result = await session.execute(
        select(AssetTagCounter).where(
            AssetTagCounter.company_prefix == COMPANY_PREFIX,
            AssetTagCounter.asset_type == asset_type,
        )
    )

    counter = result.scalar_one_or_none()

    if counter is None:
        counter = AssetTagCounter(
            company_prefix=COMPANY_PREFIX,
            asset_type=asset_type,
            last_number=0,
        )
        session.add(counter)
        await session.flush()

    return counter


async def seed_assets(
    session,
    users: list[User],
) -> None:
    user1, user2, user3 = users
    assigned_users = [user1, user2, user3]

    assignment_index = 0

    for asset_data in ASSET_SEED_DATA:
        serial_number = asset_data["serial_number"]

        result = await session.execute(
            select(Asset).where(Asset.serial_number == serial_number)
        )
        asset = result.scalar_one_or_none()

        if asset is not None:
            continue

        counter = await get_or_create_counter(
            session,
            asset_type=asset_data["type"],
        )

        counter.last_number += 1

        prefix = ASSET_TYPE_PREFIX[asset_data["type"]]

        asset_tag = f"{COMPANY_PREFIX}-{prefix}-{counter.last_number:04d}"

        assigned_to = None

        if asset_data["status"] == AssetStatus.ASSIGNED:
            assigned_user = assigned_users[assignment_index % len(assigned_users)]
            assigned_to = assigned_user.id
            assignment_index += 1

        asset = Asset(
            asset_tag=asset_tag,
            type=asset_data["type"],
            serial_number=serial_number,
            status=asset_data["status"],
            assigned_to=assigned_to,
            purchase_date=asset_data["purchase_date"],
            warranty_expiry=asset_data["warranty_expiry"],
            notes=asset_data["notes"],
        )

        session.add(asset)

    await session.flush()


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        try:
            admin = await get_or_create_user(
                session,
                email=ADMIN_EMAIL,
                password=ADMIN_PASSWORD,
                full_name=ADMIN_NAME,
                role=UserRole.ADMIN,
            )

            users = []

            for user_data in USERS:
                user = await get_or_create_user(
                    session,
                    email=user_data["email"],
                    password=user_data["password"],
                    full_name=user_data["full_name"],
                    role=UserRole.USER,
                )
                users.append(user)

            await seed_assets(session, users)

            await session.commit()

            print("Seed completed successfully.")
            print()
            print("Admin:")
            print(f"  Email: {admin.email}")
            print(f"  Password: {ADMIN_PASSWORD}")
            print()
            print("Users:")

            for user in users:
                print(f"  Email: {user.email}")
                print(f"  Password: {USERS[users.index(user)]['password']}")

            print()
            print(f"Assets: {len(ASSET_SEED_DATA)}")

        except Exception:
            await session.rollback()
            raise

        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
