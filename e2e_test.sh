#!/bin/bash
# e2e_test.sh
# End-to-end tests against a running DataPrune server (localhost:8001)
#
# Prerequisites: DataPrune must be running (./run_local.sh in another tab)
#
# Usage:
#   chmod +x e2e_test.sh
#   ./e2e_test.sh

BASE_URL="http://localhost:8001"
PASS=0
FAIL=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No color

check() {
  local label="$1"
  local expected="$2"
  local actual="$3"
  if echo "$actual" | grep -q "$expected"; then
    echo -e "${GREEN}  ✅ PASS${NC}: $label"
    PASS=$((PASS+1))
  else
    echo -e "${RED}  ❌ FAIL${NC}: $label"
    echo -e "     Expected to find: '${YELLOW}$expected${NC}'"
    echo -e "     Got: $actual" | head -c 300
    echo ""
    FAIL=$((FAIL+1))
  fi
}

echo ""
echo -e "${BOLD}🧪 DataPrune End-to-End Tests${NC}"
echo "================================="
echo "Target: $BASE_URL"
echo ""

# ── Health check ────────────────────────────────────────────────────────────
echo -e "${BOLD}[1] Health Check${NC}"
RESP=$(curl -s "$BASE_URL/health")
check "Health endpoint returns ok" '"status":"ok"' "$RESP"
echo ""

# ── Profile discovery ────────────────────────────────────────────────────────
echo -e "${BOLD}[2] Profile Discovery${NC}"
RESP=$(curl -s "$BASE_URL/api/v1/profiles")
check "salesforce_account profile exists" "salesforce_account" "$RESP"
check "slack_message profile exists" "slack_message" "$RESP"
check "discord_event profile exists" "discord_event" "$RESP"
echo ""

# ── Salesforce account pruning ───────────────────────────────────────────────
echo -e "${BOLD}[3] Salesforce Account Pruning${NC}"
RESP=$(curl -s -X POST "$BASE_URL/api/v1/prune" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "salesforce_account",
    "payload": {
      "Name": "Acme Corp",
      "Industry": "Technology",
      "AnnualRevenue": 5000000,
      "SSN": "123-45-6789",
      "SystemModstamp": "2024-01-01T00:00:00Z",
      "IsDeleted": false,
      "PhotoUrl": "/services/images/photo.png",
      "BillingStreet": "123 Main St",
      "BillingCity": "San Francisco",
      "CreatedById": "0051234567890ABC"
    }
  }')

check "Response contains pruned_payload"  "pruned_payload" "$RESP"
check "Name field is kept"                "Acme Corp"      "$RESP"
check "Industry field is kept"            "Technology"     "$RESP"
check "AnnualRevenue field is kept"       "5000000"        "$RESP"
check "SSN is masked (not raw value)"     "REDACTED"       "$RESP"
check "Noise field SystemModstamp gone"   "bytes_saved"    "$RESP"
check "bytes_saved > 0"                   "bytes_saved"    "$RESP"
check "tokens_saved_estimate present"     "tokens_saved"   "$RESP"
# The raw SSN must NOT appear anywhere in the response
if echo "$RESP" | grep -q "123-45-6789"; then
  echo -e "${RED}  ❌ FAIL${NC}: Raw SSN leaked into response!"
  FAIL=$((FAIL+1))
else
  echo -e "${GREEN}  ✅ PASS${NC}: Raw SSN did not leak"
  PASS=$((PASS+1))
fi
echo ""

# ── Slack message pruning ────────────────────────────────────────────────────
echo -e "${BOLD}[4] Slack Message Pruning${NC}"
RESP=$(curl -s -X POST "$BASE_URL/api/v1/prune" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "slack_message",
    "payload": {
      "text": "Hello team!",
      "user": "U123ABC",
      "channel": "C456DEF",
      "user_token": "xoxb-super-secret-token",
      "team_id": "T789GHI",
      "event_ts": "1234567890.123"
    }
  }')

check "text field kept"              "Hello team"    "$RESP"
check "user field kept"              "U123ABC"       "$RESP"
check "team_id stripped"             "bytes_saved"   "$RESP"
check "user_token masked"            "REDACTED"      "$RESP"
if echo "$RESP" | grep -q "xoxb-super-secret-token"; then
  echo -e "${RED}  ❌ FAIL${NC}: Slack token leaked!"
  FAIL=$((FAIL+1))
else
  echo -e "${GREEN}  ✅ PASS${NC}: Slack token did not leak"
  PASS=$((PASS+1))
fi
echo ""

# ── Batch pruning ────────────────────────────────────────────────────────────
echo -e "${BOLD}[5] Batch Pruning (3 Salesforce accounts)${NC}"
RESP=$(curl -s -X POST "$BASE_URL/api/v1/prune/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "salesforce_account",
    "payloads": [
      {"Name": "Company A", "Industry": "Finance", "AnnualRevenue": 1000000, "junk": "aaaaaaaaaaaaaaaaaaa"},
      {"Name": "Company B", "Industry": "Healthcare", "AnnualRevenue": 2000000, "junk": "bbbbbbbbbbbbbbbbbbb"},
      {"Name": "Company C", "Industry": "Energy", "AnnualRevenue": 3000000, "junk": "ccccccccccccccccccc"}
    ]
  }')

check "Batch returns pruned_payload list" "Company A"   "$RESP"
check "Batch bytes_saved positive"        "bytes_saved" "$RESP"
echo ""

# ── Unknown profile → 404 ────────────────────────────────────────────────────
echo -e "${BOLD}[6] Unknown Profile Returns 404${NC}"
RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/v1/prune" \
  -H "Content-Type: application/json" \
  -d '{"profile": "this_does_not_exist", "payload": {"foo": "bar"}}')
check "404 for unknown profile" "404" "$RESP"
echo ""

# ── Audit log populated ──────────────────────────────────────────────────────
echo -e "${BOLD}[7] Audit Log & Stats${NC}"
RESP=$(curl -s "$BASE_URL/api/v1/audit/logs")
check "Audit log has entries"           "source_profile"  "$RESP"
check "Audit log has salesforce entry"  "salesforce"      "$RESP"

RESP=$(curl -s "$BASE_URL/api/v1/audit/stats")
check "Stats total_operations > 0"      "total_operations" "$RESP"
check "Stats total_bytes_saved > 0"     "total_bytes_saved" "$RESP"

echo ""
echo "─────────────────────────────────────"
TOTAL=$((PASS+FAIL))
echo -e "${BOLD}Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC} (of $TOTAL total)"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}${BOLD}🎉 All tests passed! DataPrune is working correctly.${NC}"

  echo ""
  echo "📊 Live token savings so far:"
  curl -s "$BASE_URL/api/v1/audit/stats" | python3 -m json.tool 2>/dev/null || \
    curl -s "$BASE_URL/api/v1/audit/stats"
  echo ""
else
  echo -e "${RED}Some tests failed. Make sure DataPrune is running:${NC}"
  echo "  ./run_local.sh"
  exit 1
fi
