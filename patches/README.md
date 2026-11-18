# Patch queue

Apply numbered `NNNN-name.patch` files in lexical order to a clean upstream export.
Never edit tracked files under `vendor/new-api`. Keep one behavior per patch:

- `0001-dsh-zitadel-bearer.patch`: native OIDC authentication and first-login provisioning, with Go regression tests. Browser discovery must match the native issuer; discovery and background JWKS requests have bounded HTTP clients. Billing, relay keys, groups, and PAT authorization remain upstream-owned.
- `0002-source-notice.patch`: visible modified-source link beside the preserved upstream attribution. Release preparation embeds the exact public source release URL.
- `0003-zitadel-account-sync.patch`: opt-in, read-only Zitadel User API polling that disables linked local accounts for confirmed inactive, locked, or deleted identities. It preserves local disables, advances authentication versions, publishes cache updates, and revokes browser sessions. SQLite, MySQL, and PostgreSQL tests cover state handling and credential rejection.
- `0004-zitadel-model-groups.patch`: opt-in organization/project-scoped `manager`, `admin`, and `ORG_OWNER` synchronization into `default`/`external` model access, with local New API administrator precedence. The same worker reads complete role snapshots, applies fenced group mutations and revocations, and lets `external` select all registered real model groups. Existing API-key group restrictions and billing remain upstream-owned.
- `0005-zitadel-subscription-entitlement.patch`: opt-in employee subscription assignment from the `newapi-monthly-20` role. A durable record prevents repeated issuance and identifies the exact subscription to cancel after role removal.

To update a patch, initialize a disposable exported tree as a Git repository, commit the pristine baseline, edit and test there, then export `git diff --binary`. New files must be included in the diff. Review upstream contract changes; never force a rejected patch through fuzz or drop its tests. `scripts/prepare.py` fails when any patch does not apply.

The patch queue is licensed under AGPL-3.0, as is the resulting modified application. See the root LICENSE and upstream notices in every source export and image.

Authentication changes are reviewed against the [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), and [ASVS 5.0.0](https://asvs.owasp.org/). Relevant controls include issuer/subject binding (`v5.0.0-10.3.3`), signature and algorithm validation (`9.1.1`–`9.1.3`), token validity and audience (`9.2.1`–`9.2.3`), server-side credential validation (`7.2.1`), and session termination after account disable (`7.4.1`–`7.4.2`). TLS timeouts and secret-free logs also apply. Regression tests use local identity fixtures and isolated databases; they do not certify a production Zitadel deployment or claim a complete ASVS assessment.

For upstream `57345547be11b8cc0d58252622d7319545fc6fdd`, validation passed with Go 1.26.10 and Bun 1.4.4: four preparation tests; `go test ./middleware ./model ./service -count=1`; frontend typecheck and three source-notice tests; `go test ./service -run TestDSHOIDC -count=1 -v` with dedicated SQLite 3.50.4, MySQL 8.4.13, and PostgreSQL 16.15 databases. The synchronization patch adds no schema migration. CI repeats the database and image gates for each candidate upstream revision.
