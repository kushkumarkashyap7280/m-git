# Git & GitHub Multi-Account Profile Manager

A command-line tool for macOS and Linux to manage and switch between multiple Git identities (`user.name`, `user.email`) and GitHub authentication credentials on a single machine.

Designed for developers managing:
- Company / organizational repositories
- Personal open-source projects
- Freelance / client repositories

---

## Features

- **Global Switching**: Updates `git config --global user.name`, `user.email`, and credentials in macOS Keychain.
- **Auto-Initializing Storage**: Generates a local `profiles.json` configuration file on first execution with restricted user permissions (`chmod 600`).
- **Safe for Version Control**: The repository `.gitignore` automatically excludes `profiles.json`. Sensitive personal tokens and account details are never tracked or pushed.
- **Clipboard Integration**: Supports importing Personal Access Tokens directly from macOS clipboard (`pbpaste`) to prevent terminal escape-sequence errors.
- **API Validation**: Validates access tokens against the GitHub REST API before saving.
- **Clean CLI Interface**: Text-based interface with clear formatting and masked token previews.

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
