"""Shared pytest fixtures for DataPrune tests."""

import os

import pytest
import pytest_asyncio
import yaml
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_dataprune.db"

from app.database import Base, get_db
from app.main import app

TEST_PROFILES = {
    "salesforce_account": {
        "keep": ["Name", "Industry", "AnnualRevenue"],
        "mask": ["SSN", "TaxId"],
        "mask_pattern": "***-REDACTED-***",
    },
    "slack_message": {
        "keep": ["text", "user", "channel"],
        "mask": ["user_token"],
        "mask_pattern": "***REDACTED***",
    },
    "discord_event": {
        "keep": ["content", "author_username", "guild_name"],
        "mask": ["author_id"],
        "mask_pattern": "***REDACTED***",
    },
    "snowflake_sales_report": {
        "keep": ["REGION", "REVENUE", "PERIOD", "REP_NAME"],
        "mask": [],
    },
    "custom_mask_pattern": {
        "keep": ["username", "role"],
        "mask": ["password", "api_key"],
        "mask_pattern": "[CLASSIFIED]",
    },
    "no_mask": {
        "keep": ["title", "body"],
        "mask": [],
    },
    "nested_profile": {
        "keep": ["name", "address", "city", "zip", "contacts", "email", "phone"],
        "mask": ["ssn", "secret"],
        "mask_pattern": "***REDACTED***",
    },
}

TEST_DB_URL = "sqlite+aiosqlite:///./test_dataprune.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def profiles_yaml_path(tmp_path_factory):
    """Write test profiles to a temp YAML file."""
    tmp = tmp_path_factory.mktemp("config")
    yaml_path = tmp / "test_profiles.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(TEST_PROFILES, f)
    os.environ["PROFILES_PATH"] = str(yaml_path)
    return yaml_path


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create tables, yield a session, drop tables after each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(profiles_yaml_path, db_session):
    """Async HTTPX client wired to the FastAPI app with test overrides."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    from app.engine import PruneEngine

    app.state.engine = PruneEngine(str(profiles_yaml_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
