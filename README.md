# DSH New API

This public repository owns the official New API vendor pin, the [patch queue](patches/README.md), validation, and publication of **`ghcr.io/ahdg6/newapi`**. DSH is an HTTP consumer of this image; it does not maintain a second copy of these sources or build this server.

The official [Calcium-Ion/new-api](https://github.com/Calcium-Ion/new-api) checkout is kept unmodified under `vendor/new-api`. Its Git link records the validated upstream revision. `scripts/prepare.py` exports exact upstream sources and applies numbered patches to a fresh directory. Authentication and the source notice are separate patches; billing, model routing, groups, quotas, and PAT policy remain upstream-owned.

## Daily builds and consumption

[image.yml](.github/workflows/image.yml) runs daily at **20:23 UTC / 04:23 Asia/Taipei** (GitHub scheduling can be delayed). It fetches the latest upstream **main commit**, including unreleased changes, then applies patches, runs the full middleware/model Go tests, builds the official Dockerfile, and starts the actual image against an isolated SQLite database. A rejected patch, failed test, failed build, or failed startup prevents publication and leaves the previous `latest` usable. Incompatible upstream changes require a reviewed patch update; the workflow never weakens authentication tests or automatically resolves patch conflicts.

After validation, an upstream pin change is committed separately by the workflow. Corresponding sources are published before the image. The same workflow validates pull requests without publishing. Pushes to `main` build the checked-in pin; manual runs default to fetching upstream and can disable `update_upstream` to rebuild the pin. Publication is serialized. No workflow deploys servers or migrates existing databases.

- Image: `ghcr.io/ahdg6/newapi:latest` (last successful publication, **linux/amd64**).
- Traceable build: `ghcr.io/ahdg6/newapi:build-<run-id>-<attempt>`.
- [Release](https://github.com/ahdg6/newapi/releases) with the same build name: `patched-source.tar.gz`, `build-scripts.tar.gz`, `DSH-BUILD.json`, `SHA256SUMS`, and `image-digest.txt`.
- Production deployments should pin `ghcr.io/ahdg6/newapi@sha256:…` and retain database/configuration backups. Image rollback does not downgrade databases.

Each source archive contains the complete patched application, including tracked local Go modules and initialized nested submodules. The build-script archive contains this repository's patch queue and pipeline. `DSH-BUILD.json` identifies the distribution commit, exact upstream commits and public source release. Image OCI labels identify source ownership, upstream revision and release URL. The visible footer links to that exact release while preserving upstream attribution.

The repository is public. GHCR package visibility is configured separately: deployments need package read access unless the package is public. No private checkout or credentials are required to download public release source assets.

## Development and recovery

Requirements: Git, Python 3.12+, Go (CI uses 1.26.1), and Docker/Buildx. Frontend patch checks use the upstream Bun lockfile.

```sh
git clone --recurse-submodules https://github.com/ahdg6/newapi.git
cd newapi
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/prepare.py .build/new-api
cd .build/new-api
go test ./middleware ./model -count=1
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


The latest upstream requires explicit dashboard access-token route declarations. Native OIDC respects session-only and undeclared-route rejection while keeping PAT-specific scope evaluation on PAT credentials. Native and browser OIDC first-login paths still use upstream's distinct registration flows; ambiguous historical bindings fail closed rather than merging accounts.

## License and source availability

The modified application and this repository's patches/build scripts are AGPL-3.0; see [LICENSE](LICENSE). Upstream LICENSE, NOTICE, THIRD-PARTY-LICENSES.md, author attribution, and original-project link are preserved. Changes are described in the patch queue and in `DSH-MODIFICATIONS.md` in each source export. Full corresponding patched source and build scripts are attached to each public release before image publication. Keep the exact release available to network users for every deployed image; source archives are not disposable CI artifacts.

Tests use local identity fixtures. They verify authentication behavior and startup for the selected revision, not production Zitadel login, production database migration, all providers, or other architectures.
