"""Tests for sensitive-field masking behavior."""

import pytest
import yaml

from app.engine import PruneEngine


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    """Create a PruneEngine with masking-specific test profiles."""
    from tests.conftest import TEST_PROFILES

    tmp = tmp_path_factory.mktemp("mask_test")
    yaml_path = tmp / "profiles.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(TEST_PROFILES, f)
    return PruneEngine(str(yaml_path))


class TestSensitiveFieldMasking:
    def test_ssn_is_masked(self, engine):
        raw = {
            "Name": "Acme Corp",
            "Industry": "Finance",
            "AnnualRevenue": 1_000_000,
            "SSN": "123-45-6789",
        }
        result = engine.prune(raw, "salesforce_account")
        assert result.pruned_payload.get("SSN") == "***-REDACTED-***"
        assert "123-45-6789" not in str(result.pruned_payload)

    def test_tax_id_is_masked(self, engine):
        raw = {"Name": "Corp X", "TaxId": "98-7654321", "Industry": "Healthcare"}
        result = engine.prune(raw, "salesforce_account")
        assert result.pruned_payload.get("TaxId") == "***-REDACTED-***"
        assert "98-7654321" not in str(result.pruned_payload)

    def test_noise_field_with_sensitive_value_is_fully_stripped(self, engine):
        raw = {
            "Name": "Corp Y",
            "Industry": "Energy",
            "AnnualRevenue": 500_000,
            "InternalCreditScore": "850",
        }
        result = engine.prune(raw, "salesforce_account")
        assert "InternalCreditScore" not in result.pruned_payload
        assert "850" not in str(result.pruned_payload)

    def test_mask_pattern_applies_regardless_of_value_type(self, engine):
        raw = {"Name": "Corp Z", "Industry": "Tech", "SSN": 123456789}
        result = engine.prune(raw, "salesforce_account")
        assert result.pruned_payload["SSN"] == "***-REDACTED-***"

    def test_custom_mask_pattern_is_used(self, engine):
        raw = {
            "username": "alice",
            "role": "admin",
            "password": "super_secret_123",
            "api_key": "sk-abc123",
        }
        result = engine.prune(raw, "custom_mask_pattern")
        assert result.pruned_payload["password"] == "[CLASSIFIED]"
        assert result.pruned_payload["api_key"] == "[CLASSIFIED]"
        assert "super_secret_123" not in str(result.pruned_payload)
        assert "sk-abc123" not in str(result.pruned_payload)

    def test_keep_fields_without_mask_pass_through_unchanged(self, engine):
        raw = {"username": "bob", "role": "viewer", "password": "pass123"}
        result = engine.prune(raw, "custom_mask_pattern")
        assert result.pruned_payload["username"] == "bob"
        assert result.pruned_payload["role"] == "viewer"

    def test_profile_with_empty_mask_list(self, engine):
        raw = {"title": "My Post", "body": "Hello world", "author_token": "secret"}
        result = engine.prune(raw, "no_mask")
        assert result.pruned_payload == {"title": "My Post", "body": "Hello world"}
        assert "secret" not in str(result.pruned_payload)
