# DSH New API

This public repository owns the official New API vendor pin, the [patch queue](patches/README.md), validation, and publication of **`ghcr.io/ahdg6/newapi`**. DSH is an HTTP consumer of this image; it does not maintain a second copy of these sources or build this server.

The official [Calcium-Ion/new-api](https://github.com/Calcium-Ion/new-api) checkout is kept unmodified under `vendor/new-api`. Its Git link records the validated upstream revision. `scripts/prepare.py` exports exact upstream sources and applies numbered patches to a fresh directory. Native authentication, the source notice, Zitadel account synchronization, and optional model-group synchronization are separate patches; billing, model routing, quotas, and PAT policy remain upstream-owned.

## Daily builds and consumption

[image.yml](.github/workflows/image.yml) runs daily at **20:23 UTC / 04:23 Asia/Hong_Kong** (GitHub scheduling can be delayed). It fetches the latest upstream **main commit**, including unreleased changes, then applies patches, runs the full middleware/model/service Go tests and account-sync tests against SQLite, MySQL, and PostgreSQL, checks frontend types and the source notice, builds the official Dockerfile, and starts the actual image against an isolated SQLite database. A rejected patch, failed test, failed build, or failed startup prevents publication and leaves the previous `latest` usable. Incompatible upstream changes require a reviewed patch update; the workflow never weakens authentication tests or automatically resolves patch conflicts.

CI reads Go from the selected upstream `go.mod` and Bun from `web/package.json`'s `packageManager`. This keeps validation aligned with the Dockerfile's toolchain when upstream adopts commands such as `bun check`; a hard-coded older Bun version caused the November build failures.

After validation, an upstream pin change is committed separately by the workflow. Corresponding sources are published before the image. The same workflow validates pull requests without publishing. Pushes to `main` build the checked-in pin; manual runs default to fetching upstream and can disable `update_upstream` to rebuild the pin. Publication is serialized. No workflow deploys servers or migrates existing databases.

To publish a source change against a deployment's existing upstream version, dispatch with `update_upstream=false` and `upstream_revision=<exact 40-character upstream commit>`. The same tests, database matrix, image build, and source publication run for that commit. This produces a build-tagged image without changing the repository's vendor pin or moving `latest`; deploy the resulting image digest explicitly. The release's `DSH-BUILD.json` records the actual upstream commit.

- Image: `ghcr.io/ahdg6/newapi:latest` (last successful publication, **linux/amd64**).
- Traceable build: `ghcr.io/ahdg6/newapi:build-<run-id>-<attempt>`.
- [Release](https://github.com/ahdg6/newapi/releases) with the same build name: `patched-source.tar.gz`, `build-scripts.tar.gz`, `DSH-BUILD.json`, `SHA256SUMS`, and `image-digest.txt`.
- Production deployments should pin `ghcr.io/ahdg6/newapi@sha256:…` and retain database/configuration backups. Image rollback does not downgrade databases.

Each source archive contains the complete patched application, including tracked local Go modules and initialized nested submodules. The build-script archive contains this repository's patch queue and pipeline. `DSH-BUILD.json` identifies the distribution commit, exact upstream commits and public source release. Image OCI labels identify source ownership, upstream revision and release URL. The visible footer links to that exact release while preserving upstream attribution.

The repository is public. GHCR package visibility is configured separately: deployments need package read access unless the package is public. No private checkout or credentials are required to download public release source assets.

## Development and recovery

Requirements: Git, Python 3.12+, Go matching `vendor/new-api/go.mod`, Bun matching `vendor/new-api/web/package.json`, and Docker/Buildx. Frontend patch checks use the upstream Bun lockfile.

```sh
git clone --recurse-submodules https://github.com/ahdg6/newapi.git
cd newapi
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/prepare.py .build/new-api
cd .build/new-api
go test ./middleware ./model ./service -count=1
cd web
bun install --frozen-lockfile
bun run typecheck
bun run test src/components/layout/components/__tests__/source-notice.test.tsx
cd ..
docker build -t new-api:dsh .
```

Preparation rejects existing output directories and modified or incorrectly initialized upstream checkouts. Git archive errors are propagated, nested Git discovery cannot silently skip patches, and missing authentication/source notices abort preparation. Remove a failed disposable export before retrying with a corrected input; never build a partially prepared tree.

To evaluate an upstream change locally, fetch `main`, detach `vendor/new-api` at the candidate SHA, initialize its recursive submodules, and run the same preparation/tests/build. Keep the pin change and patch behavior change as separate commits. Patch maintenance instructions are in [patches/README.md](patches/README.md). A failed daily run requires inspecting its error and updating the affected patch or fixing the upstream incompatibility; it is not permission to publish unvalidated upstream.

## Authentication contract

Set these variables on the New API deployment:

| Variable | Value |
| --- | --- |
| `DSH_OIDC_ISSUER` | Exact HTTPS Zitadel issuer, e.g. `https://auth.nas.gxyxjt.com:10001` |
| `DSH_OIDC_AUDIENCE` | Zitadel project ID that the access token must name in `aud` |
| `DSH_OIDC_CLIENT_ID` | Zitadel public native client ID used by DSH |

Configure New API's built-in OIDC `WellKnown` to exactly
`<DSH_OIDC_ISSUER>/.well-known/openid-configuration`. Both browser and native
login must use the same issuer: the upstream `oidc_id` column stores only a
subject. A missing or different discovery URL rejects native OIDC credentials.
Changing issuer requires reviewing and migrating existing bindings first.

With all three set, New API accepts a signed Zitadel JWT **access token** in
`Authorization: Bearer` on its existing dashboard `UserAuth` routes. It checks
issuer, audience, signature, expiry, approved signing algorithm, and client ID.
The token's `sub` resolves an existing `users.oidc_id`, established by New
API's built-in OIDC login or binding. On the first authenticated
`GET /api/user/self`, an unbound subject creates one ordinary New API user
only while New API's OIDC login and registration are enabled. The new user
uses the same OIDC UserInfo username, display name, and email as the built-in
web login; UserInfo `sub` must match the verified access token. Previously
created DSH placeholder accounts are left unchanged for manual cleanup.
Username collisions keep the generated username; email collisions
reject new registration and leave existing accounts separate. The new user receives upstream's default
group, quota, and sidebar settings. A database
unique identity claim prevents duplicate native first-login accounts. It never
matches by email or grants administrator privileges. Existing New API user
status, role, group, quota, and
endpoint checks continue to apply. Routes requiring a live dashboard session
continue to reject this credential. `AdminAuth` and `RootAuth` reject it even
if the linked user has a privileged role. The relay `/v1` middleware is unchanged;
model calls still require New API model keys.

The DSH public client should use Authorization Code + PKCE and request the
scope `urn:zitadel:iam:org:project:id:<project-id>:aud` so its JWT access token
contains the configured audience. Configure refresh access in Zitadel for DSH
separately. Do not send an ID token. If Zitadel issues opaque access tokens,
this patch will reject them; configure JWT access tokens for the native client.


The latest upstream requires explicit dashboard access-token route declarations. Native OIDC respects session-only and undeclared-route rejection while keeping PAT-specific scope evaluation on PAT credentials. Native and browser OIDC first-login paths still use upstream's distinct registration flows; ambiguous historical bindings fail closed rather than merging accounts. Discovery and background signing-key refreshes use a five-second HTTP timeout.

## Synchronize disabled Zitadel accounts

Account synchronization is optional and disabled by default. Configure these
variables on the New API server to enable it:

| Variable | Value |
| --- | --- |
| `DSH_OIDC_ISSUER` | The same HTTPS Zitadel issuer used for the existing OIDC bindings |
| `DSH_OIDC_SYNC_TOKEN` | A dedicated Zitadel service-account PAT with `user.read` permission for every linked user's organization |
| `DSH_OIDC_SYNC_INTERVAL` | Go duration between scans, default `60s`; accepted range `10s` to `24h` |

Configure built-in OIDC before enabling the synchronizer, then keep the PAT in
deployment secrets. It is a server credential and must never be sent to browser
or native clients. New API's OIDC discovery URL must match the issuer exactly,
and configured OIDC endpoints must belong to that issuer. Invalid enabled
configuration rejects startup; configuration is checked again on every scan.

A background scan starts on boot on master nodes and checks all enabled users
with an `oidc_id` through Zitadel's [Get User API](https://zitadel.com/docs/reference/api/user/zitadel.user.v2.UserService.GetUserByID),
including users who have no active dashboard requests. A successful response
with the matching user ID and state `USER_STATE_INACTIVE`, `USER_STATE_LOCKED`,
or `USER_STATE_DELETED` disables the linked New API account, advances its
authentication version, refreshes its authentication cache, and revokes its
browser sessions. Dashboard JWTs, PATs, and relay/model keys then follow the
existing disabled-account checks. Already-running requests are not interrupted.
Propagation takes up to a scan interval plus scan time while Zitadel is healthy.

Active users are never automatically enabled: local administrator decisions and
previously synchronized disables remain in force. Restore the upstream account,
then explicitly enable its New API account when appropriate. Unlinked local
accounts are unaffected.

Timeouts, redirects, permission errors, HTTP 404, invalid JSON, mismatched IDs,
and unknown states leave local account status unchanged and produce an error
for operators. Token expiry, introspection `active=false`, and logout are not
account-disable signals. Rotate an expired service PAT and investigate repeated
sync errors; an unreachable identity provider delays synchronization.

For local database verification, set `TEST_MYSQL_DSN` and `TEST_POSTGRES_DSN` to
dedicated disposable databases and run `go test ./service -run TestDSHOIDC -count=1`
inside the prepared source. These tests also run against SQLite. They migrate
fixture tables and create/remove fixture data; use disposable databases.

## Synchronize model-group access from Zitadel roles

Role synchronization uses the same account-state worker and is disabled unless
both additional settings are supplied:

| Variable | Value |
| --- | --- |
| `DSH_OIDC_GROUP_SYNC_ORG_ID` | Exact organization whose business roles control model access |
| `DSH_OIDC_GROUP_SYNC_PROJECT_ID` | Exact project containing `manager` and `admin` business roles |

Both settings require `DSH_OIDC_SYNC_TOKEN` and the existing issuer/discovery
configuration. Use an organization-scoped read-only service identity with
`user.read`, `user.grant.read`, and `org.member.read` access (for example
`ORG_OWNER_VIEWER`); keep its PAT in deployment secrets. The worker reads complete
paginated project-grant and organization-member snapshots through the Management
API, and verifies each linked user's organization through the Get User API.

Within the configured organization and project, `manager` or `admin` role
assignments and organization `ORG_OWNER` membership map to the New API account
group `external`. Other linked users in that organization map to `default`.
For users outside that organization, only the managed `external` group is
revoked to `default`; unrelated custom groups are preserved. New API administrators
(local role `10` and root `100`) receive `external` independently of Zitadel roles,
including unlinked local administrators. A locally demoted unlinked administrator
in `external` returns to `default`. Portal-only administrator grants are unrelated.
This never grants New API administrator authority, enables an account, changes
quotas, rewrites API-key groups, or matches identities by email.

In this mode `external` can select every currently registered real model group
from `GroupRatio`, including groups added later. Configure the global
`UserUsableGroups` to only `default` and `gxyxjt`, register `external` with the
desired billing ratio, and place external upstream channels only in their
intended restricted groups. Existing per-key restrictions still apply.

Role removal and organization transfer revoke full group access on the next
successful scan (normally within the configured interval plus scan time).
Group changes use upstream authentication-version fencing, refresh user and
model-key caches, and revoke browser sessions; existing model keys then follow
the new group permissions. Stable scans do not rewrite users or revoke sessions.
Malformed or incomplete role results, snapshot changes during pagination, API
permission errors, and timeouts preserve existing groups and report an error;
account-state synchronization continues. Local administrator group assignment
does not depend on a successful role lookup. New accounts initially use the
upstream `default` group until their first successful scan. Already-running
requests are not interrupted.

## License and source availability

The modified application and this repository's patches/build scripts are AGPL-3.0; see [LICENSE](LICENSE). Upstream LICENSE, NOTICE, THIRD-PARTY-LICENSES.md, author attribution, and original-project link are preserved. Changes are described in the patch queue and in `DSH-MODIFICATIONS.md` in each source export. Full corresponding patched source and build scripts are attached to each public release before image publication. Keep the exact release available to network users for every deployed image; source archives are not disposable CI artifacts.

Tests use local identity fixtures. They verify authentication behavior and startup for the selected revision, not production Zitadel login, production database migration, all providers, or other architectures.
