#!/usr/bin/env bash
# ---
# input: none (run from anywhere inside a git repo)
# output: symlink .git/hooks/pre-commit -> sentinel pre-commit hook
# pos: .sentinel/hooks/install.sh
# last_modified: 2026-03-06
# ---

# Idempotent hook installer for Sentinel pre-commit hook.
# Safe: will not overwrite existing hooks from other tools.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK_SOURCE="$SCRIPT_DIR/pre-commit"

# 1. Find the git repo root
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
    echo "Error: not inside a git repository." >&2
    exit 1
fi

# 2. Determine hooks directory (respect core.hooksPath if set)
HOOKS_PATH=$(git config --get core.hooksPath 2>/dev/null || true)
if [ -n "$HOOKS_PATH" ]; then
    # Resolve relative paths against repo root
    if [[ "$HOOKS_PATH" != /* ]]; then
        HOOKS_PATH="$REPO_ROOT/$HOOKS_PATH"
    fi
else
    HOOKS_PATH="$REPO_ROOT/.git/hooks"
fi

# Ensure hooks directory exists
mkdir -p "$HOOKS_PATH"

TARGET="$HOOKS_PATH/pre-commit"

# 3. If pre-commit already points to our hook: skip
if [ -L "$TARGET" ]; then
    EXISTING_TARGET=$(readlink "$TARGET")
    if [ "$EXISTING_TARGET" = "$HOOK_SOURCE" ]; then
        echo "Sentinel: pre-commit hook already installed. Nothing to do."
        exit 0
    fi
fi

# 4. If pre-commit exists and is different: warn, don't overwrite
if [ -e "$TARGET" ]; then
    echo "Warning: $TARGET already exists and is not a Sentinel hook." >&2
    echo "  To install manually, run:" >&2
    echo "    ln -sf \"$HOOK_SOURCE\" \"$TARGET\"" >&2
    exit 0
fi

# 5. If no pre-commit: symlink our hook
ln -s "$HOOK_SOURCE" "$TARGET"

# 6. Ensure executable
chmod +x "$HOOK_SOURCE"

echo "Sentinel: pre-commit hook installed successfully."
echo "  $TARGET -> $HOOK_SOURCE"

exit 0
