# Core Domain Skeleton (M1-S2)

This scaffold adds the first-pass domain model and auth/workspace boundaries required for milestone M1-S2.

## Domain Entities

- `accounts`: top-level business account/tenant metadata.
- `users`: identity records with hashed credentials.
- `workspaces`: collaboration spaces under an account.
- `workspace_memberships`: user-to-workspace role map (`member`, `admin`, `owner`).

## Auth and Authorization

- Passwords use `PBKDF2-HMAC-SHA256` hashes.
- Access tokens are signed bearer tokens (`HS256`) with expiration (`exp`).
- Protected workspace routes authenticate the token and enforce role-based guards:
  - `GET /api/v1/workspaces/{workspaceId}` requires at least `member`.
  - `GET /api/v1/workspaces/{workspaceId}/members` requires at least `admin`.

## API Skeleton

- `POST /api/v1/signup`:
  - creates `account`, `user`, `workspace`, and owner membership in one flow
  - returns bearer token and workspace metadata
- `GET /healthz`: basic service readiness probe

## Local Bootstrap

Use local bootstrap to create the database and seed demo users/workspace:

```bash
./scripts/bootstrap-local-dev.sh
```
