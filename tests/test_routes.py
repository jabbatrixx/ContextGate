"""Integration tests for the FastAPI API endpoints."""

import pytest


@pytest.mark.asyncio
class TestPruneSingleEndpoint:
    SALESFORCE_RAW = {
        "Name": "Acme Corp",
        "Industry": "Technology",
        "AnnualRevenue": 5_000_000,
        "SSN": "123-45-6789",
        "SystemModstamp": "2024-01-01T00:00:00Z",
        "IsDeleted": False,
        "PhotoUrl": "/services/images/photo.png",
        "BillingStreet": "123 Main St",
        "BillingCity": "San Francisco",
    }

    async def test_returns_200_with_pruned_payload(self, client):
        resp = await client.post(
            "/api/v1/prune",
            json={
                "profile": "salesforce_account",
                "payload": self.SALESFORCE_RAW,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "salesforce_account"
        assert "pruned_payload" in data

    async def test_only_keep_fields_in_response(self, client):
        resp = await client.post(
            "/api/v1/prune",
            json={
                "profile": "salesforce_account",
                "payload": self.SALESFORCE_RAW,
            },
        )
        pruned = resp.json()["pruned_payload"]
        assert set(pruned.keys()) == {"Name", "Industry", "AnnualRevenue", "SSN"}

    async def test_ssn_is_masked_in_response(self, client):
        resp = await client.post(
            "/api/v1/prune",
            json={
                "profile": "salesforce_account",
                "payload": self.SALESFORCE_RAW,
            },
        )
        pruned = resp.json()["pruned_payload"]
        assert "123-45-6789" not in str(pruned)
        assert pruned["SSN"] == "***-REDACTED-***"

    async def test_bytes_saved_is_positive(self, client):
        resp = await client.post(
            "/api/v1/prune",
            json={
                "profile": "salesforce_account",
                "payload": self.SALESFORCE_RAW,
            },
        )
        data = resp.json()
        assert data["bytes_saved"] > 0
        assert data["original_bytes"] > data["pruned_bytes"]

    async def test_tokens_saved_estimate_present(self, client):
        resp = await client.post(
            "/api/v1/prune",
            json={
                "profile": "salesforce_account",
                "payload": self.SALESFORCE_RAW,
            },
        )
        assert "tokens_saved_estimate" in resp.json()

    async def test_unknown_profile_returns_404(self, client):
        resp = await client.post(
            "/api/v1/prune",
            json={
                "profile": "does_not_exist",
                "payload": {"foo": "bar"},
            },
        )
        assert resp.status_code == 404
        assert "does_not_exist" in resp.json()["detail"]

    async def test_slack_profile_works(self, client):
        resp = await client.post(
            "/api/v1/prune",
            json={
                "profile": "slack_message",
                "payload": {
                    "text": "Hello team!",
                    "user": "U123",
                    "channel": "C456",
                    "user_token": "xoxb-secret",
                    "team_id": "T789",
                },
            },
        )
        assert resp.status_code == 200
        pruned = resp.json()["pruned_payload"]
        assert "text" in pruned
        assert "team_id" not in pruned
        assert "xoxb-secret" not in str(pruned)

    async def test_discord_profile_works(self, client):
        resp = await client.post(
            "/api/v1/prune",
            json={
                "profile": "discord_event",
                "payload": {
                    "content": "GG!",
                    "author_username": "player1",
                    "guild_name": "Gaming Hub",
                    "author_id": "9876543210",
                    "guild_id": "1122334455",
                },
            },
        )
        assert resp.status_code == 200
        pruned = resp.json()["pruned_payload"]
        assert "guild_id" not in pruned
        assert pruned.get("author_id") == "***REDACTED***"


@pytest.mark.asyncio
class TestPruneBatchEndpoint:
    async def test_batch_returns_list_of_pruned_records(self, client):
        payloads = [
            {
                "Name": f"Company {i}",
                "Industry": "Tech",
                "AnnualRevenue": i * 1000,
                "noise_field": "x" * 100,
            }
            for i in range(3)
        ]
        resp = await client.post(
            "/api/v1/prune/batch",
            json={
                "profile": "salesforce_account",
                "payloads": payloads,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["pruned_payload"], list)
        assert len(data["pruned_payload"]) == 3

    async def test_batch_aggregate_bytes_saved(self, client):
        payloads = [
            {"Name": "A", "Industry": "B", "AnnualRevenue": 1, "noise": "x" * 200} for _ in range(4)
        ]
        resp = await client.post(
            "/api/v1/prune/batch",
            json={
                "profile": "salesforce_account",
                "payloads": payloads,
            },
        )
        assert resp.json()["bytes_saved"] > 0

    async def test_empty_batch_returns_422(self, client):
        resp = await client.post(
            "/api/v1/prune/batch",
            json={
                "profile": "salesforce_account",
                "payloads": [],
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestProfilesEndpoint:
    async def test_returns_list_of_profiles(self, client):
        resp = await client.get("/api/v1/profiles")
        assert resp.status_code == 200
        data = resp.json()
        assert "profiles" in data
        assert "salesforce_account" in data["profiles"]
        assert "slack_message" in data["profiles"]

    async def test_count_matches_profiles_length(self, client):
        resp = await client.get("/api/v1/profiles")
        data = resp.json()
        assert data["count"] == len(data["profiles"])


@pytest.mark.asyncio
class TestAuditEndpoint:
    async def test_audit_log_is_written_after_prune(self, client):
        await client.post(
            "/api/v1/prune",
            json={
                "profile": "salesforce_account",
                "payload": {"Name": "Test Co", "Industry": "Tech", "noise": "x" * 500},
            },
        )
        resp = await client.get("/api/v1/audit/logs")
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) >= 1
        assert logs[0]["source_profile"] == "salesforce_account"

    async def test_audit_log_does_not_contain_raw_payload(self, client):
        await client.post(
            "/api/v1/prune",
            json={
                "profile": "salesforce_account",
                "payload": {"Name": "Secret Corp", "SSN": "999-99-9999"},
            },
        )
        resp = await client.get("/api/v1/audit/logs")
        logs_str = str(resp.json())
        assert "Secret Corp" not in logs_str
        assert "999-99-9999" not in logs_str

    async def test_health_endpoint(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_audit_stats_returns_structured_response(self, client):
        await client.post(
            "/api/v1/prune",
            json={
                "profile": "salesforce_account",
                "payload": {"Name": "A", "Industry": "B", "noise": "x" * 100},
            },
        )
        resp = await client.get("/api/v1/audit/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_operations" in data
        assert "total_bytes_saved" in data
        assert "total_tokens_saved" in data
        assert data["total_operations"] >= 1
