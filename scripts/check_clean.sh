#!/usr/bin/env bash
# Clean-room check: fails if tracked files contain markers of non-public or employer content.
# The marker list is deliberately generic; extend it locally via CLEAN_EXTRA_PATTERNS (never commit employer names).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PATTERNS='(srv[0-9]{5,}|hstgr\.cloud|\b[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b|BEGIN [A-Z ]*PRIVATE KEY|api[_-]?key\s*[:=]\s*[A-Za-z0-9]{16,})'
[ -n "${CLEAN_EXTRA_PATTERNS:-}" ] && PATTERNS="$PATTERNS|$CLEAN_EXTRA_PATTERNS"
if git ls-files -z | xargs -0 grep -nIiE "$PATTERNS" -- 2>/dev/null | grep -v '^scripts/check_clean.sh'; then
  echo "check_clean: markers found above - remove them before committing" >&2; exit 1
fi
echo "check_clean: OK"
