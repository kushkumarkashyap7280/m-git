#!/usr/bin/env bash

# ==========================================================
# enter-git-config: Multi-Account Git & GitHub Profile Manager

# ==========================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILES_DIR="$SCRIPT_DIR/profiles"
mkdir -p "$PROFILES_DIR"

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    [ -t 1 ] && [ -n "$TERM" ] && clear || true
    echo -e "${CYAN}${BOLD}====================================================${NC}"
    echo -e "${CYAN}${BOLD}         🚀 GIT & GITHUB PROFILE MANAGER           ${NC}"
    echo -e "${CYAN}${BOLD}====================================================${NC}"
    
    CURRENT_USER=$(git config --global user.name 2>/dev/null || echo "Not configured")
    CURRENT_EMAIL=$(git config --global user.email 2>/dev/null || echo "Not configured")
    echo -e "${BOLD}Current Global Git User:${NC}  ${GREEN}$CURRENT_USER${NC}"
    echo -e "${BOLD}Current Global Git Email:${NC} ${GREEN}$CURRENT_EMAIL${NC}"
    echo -e "${CYAN}----------------------------------------------------${NC}"
}

get_profiles() {
    PROFILES=()
    while IFS= read -r file; do
        [ -f "$file" ] && PROFILES+=("$file")
    done < <(find "$PROFILES_DIR" -name "*.conf" 2>/dev/null | sort)
}

# Function to clean and sanitize token
clean_token() {
    local raw="$1"
    # Strip carriage returns, newlines, tabs, quotes, spaces, and terminal ANSI escape codes
    echo "$raw" | tr -d '\r\n\t "' | sed -E 's/\x1b\[[0-9;]*[a-zA-Z~]//g' | sed -E 's/[^a-zA-Z0-9_]//g'
}

# Verify token against GitHub API
verify_github_token() {
    local token="$1"
    curl -s -H "Authorization: Bearer $token" -H "User-Agent: GitProfileManager" https://api.github.com/user | \
    python3 -c "import sys, json; print(json.load(sys.stdin).get('login', ''))" 2>/dev/null
}

# ----------------------------------------------------------
# GitHub CLI (gh) credential backend
#
# Why: git-credential-osxkeychain (macOS) / cache / store helpers key their
# lookup by protocol+host only when the remote URL carries no username, so
# with several accounts saved for the same host, git can silently hand back
# a stale token instead of the one you just switched to -- this is also why
# VS Code (which just shells out to git) keeps using the wrong account.
# `gh` tracks multiple accounts per host natively and always resolves the
# *active* one, and it behaves identically on macOS and Linux, so it
# replaces the manual erase/store dance below wherever it's installed.
# ----------------------------------------------------------
check_gh_cli() {
    command -v gh >/dev/null 2>&1
}

apply_github_auth() {
    local username="$1"
    local token="$2"

    if check_gh_cli; then
        if printf '%s' "$token" | gh auth login --hostname github.com --git-protocol https --with-token 2>/tmp/gh_login_err; then
            gh auth switch --hostname github.com --user "$username" >/dev/null 2>&1
            gh auth setup-git >/dev/null 2>&1
            echo -e "${CYAN}git credential.helper routed through gh CLI (github.com -> $username).${NC}"
        else
            echo -e "${RED}Warning: 'gh auth login' failed:${NC} $(cat /tmp/gh_login_err 2>/dev/null)"
        fi
        rm -f /tmp/gh_login_err
    else
        echo -e "${YELLOW}Warning: GitHub CLI 'gh' not found on PATH.${NC}"
        echo -e "Install it (brew install gh / apt install gh -- see https://cli.github.com) for reliable multi-account auth."
        echo -e "Falling back to macOS Keychain (single-account only, may collide with prior tokens; not available on Linux)."
        git config --global credential.helper osxkeychain
        printf "protocol=https\nhost=github.com\n" | git credential-osxkeychain erase 2>/dev/null
        printf "protocol=https\nhost=github.com\nusername=%s\npassword=%s\n" "$username" "$token" | git credential-osxkeychain store 2>/dev/null
    fi
}

# Open a new VS Code window pinned to a profile. The GitHub sign-in inside
# that profile is a separate, OAuth-only session VS Code manages itself --
# it must be signed in once, interactively, via that window's Accounts icon;
# this just opens the correctly-scoped window.
launch_vscode_profile() {
    local vscode_profile="$1"
    [ -z "$vscode_profile" ] && return
    read -p "Open VS Code with profile '$vscode_profile' now? (y/n): " LAUNCH
    if [[ "$LAUNCH" =~ ^[Yy]$ ]]; then
        if command -v code >/dev/null 2>&1; then
            code -n --profile "$vscode_profile" >/dev/null 2>&1 &
            echo -e "${GREEN}Launched VS Code with profile '$vscode_profile'.${NC}"
            echo -e "First time only: sign in via that window's Accounts icon with the matching GitHub account."
        else
            echo -e "${YELLOW}Warning: 'code' CLI not found on PATH.${NC}"
            echo -e "In VS Code: Cmd/Ctrl+Shift+P -> 'Shell Command: Install code command in PATH'."
        fi
    fi
}

# ----------------------------------------------------------
# 1. SWITCH ACCOUNT
# ----------------------------------------------------------
switch_account() {
    print_header
    get_profiles

    if [ ${#PROFILES[@]} -eq 0 ]; then
        echo -e "\n${YELLOW}⚠️  No accounts saved yet!${NC}"
        echo -e "Please choose Option 2 from the main menu to add an account.\n"
        read -p "Press Enter to return to main menu..."
        return
    fi

    echo -e "\n${BOLD}Select an account to switch to:${NC}\n"
    for i in "${!PROFILES[@]}"; do
        PROFILE_FILE="${PROFILES[$i]}"
        unset PROFILE_LABEL GIT_USERNAME GIT_EMAIL GIT_TOKEN
        source "$PROFILE_FILE"
        echo -e "  ${CYAN}[$((i+1))]${NC} ${BOLD}$PROFILE_LABEL${NC}"
        echo -e "      Username: ${BLUE}$GIT_USERNAME${NC} | Email: ${BLUE}$GIT_EMAIL${NC}"
    done
    echo -e "  ${YELLOW}[B]${NC} Back to Main Menu"
    echo ""

    read -p "Enter choice [1-${#PROFILES[@]} or B]: " CHOICE

    if [[ "$CHOICE" =~ ^[Bb]$ ]] || [ -z "$CHOICE" ]; then
        return
    fi

    if [[ "$CHOICE" =~ ^[0-9]+$ ]] && [ "$CHOICE" -ge 1 ] && [ "$CHOICE" -le "${#PROFILES[@]}" ]; then
        SELECTED_FILE="${PROFILES[$((CHOICE-1))]}"
        unset PROFILE_LABEL GIT_USERNAME GIT_EMAIL GIT_TOKEN VSCODE_PROFILE
        source "$SELECTED_FILE"

        echo -e "\n${YELLOW}Switching globally to $PROFILE_LABEL...${NC}"

        # 1. Update Global Git User (identity)
        git config --global user.name "$GIT_USERNAME"
        git config --global user.email "$GIT_EMAIL"

        # 2. Route GitHub credential resolution through gh CLI (falls back to
        #    Keychain if gh isn't installed) -- see apply_github_auth() for why.
        apply_github_auth "$GIT_USERNAME" "$GIT_TOKEN"

        # 3. Verify
        echo -e "${YELLOW}Verifying with GitHub...${NC}"
        AUTHED_USER=$(verify_github_token "$GIT_TOKEN")

        echo ""
        if [ -n "$AUTHED_USER" ]; then
            echo -e "${GREEN}🎉 SUCCESS: Switched to '$PROFILE_LABEL'!${NC}"
            echo -e "✅ GitHub Auth: ${GREEN}Active & Verified as @$AUTHED_USER${NC}"
        else
            echo -e "${YELLOW}⚠️  Git configured, but GitHub token verification failed.${NC}"
            echo -e "Token may be expired or lack 'repo' scope."
        fi

        echo -e "✅ Global Git User:  ${CYAN}$GIT_USERNAME${NC}"
        echo -e "✅ Global Git Email: ${CYAN}$GIT_EMAIL${NC}\n"

        # 4. Optionally open the matching VS Code profile (separate OAuth
        #    session -- see launch_vscode_profile() comment).
        launch_vscode_profile "$VSCODE_PROFILE"

        read -p "Press Enter to return to main menu..."
    else
        echo -e "${RED}Invalid selection.${NC}"
        sleep 1
    fi
}

# ----------------------------------------------------------
# 2. ADD NEW ACCOUNT
# ----------------------------------------------------------
add_account() {
    print_header
    echo -e "\n${BOLD}➕ Add New GitHub Account${NC}\n"

    read -p "Account Nickname (e.g. Company, Client, Personal): " PROFILE_LABEL
    if [ -z "$PROFILE_LABEL" ]; then
        echo -e "${RED}❌ Nickname cannot be empty.${NC}"
        sleep 1
        return
    fi

    read -p "GitHub Username (e.g. <user>): " GIT_USERNAME
    if [ -z "$GIT_USERNAME" ]; then
        echo -e "${RED}❌ Username cannot be empty.${NC}"
        sleep 1
        return
    fi

    read -p "Git Email (e.g. <user>@example.com): " GIT_EMAIL
    if [ -z "$GIT_EMAIL" ]; then
        echo -e "${RED}❌ Email cannot be empty.${NC}"
        sleep 1
        return
    fi

    read -p "VS Code Profile name to open on switch (optional, must already exist in VS Code): " VSCODE_PROFILE

    echo -e "\n${BOLD}How would you like to provide the Personal Access Token (PAT)?${NC}"
    echo -e "  ${CYAN}[1] Read directly from Mac Clipboard${NC} ${GREEN}(Recommended - just copy on GitHub first)${NC}"
    echo -e "  ${CYAN}[2] Type / Paste into terminal manually${NC}"
    read -p "Select option [1 or 2]: " TOKEN_INPUT_METHOD

    RAW_TOKEN=""
    if [ "$TOKEN_INPUT_METHOD" = "1" ]; then
        RAW_TOKEN=$(pbpaste)
        echo -e "${GREEN}Read token from clipboard.${NC}"
    else
        echo -e "${YELLOW}Paste token and press Enter:${NC}"
        read -r RAW_TOKEN
    fi

    GIT_TOKEN=$(clean_token "$RAW_TOKEN")

    if [ -z "$GIT_TOKEN" ]; then
        echo -e "${RED}❌ Token cannot be empty or invalid.${NC}"
        sleep 2
        return
    fi

    TOKEN_LEN=${#GIT_TOKEN}
    if [ "$TOKEN_LEN" -gt 8 ]; then
        TOKEN_MASK="${GIT_TOKEN:0:4}...${GIT_TOKEN: -4}"
    else
        TOKEN_MASK="****"
    fi
    echo -e "Token format check: ${GREEN}$TOKEN_MASK${NC} (clean length: $TOKEN_LEN characters)"

    # Verify with GitHub API
    echo -e "\n${YELLOW}Testing token with GitHub API...${NC}"
    AUTHED_USER=$(verify_github_token "$GIT_TOKEN")

    if [ -n "$AUTHED_USER" ]; then
        echo -e "${GREEN}🎉 Verified! Token belongs to GitHub user: @$AUTHED_USER${NC}"
    else
        echo -e "${RED}⚠️  Warning: GitHub API rejected this token (HTTP 401 / Invalid).${NC}"
        echo -e "Make sure the token was copied correctly and has 'repo' scope."
        read -p "Do you still want to save this account? (y/n): " PROCEED
        if [[ ! "$PROCEED" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Account not saved.${NC}"
            sleep 2
            return
        fi
    fi

    # Save to profile file
    SLUG=$(echo "$PROFILE_LABEL" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')
    PROFILE_FILE="$PROFILES_DIR/${SLUG}.conf"

    cat << PROFILE_EOF > "$PROFILE_FILE"
PROFILE_LABEL="$PROFILE_LABEL"
GIT_USERNAME="$GIT_USERNAME"
GIT_EMAIL="$GIT_EMAIL"
GIT_TOKEN="$GIT_TOKEN"
VSCODE_PROFILE="$VSCODE_PROFILE"
PROFILE_EOF

    chmod 600 "$PROFILE_FILE"
    echo -e "\n${GREEN}🎉 Account '$PROFILE_LABEL' saved successfully!${NC}"

    read -p "Do you want to switch to this account globally right now? (y/n): " SWITCH_NOW
    if [[ "$SWITCH_NOW" =~ ^[Yy]$ ]]; then
        git config --global user.name "$GIT_USERNAME"
        git config --global user.email "$GIT_EMAIL"
        apply_github_auth "$GIT_USERNAME" "$GIT_TOKEN"
        echo -e "${GREEN}✅ Switched active Git user to $GIT_USERNAME ($GIT_EMAIL)!${NC}"
        launch_vscode_profile "$VSCODE_PROFILE"
    fi

    echo ""
    read -p "Press Enter to return to main menu..."
}

# ----------------------------------------------------------
# 3. DELETE ACCOUNT
# ----------------------------------------------------------
delete_account() {
    print_header
    get_profiles

    if [ ${#PROFILES[@]} -eq 0 ]; then
        echo -e "\n${YELLOW}⚠️  No accounts saved to delete.${NC}\n"
        read -p "Press Enter to return to main menu..."
        return
    fi

    echo -e "\n${BOLD}Select an account to delete (or enter username/email):${NC}\n"
    for i in "${!PROFILES[@]}"; do
        PROFILE_FILE="${PROFILES[$i]}"
        unset PROFILE_LABEL GIT_USERNAME GIT_EMAIL
        source "$PROFILE_FILE"
        echo -e "  ${CYAN}[$((i+1))]${NC} ${BOLD}$PROFILE_LABEL${NC} (Username: ${BLUE}$GIT_USERNAME${NC} | Email: ${BLUE}$GIT_EMAIL${NC})"
    done
    echo -e "  ${YELLOW}[B]${NC} Back to Main Menu"
    echo ""

    read -p "Enter number, username, or email to delete [or B]: " DEL_INPUT

    if [[ "$DEL_INPUT" =~ ^[Bb]$ ]] || [ -z "$DEL_INPUT" ]; then
        return
    fi

    TARGET_FILE=""
    TARGET_LABEL=""

    if [[ "$DEL_INPUT" =~ ^[0-9]+$ ]] && [ "$DEL_INPUT" -ge 1 ] && [ "$DEL_INPUT" -le "${#PROFILES[@]}" ]; then
        TARGET_FILE="${PROFILES[$((DEL_INPUT-1))]}"
        source "$TARGET_FILE"
        TARGET_LABEL="$PROFILE_LABEL"
    else
        for f in "${PROFILES[@]}"; do
            unset PROFILE_LABEL GIT_USERNAME GIT_EMAIL
            source "$f"
            if [ "$GIT_USERNAME" = "$DEL_INPUT" ] || [ "$GIT_EMAIL" = "$DEL_INPUT" ] || [ "$PROFILE_LABEL" = "$DEL_INPUT" ]; then
                TARGET_FILE="$f"
                TARGET_LABEL="$PROFILE_LABEL"
                break
            fi
        done
    fi

    if [ -n "$TARGET_FILE" ] && [ -f "$TARGET_FILE" ]; then
        echo ""
        read -p "Are you sure you want to delete '$TARGET_LABEL'? (y/n): " CONFIRM
        if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
            rm -f "$TARGET_FILE"
            echo -e "${GREEN}✅ Successfully deleted '$TARGET_LABEL'.${NC}"
        else
            echo -e "${YELLOW}Deletion cancelled.${NC}"
        fi
    else
        echo -e "${RED}❌ No matching account found for '$DEL_INPUT'.${NC}"
    fi

    echo ""
    read -p "Press Enter to return to main menu..."
}

# ----------------------------------------------------------
# MAIN LOOP
# ----------------------------------------------------------
while true; do
    print_header
    echo -e "${BOLD}Please choose an option:${NC}\n"
    echo -e "  ${CYAN}1)${NC} ${BOLD}Switch Account${NC}       (switch global Git user & GitHub login)"
    echo -e "  ${CYAN}2)${NC} ${BOLD}Add New Account${NC}      (save a new GitHub username, email & token)"
    echo -e "  ${CYAN}3)${NC} ${BOLD}Delete Account${NC}       (delete by number, username, or email)"
    echo -e "  ${CYAN}4)${NC} ${BOLD}Exit${NC}"
    echo ""

    read -p "Enter your choice [1-4]: " MENU_CHOICE

    case "$MENU_CHOICE" in
        1)
            switch_account
            ;;
        2)
            add_account
            ;;
        3)
            delete_account
            ;;
        4)
            [ -t 1 ] && [ -n "$TERM" ] && clear || true
            echo -e "\n${GREEN}Goodbye! 👋${NC}\n"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Please enter 1, 2, 3, or 4.${NC}"
            sleep 1
            ;;
    esac
done
