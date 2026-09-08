# Git & GitHub Multi-Account Profile Manager

A command-line tool for macOS and Linux to save and switch between multiple GitHub logins — updating your **Git identity** (`user.name`, `user.email`) and your **GitHub authentication** (which account `git push`/`pull` and your editor actually log in as) together, with one command.

Built for developers juggling:
- Company / organizational accounts
- Personal open-source accounts
- Freelance / client accounts

---

## Features

- **Save any number of GitHub accounts** — nickname, username, email, and Personal Access Token, validated against the GitHub API before saving.
- **Switch account in one step** — updates `git config --global user.name` / `user.email` **and** logs Git's credential system into the matching GitHub account, so `git push` immediately authenticates as the account you just switched to, not a stale/previous one.
- **View / Delete accounts** — list all saved accounts (tokens masked) or remove one by number, username, or email.
- **Optional VS Code Profile launch** — jump straight into a VS Code window already scoped to that account.
- **Secure local storage** — accounts live only in a local `profiles.json` / `profiles/*.conf`, `chmod 600`, and git-ignored — never committed, never leaves your machine.

---

## Prerequisites

Pick **one** of the two scripts — both do the same thing:

| Script | Requires | Notes |
|---|---|---|
| `enter-git-config.py` (recommended) | **Python 3** (preinstalled on macOS/most Linux) | Cross-platform, JSON storage (`profiles.json`) |
| `enter-git-config.sh` | **Nothing extra** — just `bash` (preinstalled on macOS/Linux) | No Python needed at all |

Both scripts also need, already on virtually every Mac/Linux dev machine:
- `git` and `curl`

**Strongly recommended (for correct GitHub login switching):**
- [GitHub CLI (`gh`)](https://cli.github.com) — without it, only your Git identity (`user.name`/`user.email`) switches; GitHub *authentication* falls back to a single-account macOS Keychain entry that can get out of sync across accounts.
  ```bash
  brew install gh        # macOS
  sudo apt install gh    # Debian/Ubuntu — see https://github.com/cli/cli/blob/trunk/docs/install_linux.md
  ```
  No manual `gh` setup needed beyond installing it — the tool runs `gh auth login` / `gh auth switch` / `gh auth setup-git` for you automatically.

**Optional:**
- [VS Code](https://code.visualstudio.com) with the `code` CLI on your `PATH`, only if you want the "open matching VS Code Profile" feature.

---

## Installation

Clone or download this repo anywhere, e.g. `~/gitconfigurescripts`, then make it runnable as a plain command:

```bash
# Python version (recommended)
ln -sf ~/gitconfigurescripts/enter-git-config.py /usr/local/bin/enter-git-config

# OR the no-Python shell version
ln -sf ~/gitconfigurescripts/enter-git-config.sh /usr/local/bin/enter-git-config
```

*(No permission to write to `/usr/local/bin`? Use a shell alias instead — add `alias enter-git-config="~/gitconfigurescripts/enter-git-config.py"` to your `~/.zshrc` or `~/.bashrc`, then `source` it.)*

---

## Usage

Run it from any terminal, in any directory:

```bash
enter-git-config
```

```text
╭────────────────────────────────────────────────────────────╮
│             GIT & GITHUB PROFILE MANAGER                    │
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

1. **Switch Account** — pick a saved account by number. This sets `user.name`/`user.email` globally **and** switches GitHub authentication (via `gh`) to that account, then optionally opens its VS Code profile.
2. **Add New Account** — prompts for a nickname, GitHub username, email, optional VS Code profile name, and a Personal Access Token (paste it or import from clipboard). The token is verified against the GitHub API before saving.
3. **Delete Account** — remove a saved account by its number, username, or email.
4. **View Accounts** — table of every saved account with masked tokens.
5. **Exit**

### Generating a Personal Access Token (PAT)

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
2. **Generate new token (classic)** → give it a label → check the **`repo`** scope.
3. Generate, copy the token, and paste it into **Add New Account**.

---

## How switching actually works

There are two separate places GitHub identity lives on your machine — this tool handles the first automatically and helps with the second:

1. **Git's credential system** — what `git push`/`pull`/`clone` and your editor's Source Control panel use. `Switch Account` manages this by delegating to `gh` CLI, which tracks multiple GitHub accounts natively and always resolves whichever one you last switched to (this replaces the old, single-account macOS Keychain method, which could authenticate as a stale account even after switching).
2. **VS Code's own "Sign in with GitHub"** (Accounts icon, bottom-left) — a separate OAuth session used by Copilot, the GitHub Pull Requests extension, and Settings Sync. It can't be set with a token; it always needs an interactive sign-in. To handle this, give an account a **VS Code Profile** name when adding it (Profiles icon in VS Code → Create Profile → sign in with that account's GitHub once via the Accounts icon). From then on, switching that account in this tool offers to open that exact profile window, already signed in.

---

## Repository Structure

```text
gitconfigurescripts/
├── README.md               # This file
├── .gitignore               # Ignores profiles.json / profiles/ and credential files
├── enter-git-config.py      # Python CLI (recommended)
├── enter-git-config.sh      # Shell-only CLI (no Python required)
└── profiles.json            # Local account storage (created on first run, chmod 600, never committed)
```

---

## Security and Privacy

- Accounts are stored **only locally** in `profiles.json` (Python) or `profiles/*.conf` (shell), permissions restricted to your user (`chmod 600`).
- `.gitignore` ensures this file is never committed or pushed.
- Tokens are never printed in full — only masked previews (`ghp_****...1234`) are shown.
