#!/usr/bin/env bash
# ---
# input: git staged files (*.py, *.ts, *.sh)
# output: stderr warnings for stale last_modified dates
# pos: .sentinel/hooks/lib/check_headers.sh
# last_modified: 2026-03-06
# ---

# Check if files with YAML front matter headers were modified but the
# last_modified date wasn't updated. Pure bash, no Python dependency.

check_headers() {
    local warnings=0
    local today
    today=$(date +%Y-%m-%d)

    # Only act on Claude's changes — check author name or commit message pattern
    if [ -n "$GIT_AUTHOR_NAME" ] && [[ "$GIT_AUTHOR_NAME" != *"claude"* && "$GIT_AUTHOR_NAME" != *"Claude"* ]]; then
        return 0
    fi

    # Get staged source files (modified only, not added/deleted)
    local files
    files=$(git diff --cached --name-only --diff-filter=M -- '*.py' '*.ts' '*.sh' 2>/dev/null)

    if [ -z "$files" ]; then
        return 0
    fi

    while IFS= read -r file; do
        [ -z "$file" ] && continue
        [ ! -f "$file" ] && continue

        # Read the first 10 lines to look for YAML front matter
        local header
        header=$(head -n 10 "$file")

        # Check if file has a YAML header (starts with # --- or // ---)
        if echo "$header" | grep -qE '^(#|//) ---'; then
            # Extract last_modified value from the header
            local last_mod
            last_mod=$(echo "$header" | grep -oE 'last_modified: [0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1 | cut -d' ' -f2)

            if [ -n "$last_mod" ] && [ "$last_mod" != "$today" ]; then
                echo "  - $file (last_modified: $last_mod, today: $today)" >&2
                warnings=$((warnings + 1))
            fi
        fi
    done <<< "$files"

    if [ "$warnings" -gt 0 ]; then
        echo "Warning: Sentinel: $warnings file(s) modified without header date update" >&2
    fi

    return 0
}
