#!/usr/bin/env python3
"""
Multi-Account Git & GitHub Profile Manager
Interactive CLI tool to seamlessly manage and switch between multiple Git & GitHub accounts.
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROFILES_FILE = SCRIPT_DIR / "profiles.json"
OLD_PROFILES_DIR = SCRIPT_DIR / "profiles"

# ANSI Colors
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[0;36m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
MAGENTA = "\033[0;35m"
RESET = "\033[0m"


def clear_screen():
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    clear_screen()
    print(f"{CYAN}{BOLD}╭────────────────────────────────────────────────────────────╮{RESET}")
    print(f"{CYAN}{BOLD}│             GIT & GITHUB PROFILE MANAGER                │{RESET}")
    print(f"{CYAN}{BOLD}╰────────────────────────────────────────────────────────────╯{RESET}")

    current_user = run_cmd(["git", "config", "--global", "user.name"]) or "Not configured"
    current_email = run_cmd(["git", "config", "--global", "user.email"]) or "Not configured"

    print(f" {BOLD}Active Global User:{RESET}  {GREEN}{BOLD}{current_user}{RESET}")
    print(f" {BOLD}Active Global Email:{RESET} {GREEN}{current_email}{RESET}")
    print(f"{DIM}──────────────────────────────────────────────────────────────{RESET}")


def run_cmd(cmd_list, stdin_input=None):
    """Run a shell command and return stdout string (stripped)."""
    try:
        proc = subprocess.run(
            cmd_list,
            input=stdin_input,
            text=True,
            capture_output=True,
            check=False
        )
        return proc.stdout.strip()
    except Exception:
        return ""


def init_profiles_file():
    """Ensure profiles.json exists with secure permissions (chmod 600)."""
    if not PROFILES_FILE.exists():
        PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROFILES_FILE, "w") as f:
            json.dump([], f, indent=2)
        try:
            os.chmod(PROFILES_FILE, 0o600)
        except OSError:
            pass


def load_profiles():
    """Load profiles from profiles.json, initializing file if it does not exist."""
    init_profiles_file()
    profiles = []

    try:
        with open(PROFILES_FILE, "r") as f:
            profiles = json.load(f)
    except Exception:
        profiles = []

    # Migrate legacy .conf files if present and not already migrated
    if OLD_PROFILES_DIR.exists():
        migrated = False
        for conf_file in OLD_PROFILES_DIR.glob("*.conf"):
            try:
                content = conf_file.read_text()
                label_m = re.search(r'PROFILE_LABEL="([^"]+)"', content)
                user_m = re.search(r'GIT_USERNAME="([^"]+)"', content)
                email_m = re.search(r'GIT_EMAIL="([^"]+)"', content)
                token_m = re.search(r'GIT_TOKEN="([^"]+)"', content)
                vscode_m = re.search(r'VSCODE_PROFILE="([^"]*)"', content)

                if label_m and user_m and email_m and token_m:
                    existing = any(p.get("username") == user_m.group(1) for p in profiles)
                    if not existing:
                        profiles.append({
                            "label": label_m.group(1),
                            "username": user_m.group(1),
                            "email": email_m.group(1),
                            "token": token_m.group(1),
                            "vscode_profile": (vscode_m.group(1) if vscode_m and vscode_m.group(1) else None)
                        })
                        migrated = True
            except Exception:
                pass
        if migrated:
            save_profiles(profiles)

    return profiles


def save_profiles(profiles):
    """Save profiles securely with 600 permissions."""
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2)
    os.chmod(PROFILES_FILE, 0o600)


def clean_token(raw_token):
    """Strip whitespace, quotes, escape sequences from pasted tokens."""
    cleaned = re.sub(r'[\r\n\t "]', '', raw_token)
    cleaned = re.sub(r'\x1b\[[0-9;]*[a-zA-Z~]', '', cleaned)
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '', cleaned)
    return cleaned.strip()


def verify_github_token(token):
    """Verify personal access token against GitHub API using curl (respecting macOS root certs)."""
    try:
        cmd = [
            "curl", "-s",
            "-H", f"Authorization: Bearer {token}",
            "-H", "User-Agent: GitProfileManager",
            "https://api.github.com/user"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        data = json.loads(proc.stdout)
        return data.get("login")
    except Exception:
        return None


def mask_token(token):
    if len(token) > 8:
        return f"{token[:4]}...{token[-4:]}"
    return "****"


# -------------------------------------------------------------
# GitHub CLI (gh) credential backend
#
# Why: `git credential-osxkeychain` (and Linux equivalents) key lookups by
# protocol+host only when the remote URL has no username in it, so with
# several accounts stored for the same host, git/VS Code can silently pick
# up a stale token instead of the one you just switched to. `gh` natively
# tracks multiple accounts per host and always resolves the *active* one,
# and it works identically on macOS and Linux (and Windows), so it replaces
# the Keychain-erase/store dance entirely.
# -------------------------------------------------------------

def check_gh_cli():
    """Return True if GitHub CLI (gh) is installed and on PATH."""
    return run_cmd(["gh", "--version"]) != ""


def gh_login_with_token(token):
    """Log a GitHub account into gh using a PAT (adds it to gh's stored accounts,
    or refreshes it if already known). Non-interactive: token is piped via stdin."""
    try:
        proc = subprocess.run(
            ["gh", "auth", "login", "--hostname", "github.com", "--git-protocol", "https", "--with-token"],
            input=token, text=True, capture_output=True, check=False
        )
        return proc.returncode == 0, proc.stderr.strip()
    except Exception as e:
        return False, str(e)


def gh_switch_account(username):
    """Make `username` the active gh account for github.com (and therefore the
    one git/VS Code get when they ask for a credential)."""
    proc = subprocess.run(
        ["gh", "auth", "switch", "--hostname", "github.com", "--user", username],
        text=True, capture_output=True, check=False
    )
    return proc.returncode == 0


def gh_setup_git():
    """Point git's credential.helper at `gh auth git-credential` (idempotent)."""
    run_cmd(["gh", "auth", "setup-git"])


def apply_github_auth(username, token):
    """Route git's GitHub credential through gh CLI if available, otherwise fall
    back to the legacy macOS-only Keychain method (with a warning, since that
    path is prone to stale-account collisions and doesn't work on Linux)."""
    if check_gh_cli():
        ok, err = gh_login_with_token(token)
        if not ok:
            print(f"{RED}Warning: 'gh auth login' failed: {err}{RESET}")
            return False
        gh_switch_account(username)
        gh_setup_git()
        print(f"{DIM}git credential.helper routed through gh CLI (github.com -> {username}).{RESET}")
        return True
    else:
        print(f"{YELLOW}Warning: GitHub CLI 'gh' not found on PATH.{RESET}")
        print(f"{DIM}Install it (brew install gh / see https://cli.github.com) for reliable multi-account auth.{RESET}")
        print(f"{DIM}Falling back to macOS Keychain (single-account only, may collide with prior tokens).{RESET}")
        run_cmd(["git", "config", "--global", "credential.helper", "osxkeychain"])
        erase_input = "protocol=https\nhost=github.com\n"
        run_cmd(["git", "credential-osxkeychain", "erase"], stdin_input=erase_input)
        store_input = f"protocol=https\nhost=github.com\nusername={username}\npassword={token}\n"
        run_cmd(["git", "credential-osxkeychain", "store"], stdin_input=store_input)
        return False


def launch_vscode_profile(vscode_profile):
    """Open a new VS Code window pinned to the given profile, if the `code`
    CLI is available. The GitHub sign-in inside that profile is a separate,
    OAuth-only session VS Code manages itself -- it must be signed in once,
    interactively, via that window's Accounts icon; this just opens the
    correctly-scoped window so you sign in (or already are) as the right account."""
    if not vscode_profile:
        return
    launch = input(f"\nOpen VS Code with profile '{vscode_profile}' now? (y/n): ").strip().lower()
    if launch != 'y':
        return
    if run_cmd(["code", "--version"]):
        subprocess.run(["code", "-n", "--profile", vscode_profile], check=False)
        print(f"{GREEN}Launched VS Code with profile '{vscode_profile}'.{RESET}")
        print(f"{DIM}First time only: sign in via that window's Accounts icon with the matching GitHub account.{RESET}")
    else:
        print(f"{YELLOW}Warning: 'code' CLI not found on PATH.{RESET}")
        print(f"{DIM}In VS Code: Cmd+Shift+P -> 'Shell Command: Install code command in PATH'.{RESET}")


# -------------------------------------------------------------
# Actions
# -------------------------------------------------------------

def switch_account():
    print_banner()
    profiles = load_profiles()

    if not profiles:
        print(f"\n{YELLOW}Warning: No saved accounts found.{RESET}")
        print(f"Choose Option 2 from the main menu to add an account.\n")
        input(f"{DIM}Press Enter to return to main menu...{RESET}")
        return

    print(f"\n{BOLD}Select an account to switch to globally:{RESET}\n")
    for idx, p in enumerate(profiles, 1):
        print(f"  {CYAN}[{idx}]{RESET} {BOLD}{p['label']}{RESET}")
        print(f"      Username: {BLUE}{p['username']}{RESET} | Email: {BLUE}{p['email']}{RESET}")
    print(f"  {YELLOW}[B]{RESET} Back to Main Menu\n")

    choice = input("Enter choice: ").strip()
    if choice.lower() == 'b' or not choice:
        return

    if not choice.isdigit() or not (1 <= int(choice) <= len(profiles)):
        print(f"{RED}Invalid selection.{RESET}")
        input(f"{DIM}Press Enter to continue...{RESET}")
        return

    selected = profiles[int(choice) - 1]
    print(f"\n{YELLOW}Switching globally to {selected['label']}...{RESET}")

    # 1. Update git config globally (identity)
    run_cmd(["git", "config", "--global", "user.name", selected["username"]])
    run_cmd(["git", "config", "--global", "user.email", selected["email"]])

    # 2. Route GitHub credential resolution through gh CLI (falls back to
    #    Keychain if gh isn't installed) -- see apply_github_auth() for why.
    apply_github_auth(selected["username"], selected["token"])

    # 3. Verify
    print(f"{DIM}Verifying authentication with GitHub...{RESET}")
    authed_user = verify_github_token(selected["token"])

    print(f"\n{GREEN}{BOLD}SUCCESS: Switched to '{selected['label']}'!{RESET}")
    if authed_user:
        print(f"GitHub Authentication: {GREEN}Active as @{authed_user}{RESET}")
    else:
        print(f"Warning: Git credentials updated, but GitHub token could not be verified.")

    print(f"Active Git User:  {CYAN}{selected['username']}{RESET}")
    print(f"Active Git Email: {CYAN}{selected['email']}{RESET}\n")

    # 4. Optionally open the matching VS Code profile (separate OAuth session --
    #    see launch_vscode_profile() docstring).
    launch_vscode_profile(selected.get("vscode_profile"))

    input(f"\n{DIM}Press Enter to return to main menu...{RESET}")


def add_account():
    print_banner()
    print(f"\n{BOLD}Add New Git & GitHub Account{RESET}\n")

    label = input(f"Account Nickname {DIM}(e.g. Company Work, Client Project, Personal){RESET}: ").strip()
    if not label:
        print(f"{RED}Error: Nickname cannot be empty.{RESET}")
        input(f"{DIM}Press Enter to continue...{RESET}")
        return

    username = input(f"GitHub Username {DIM}(e.g. <user>){RESET}: ").strip()
    if not username:
        print(f"{RED}Error: Username cannot be empty.{RESET}")
        input(f"{DIM}Press Enter to continue...{RESET}")
        return

    email = input(f"Git Email {DIM}(e.g. <user>@example.com){RESET}: ").strip()
    if not email:
        print(f"{RED}Error: Email cannot be empty.{RESET}")
        input(f"{DIM}Press Enter to continue...{RESET}")
        return

    vscode_profile = input(
        f"VS Code Profile name to open on switch {DIM}(optional -- must already exist in VS Code, leave blank to skip){RESET}: "
    ).strip()

    print(f"\n{BOLD}Provide Personal Access Token (PAT):{RESET}")
    print(f"  {CYAN}[1]{RESET} Read directly from Mac Clipboard {GREEN}(Recommended){RESET}")
    print(f"  {CYAN}[2]{RESET} Paste into terminal manually")
    method = input("Select option [1 or 2]: ").strip()

    raw_token = ""
    if method == "1":
        raw_token = run_cmd(["pbpaste"])
        print(f"{GREEN}Read token from clipboard.{RESET}")
    else:
        raw_token = input("Paste token and press Enter: ").strip()

    token = clean_token(raw_token)
    if not token:
        print(f"{RED}Error: Token cannot be empty.{RESET}")
        input(f"{DIM}Press Enter to continue...{RESET}")
        return

    print(f"Token format: {GREEN}{mask_token(token)}{RESET} ({len(token)} characters)")
    print(f"\n{YELLOW}Testing token with GitHub API...{RESET}")
    authed_user = verify_github_token(token)

    if authed_user:
        print(f"{GREEN}Verified! Token belongs to GitHub user: @{authed_user}{RESET}")
    else:
        print(f"{RED}Warning: Warning: GitHub API rejected this token or network failed.{RESET}")
        proceed = input("Do you still want to save this account? (y/n): ").strip().lower()
        if proceed != 'y':
            print(f"{YELLOW}Account not saved.{RESET}")
            input(f"{DIM}Press Enter to continue...{RESET}")
            return

    profiles = load_profiles()
    # Update if already exists, else append
    existing_idx = next((i for i, p in enumerate(profiles) if p.get("username") == username), None)
    new_profile = {
        "label": label,
        "username": username,
        "email": email,
        "token": token,
        "vscode_profile": vscode_profile or None
    }

    if existing_idx is not None:
        profiles[existing_idx] = new_profile
        print(f"\n{GREEN}Updated existing account '{label}'!{RESET}")
    else:
        profiles.append(new_profile)
        print(f"\n{GREEN}Account '{label}' saved successfully!{RESET}")

    save_profiles(profiles)

    switch_now = input("\nSwitch to this account globally right now? (y/n): ").strip().lower()
    if switch_now == 'y':
        run_cmd(["git", "config", "--global", "user.name", username])
        run_cmd(["git", "config", "--global", "user.email", email])
        apply_github_auth(username, token)
        print(f"{GREEN}Switched active Git user to {username} ({email})!{RESET}")
        launch_vscode_profile(vscode_profile)

    input(f"\n{DIM}Press Enter to return to main menu...{RESET}")


def delete_account():
    print_banner()
    profiles = load_profiles()

    if not profiles:
        print(f"\n{YELLOW}Warning: No accounts saved to delete.{RESET}\n")
        input(f"{DIM}Press Enter to return to main menu...{RESET}")
        return

    print(f"\n{BOLD}Saved Accounts:{RESET}\n")
    for idx, p in enumerate(profiles, 1):
        print(f"  {CYAN}[{idx}]{RESET} {BOLD}{p['label']}{RESET} (User: {BLUE}{p['username']}{RESET} | Email: {BLUE}{p['email']}{RESET})")
    print(f"  {YELLOW}[B]{RESET} Back to Main Menu\n")

    target = input("Enter number, username, or email to delete [or B]: ").strip()
    if target.lower() == 'b' or not target:
        return

    delete_idx = None
    if target.isdigit() and 1 <= int(target) <= len(profiles):
        delete_idx = int(target) - 1
    else:
        for idx, p in enumerate(profiles):
            if target in (p["username"], p["email"], p["label"]):
                delete_idx = idx
                break

    if delete_idx is None:
        print(f"{RED}Error: No matching account found.{RESET}")
        input(f"{DIM}Press Enter to continue...{RESET}")
        return

    to_delete = profiles[delete_idx]
    confirm = input(f"\nAre you sure you want to delete '{to_delete['label']}'? (y/n): ").strip().lower()
    if confirm == 'y':
        profiles.pop(delete_idx)
        save_profiles(profiles)
        print(f"{GREEN}Successfully deleted '{to_delete['label']}'.{RESET}")
    else:
        print(f"{YELLOW}Deletion cancelled.{RESET}")

    input(f"\n{DIM}Press Enter to return to main menu...{RESET}")


def view_accounts():
    print_banner()
    profiles = load_profiles()

    if not profiles:
        print(f"\n{YELLOW}Warning: No saved accounts found.{RESET}\n")
    else:
        print(f"\n{BOLD}All Configured Accounts:{RESET}\n")
        print(f"{'#':<4} {'Label':<18} {'Username':<18} {'Email':<26} {'Token':<12} {'VS Code Profile'}")
        print(f"{DIM}─" * 100 + f"{RESET}")
        for idx, p in enumerate(profiles, 1):
            vsc = p.get("vscode_profile") or f"{DIM}(none){RESET}"
            print(f"{idx:<4} {CYAN}{p['label']:<18}{RESET} {BLUE}{p['username']:<18}{RESET} {p['email']:<26} {DIM}{mask_token(p['token']):<12}{RESET} {vsc}")
        print("")

    input(f"{DIM}Press Enter to return to main menu...{RESET}")


def main():
    while True:
        print_banner()
        print(f"{BOLD}Please select an option:{RESET}\n")
        print(f"  {CYAN}1){RESET} {BOLD}Switch Account{RESET}       {DIM}Switch global Git user & GitHub authentication{RESET}")
        print(f"  {CYAN}2){RESET} {BOLD}Add New Account{RESET}      {DIM}Save a new Git username, email & access token{RESET}")
        print(f"  {CYAN}3){RESET} {BOLD}Delete Account{RESET}       {DIM}Remove a saved account profile{RESET}")
        print(f"  {CYAN}4){RESET} {BOLD}View Accounts{RESET}        {DIM}List all configured accounts & details{RESET}")
        print(f"  {CYAN}5){RESET} {BOLD}Exit{RESET}")
        print("")

        choice = input("Enter choice [1-5]: ").strip()

        if choice == "1":
            switch_account()
        elif choice == "2":
            add_account()
        elif choice == "3":
            delete_account()
        elif choice == "4":
            view_accounts()
        elif choice == "5":
            clear_screen()
            print(f"\n{GREEN}Goodbye! {RESET}\n")
            sys.exit(0)
        else:
            print(f"{RED}Invalid choice. Please enter a number between 1 and 5.{RESET}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print(f"\n{YELLOW}Operation cancelled by user.{RESET}\n")
        sys.exit(0)
