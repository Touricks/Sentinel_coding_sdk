#!/usr/bin/env bash
# ---
# input: git staged files
# output: stderr warnings for stale directory CLAUDE.md files
# pos: .sentinel/hooks/lib/check_dir_docs.sh
# last_modified: 2026-03-06
# ---

# Check if files in a directory were modified but the directory's CLAUDE.md
# wasn't updated. Pure bash, no Python dependency.

check_dir_docs() {
    local warnings=0

    # Only act on Claude's changes — check author name or commit message pattern
    if [ -n "$GIT_AUTHOR_NAME" ] && [[ "$GIT_AUTHOR_NAME" != *"claude"* && "$GIT_AUTHOR_NAME" != *"Claude"* ]]; then
        return 0
    fi

    # Get all staged files
    local staged
    staged=$(git diff --cached --name-only 2>/dev/null)

    if [ -z "$staged" ]; then
        return 0
    fi

    # Get unique parent directories of staged files
    local dirs
    dirs=$(echo "$staged" | while IFS= read -r f; do dirname "$f"; done | sort -u)

    while IFS= read -r dir; do
        [ -z "$dir" ] && continue

        # Skip root directory, .git, and hidden directories
        [ "$dir" = "." ] && continue
        [[ "$dir" == .git* ]] && continue
        [[ "$dir" == */.git* ]] && continue

        # Check if CLAUDE.md exists in that directory
        if [ -f "$dir/CLAUDE.md" ]; then
            # Check if CLAUDE.md is also in the staged files
            if ! echo "$staged" | grep -qxF "$dir/CLAUDE.md"; then
                echo "  - $dir/CLAUDE.md exists but was not updated" >&2
                warnings=$((warnings + 1))
            fi
        fi
    done <<< "$dirs"

    if [ "$warnings" -gt 0 ]; then
        echo "Warning: Sentinel: $warnings directory manifest(s) may be stale" >&2
    fi

    return 0
}
