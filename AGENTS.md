# CommCare App Tools - Agent Guidelines

## Project Overview

This is the `commcare-app-tools` repository, which provides the `cc` CLI tool
for interacting with CommCare HQ APIs.

## Architecture

- `src/commcare_app_tools/cli/` -- Click CLI commands (thin wrappers)
- `src/commcare_app_tools/auth/` -- OAuth2 PKCE flow, token storage, authenticated sessions
- `src/commcare_app_tools/api/` -- API client, endpoint definitions, pagination
- `src/commcare_app_tools/config/` -- Environment and credential management
- `src/commcare_app_tools/formplayer/` -- FormPlayer Docker management (future)
- `src/commcare_app_tools/utils/` -- Output formatters (JSON, table, CSV)

## Key Patterns

- CLI commands should be thin -- business logic lives in `auth/`, `api/`, `config/`
- Each environment has independent OAuth credentials (client_id + user tokens)
- The `AuthenticatedClient` in `auth/session.py` handles auto-refresh of tokens
- Output formatting is centralized in `utils/output.py`
- All commands support `--format`, `--output`, `--env`, `--domain` global flags

## Testing

```bash
.\venv\Scripts\Activate.ps1
pytest
```

## Running

```bash
.\venv\Scripts\Activate.ps1
cc --help
```
