# CommCare App Tools (`cc`)

A cross-platform CLI for interacting with CommCare HQ APIs. Supports Windows, Linux, and macOS.

## Installation

### From source (development)

```bash
git clone https://github.com/jjackson/commcare-app-tools.git
cd commcare-app-tools
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

pip install -e ".[dev]"
```

### From PyPI (coming soon)

```bash
pip install commcare-app-tools
```

After installation, the `cc` command is available in your terminal.

## Quick Start

### 1. Set up your environment

By default, `cc` is configured to talk to production (`www.commcarehq.org`).
You can see all environments with:

```bash
cc env list
cc --format table env list
```

Add a custom environment:

```bash
cc env add local http://localhost:8000 --client-id YOUR_CLIENT_ID
cc env use local
```

### 2. Authenticate

Before using the API, you need to log in via OAuth2. This opens your browser
for authentication and stores tokens locally.

```bash
cc auth login
cc auth status
```

### 3. Use the API

Once authenticated, you can interact with CommCare HQ:

```bash
# List domains you have access to
cc domain list

# List applications in a domain
cc --domain my-project app list

# List cases with filters
cc --domain my-project case list --case-type patient --limit 10

# Get a specific case
cc --domain my-project case get CASE_ID

# List form submissions
cc --domain my-project form list

# List mobile workers
cc --domain my-project user list

# Make raw API requests
cc --domain my-project api get api/case/v2/
cc api get /a/my-project/api/case/v2/ --params '{"case_type": "patient"}'
```

## Output Formats

All commands support `--format` (json, table, csv) and `--output` (write to file):

```bash
# JSON (default)
cc --domain my-project case list

# Rich table
cc --format table --domain my-project case list

# CSV
cc --format csv --domain my-project case list --output cases.csv
```

## Environment Management

`cc` supports multiple CommCare HQ environments. Each environment has its own
URL, OAuth client_id, and stored credentials.

```bash
# List environments (* marks active)
cc --format table env list

# Add a new environment
cc env add staging https://staging.commcarehq.org --client-id STAGING_CLIENT_ID

# Switch active environment
cc env use staging

# Use a specific environment for one command
cc --env production domain list

# Remove a custom environment
cc env remove staging
```

Built-in environments: `production`, `india`, `staging`.

## Authentication

`cc` uses OAuth2 Authorization Code + PKCE for authentication. The flow:

1. `cc auth login` starts a temporary local HTTP server
2. Your browser opens to CommCare HQ's login page
3. After you approve, CommCare redirects back to localhost
4. Tokens are stored in `~/.commcare/credentials.json` (or platform equivalent)
5. Access tokens auto-refresh when they expire (15-minute TTL, 15-day refresh)

Each environment has independent credentials -- logging in on production
does not affect your India or staging sessions.

### Prerequisites

Before running `cc auth login`, you need an OAuth2 application registered
on the target CommCare HQ instance:

1. Go to `https://www.commcarehq.org/oauth/applications/register/`
2. Create an application with:
   - **Client type:** Public
   - **Grant type:** Authorization code
   - **Redirect URI:** `http://127.0.0.1:8400/callback`
   - **PKCE required:** Yes (recommended)
3. Copy the **Client ID** and configure it:
   ```bash
   cc env add production https://www.commcarehq.org --client-id YOUR_CLIENT_ID
   ```

## Commands Reference

```
cc auth login              # OAuth2 browser login
cc auth logout             # Clear stored tokens
cc auth status             # Show current auth state

cc env list                # List configured environments
cc env add <name> <url>    # Add a new environment
cc env use <name>          # Switch active environment
cc env remove <name>       # Remove an environment

cc api get <path>          # Raw GET request
cc api post <path> --data  # Raw POST with JSON body

cc domain list             # List accessible domains

cc app list                # List applications
cc app get <id>            # Get application details

cc case list               # List/search cases
cc case get <id>           # Get case details

cc form list               # List form submissions
cc form get <id>           # Get form details

cc user list               # List mobile workers
cc user get <id>           # Get user details
```

### Global Options

| Flag | Env Var | Description |
|------|---------|-------------|
| `--env` | `CC_ENV` | Override active environment |
| `--domain` | `CC_DOMAIN` | CommCare domain (project space) |
| `--format` | `CC_FORMAT` | Output format: json, table, csv |
| `--output` | - | Write output to file |

## Configuration Files

| File | Purpose |
|------|---------|
| `~/.commcare/config.json` | Environment definitions, active environment |
| `~/.commcare/credentials.json` | Per-environment OAuth tokens (restricted permissions) |

Override the config directory with `CC_CONFIG_DIR` environment variable.

## Development

```bash
# Run tests
pytest

# Run linter
ruff check src/

# Run formatter
ruff format src/
```

## License

MIT - see [LICENSE](LICENSE).
