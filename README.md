# Git & GitHub Multi-Account Profile Manager

A command-line tool for macOS and Linux to manage and switch between multiple Git identities (`user.name`, `user.email`) and GitHub authentication credentials on a single machine.

Designed for developers managing:
- Company / organizational repositories
- Personal open-source projects
- Freelance / client repositories

---

## Features

- **Global Switching**: Updates `git config --global user.name`, `user.email`, and GitHub credential resolution.
- **Multi-Account GitHub Auth via `gh` CLI**: Routes `git`'s credential helper through `gh auth git-credential`, so pushes/pulls/clones from *any* tool that shells out to git — including VS Code's Source Control panel and Copilot's git operations — resolve the account you just switched to, not whichever one happened to be cached. Falls back to macOS Keychain (single-account only) if `gh` isn't installed.
- **VS Code Profile Launcher**: Optionally opens a VS Code window pinned to a named [VS Code Profile](https://code.visualstudio.com/docs/editor/profiles) when you switch accounts, so each identity gets its own editor window/extension state.
- **Auto-Initializing Storage**: Generates a local `profiles.json` configuration file on first execution with restricted user permissions (`chmod 600`).
- **Safe for Version Control**: The repository `.gitignore` automatically excludes `profiles.json`. Sensitive personal tokens and account details are never tracked or pushed.
- **Clipboard Integration**: Supports importing Personal Access Tokens directly from macOS clipboard (`pbpaste`) to prevent terminal escape-sequence errors.
- **API Validation**: Validates access tokens against the GitHub REST API before saving.
- **Clean CLI Interface**: Text-based interface with clear formatting and masked token previews.

---

## Why this exists: two separate GitHub logins

There are two independent places GitHub identity lives on your machine, and switching one does **not** switch the other:

1. **Git's credential store** (what `git push`/`pull`/`clone` and VS Code's Source Control panel use). This is what `Switch Account` below manages.
2. **VS Code's own "Sign in with GitHub"** (Accounts icon, bottom-left) — a separate OAuth session used by the GitHub Pull Requests extension, Copilot, and Settings Sync. It cannot be set from a token; it always requires an interactive sign-in in that VS Code window. This tool cannot log you into it directly, but it can open the right *VS Code Profile* window for you (see below), where each profile keeps its own independent sign-in.

### Git credential resolution (fixed via `gh` CLI)

Earlier versions of this tool stored tokens directly in the macOS Keychain, keyed by `protocol=https,host=github.com` with no username. Because multiple accounts share the same host, the Keychain lookup could return a stale entry from a previous switch — `git`/VS Code would silently authenticate as the wrong account even though `user.name`/`user.email` looked correct. It also only worked on macOS.

This is now fixed by delegating to [GitHub CLI (`gh`)](https://cli.github.com), which natively tracks multiple accounts per host and always resolves the one you last made active — and behaves the same on macOS and Linux:

```bash
brew install gh        # macOS
sudo apt install gh    # Debian/Ubuntu — see https://github.com/cli/cli/blob/trunk/docs/install_linux.md
```

Nothing else to configure — `Switch Account` and `Add New Account` automatically call `gh auth login --with-token`, `gh auth switch`, and `gh auth setup-git` for you. If `gh` isn't installed, the tool warns you and falls back to the old macOS-only Keychain method.

### VS Code Profiles (for the Accounts-panel sign-in)

1. In VS Code: Profiles icon (bottom-left) → **Create Profile**, name it to match an account (e.g. `Work`, `Personal`).
2. While that profile is active, click the **Accounts** icon → **Sign in with GitHub**, and complete the OAuth flow for that specific account. This is a one-time step per profile.
3. When adding/switching an account in this tool, enter that same profile name at the `VS Code Profile name` prompt. On switch, the tool offers to run `code -n --profile "<name>"`, opening a new window already signed in as the right account.

---

## Repository Structure

```text
gitconfigurescripts/
├── README.md               # Documentation and setup instructions
├── .gitignore              # Ignores profiles.json and credential files
├── enter-git-config.py     # Python CLI tool (recommended)
├── enter-git-config.sh     # Shell script alternative
└── profiles.json           # Local storage (created on first run, chmod 600, not committed)
```

---

## Setup Instructions

Clone or download the repository into your preferred directory (e.g., `/Users/<user>/gitconfigurescripts` or `~/gitconfigurescripts`), then set up execution using one of the methods below.

### Option 1: System-wide Binary (Recommended)

Create a symlink in `/usr/local/bin` to allow running the command from any directory:

```bash
ln -sf /Users/<user>/gitconfigurescripts/enter-git-config.py /usr/local/bin/enter-git-config
```
*(Or use `~/gitconfigurescripts/enter-git-config.py`)*

Then execute:
```bash
enter-git-config
```

---

### Option 2: Zsh Shell Alias (`~/.zshrc`)

For default macOS Zsh shells:

```bash
echo 'alias enter-git-config="python3 /Users/<user>/gitconfigurescripts/enter-git-config.py"' >> ~/.zshrc
source ~/.zshrc
```

---

### Option 3: Bash Shell Alias (`~/.bashrc`)

For Linux or Bash shells:

```bash
echo 'alias enter-git-config="python3 /home/<user>/gitconfigurescripts/enter-git-config.py"' >> ~/.bashrc
source ~/.bashrc
```

---

## Usage

Run the command from any terminal:

```bash
enter-git-config
```

### Main Menu

```text
╭────────────────────────────────────────────────────────────╮
│               GIT & GITHUB PROFILE MANAGER                 │
╰────────────────────────────────────────────────────────────╯
 Active Global User:  <user>
 Active Global Email: <user>@example.com
──────────────────────────────────────────────────────────────
Please select an option:

  1) Switch Account       Switch global Git user & GitHub authentication
  2) Add New Account      Save a new Git username, email & access token
  3) Delete Account       Remove a saved account profile
  4) View Accounts        List all configured accounts & details
  5) Exit
```

### Options

1. **Switch Account**: Displays saved profiles. Select a number to apply the chosen Git identity and GitHub credentials globally.
2. **Add New Account**: Prompts for:
   - Account Nickname (e.g., `Work`, `Personal`, `Client-Alpha`)
   - GitHub Username (e.g., `<user>`)
   - Git Email (e.g., `<user>@example.com`)
   - VS Code Profile name (optional — see [VS Code Profiles](#vs-code-profiles-for-the-accounts-panel-sign-in) above)
   - Personal Access Token (paste manually or import from clipboard)
   - Performs a test request against GitHub API and confirms validity before saving.
3. **Delete Account**: Removes a profile by ID number, username, or email.
4. **View Accounts**: Displays a table of all configured accounts with masked token previews.
5. **Exit**: Closes the application.

---

## Generating a GitHub Personal Access Token (PAT)

1. Navigate to GitHub -> Account Settings.
2. Scroll to the bottom and select **Developer settings**.
3. Select **Personal access tokens** -> **Tokens (classic)**.
4. Click **Generate new token** -> **Generate new token (classic)**.
5. Provide a label and check the **`repo`** scope (required for repository access).
6. Click **Generate token** and copy the generated token string.

---

## Security and Privacy

- **Local Storage Only**: Accounts are saved locally in `profiles.json` with permissions restricted to the current user (`chmod 600`).
- **Ignored by Git**: The `.gitignore` file ensures `profiles.json` is never committed or pushed to remote repositories.
