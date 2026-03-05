"""Unit tests for the PruneEngine — pure logic, no database or FastAPI."""

import pytest
import yaml

from app.engine import ProfileNotFoundError, PruneEngine


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    """Create a PruneEngine backed by a temporary test profiles file."""
    from tests.conftest import TEST_PROFILES

    tmp = tmp_path_factory.mktemp("engine_test")
    yaml_path = tmp / "profiles.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(TEST_PROFILES, f)
    return PruneEngine(str(yaml_path))


class TestPruneKeepLogic:
    def test_only_allowlisted_fields_survive(self, engine):
        raw = {
            "Name": "Acme Corp",
            "Industry": "Technology",
            "AnnualRevenue": 5_000_000,
            "SystemModstamp": "2024-01-01T00:00:00Z",
            "IsDeleted": False,
            "PhotoUrl": "/services/images/photo.png",
            "BillingStreet": "123 Main St",
        }
        result = engine.prune(raw, "salesforce_account")
        assert set(result.pruned_payload.keys()) == {"Name", "Industry", "AnnualRevenue"}

    def test_pruned_payload_values_are_correct(self, engine):
        raw = {"Name": "Beta Ltd", "Industry": "Finance", "AnnualRevenue": 1_000_000}
        result = engine.prune(raw, "salesforce_account")
        assert result.pruned_payload["Name"] == "Beta Ltd"
        assert result.pruned_payload["Industry"] == "Finance"
        assert result.pruned_payload["AnnualRevenue"] == 1_000_000

    def test_missing_optional_fields_are_silently_ignored(self, engine):
        raw = {"Name": "Gamma Inc"}
        result = engine.prune(raw, "salesforce_account")
        assert result.pruned_payload == {"Name": "Gamma Inc"}

    def test_completely_empty_payload(self, engine):
        result = engine.prune({}, "salesforce_account")
        assert result.pruned_payload == {}


class TestCaseInsensitiveMatching:
    def test_lowercase_field_matches_uppercase_keep(self, engine):
        raw = {"region": "APAC", "revenue": 999, "period": "Q3", "rep_name": "Alice"}
        result = engine.prune(raw, "snowflake_sales_report")
        assert len(result.pruned_payload) == 4

    def test_mixed_case_field_matches(self, engine):
        raw = {"nAmE": "Delta Corp", "iNdUsTrY": "Retail", "annualrevenue": 200_000}
        result = engine.prune(raw, "salesforce_account")
        assert "nAmE" in result.pruned_payload
        assert "iNdUsTrY" in result.pruned_payload


class TestProfileListing:
    def test_list_profiles_returns_all_defined(self, engine):
        profiles = engine.list_profiles()
        assert "salesforce_account" in profiles
        assert "slack_message" in profiles
        assert "discord_event" in profiles
        assert "snowflake_sales_report" in profiles

    def test_unknown_profile_raises_error(self, engine):
        with pytest.raises(ProfileNotFoundError) as exc_info:
            engine.prune({"foo": "bar"}, "nonexistent_profile")
        assert "nonexistent_profile" in str(exc_info.value)
        assert "Available" in str(exc_info.value)


class TestSizeMetrics:
    def test_bytes_saved_is_positive(self, engine):
        raw = {
            "Name": "Acme Corp",
            "Industry": "Technology",
            "AnnualRevenue": 5_000_000,
            "SystemModstamp": "2024-01-01",
            "IsDeleted": False,
            "PhotoUrl": "/images/photo.png",
            "BillingStreet": "123 Main St",
            "BillingCity": "San Francisco",
            "BillingState": "CA",
        }
        result = engine.prune(raw, "salesforce_account")
        assert result.bytes_saved > 0
        assert result.original_bytes > result.pruned_bytes

    def test_tokens_saved_estimate_is_quarter_of_bytes(self, engine):
        raw = {"Name": "X", "Industry": "Y", "AnnualRevenue": 1, "junk": "a" * 400}
        result = engine.prune(raw, "salesforce_account")
        assert result.tokens_saved_estimate == result.bytes_saved // 4

    def test_no_noise_fields_means_zero_savings(self, engine):
        raw = {"Name": "A", "Industry": "B", "AnnualRevenue": 1}
        result = engine.prune(raw, "salesforce_account")
        assert result.original_bytes >= result.pruned_bytes


class TestBatchPrune:
    def test_batch_returns_correct_count(self, engine):
        payloads = [
            {
                "Name": f"Company {i}",
                "Industry": "Tech",
                "AnnualRevenue": i * 1000,
                "noise": "x" * 50,
            }
            for i in range(5)
        ]
        pruned_list, _ = engine.prune_batch(payloads, "salesforce_account")
        assert len(pruned_list) == 5

    def test_batch_aggregate_bytes_greater_than_single(self, engine):
        single = {"Name": "A", "Industry": "B", "AnnualRevenue": 1, "noise": "x" * 100}
        _, aggregate = engine.prune_batch([single, single, single], "salesforce_account")
        single_result = engine.prune(single, "salesforce_account")
        assert aggregate.original_bytes > single_result.original_bytes


class TestNestedPruning:
    def test_nested_dict_fields_are_pruned(self, engine):
        raw = {
            "name": "Acme",
            "address": {"city": "SF", "zip": "94105", "secret": "classified"},
        }
        result = engine.prune(raw, "nested_profile")
        assert result.pruned_payload["name"] == "Acme"
        addr = result.pruned_payload["address"]
        assert addr["city"] == "SF"
        assert addr["zip"] == "94105"
        assert addr["secret"] == "***REDACTED***"

    def test_nested_list_items_are_pruned(self, engine):
        raw = {
            "name": "Acme",
            "contacts": [
                {"email": "a@b.com", "phone": "123", "ssn": "111-22-3333"},
                {"email": "x@y.com", "phone": "456", "ssn": "444-55-6666"},
            ],
        }
        result = engine.prune(raw, "nested_profile")
        contacts = result.pruned_payload["contacts"]
        assert len(contacts) == 2
        assert contacts[0]["email"] == "a@b.com"
        assert contacts[0]["ssn"] == "***REDACTED***"
        assert "111-22-3333" not in str(result.pruned_payload)
