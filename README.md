# DSH New API image

This repository builds New API `v1.0.0-rc.40` from the pinned official
[`Calcium-Ion/new-api`](https://github.com/Calcium-Ion/new-api) Git submodule
at commit `0aec08fee811ec6136828fda790551b49e410301`, plus one reviewable
DSH authentication patch. The upstream Go module name is
`github.com/QuantumNous/new-api`.
Upstream files remain unmodified. The image retains the official license and
notices from the upstream Dockerfile.

New API is AGPL-3.0. Before deploying this modified network service, publish
the exact patched source together with this repository's patch and build script
at a URL reachable by service users, and display that URL in the service's
existing About/source notice. A private GitHub repository alone is not a
source offer to users who cannot access it. Keep the source archive associated
with the deployed image digest.

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

## Local build and updates

```sh
git submodule update --init --recursive
scripts/prepare.sh /tmp/new-api-dsh-build
cd /tmp/new-api-dsh-build
go test ./middleware ./model -run '^TestDSHOIDC' -count=1
docker build -t new-api:dsh .
```

`prepare.sh` requires a fresh output directory and stops if the patch no
longer applies. GitHub Actions builds `linux/amd64` and publishes
`ghcr.io/ahdg6/newapi` with a commit SHA tag and, for successful `main` builds,
the moving `latest` tag. A `v*` push also publishes its release tag. `latest`
points to the most recently validated commit in this repository; it does not
update the pinned upstream submodule on its own. Pin deployments to an image
digest when rollback and reproducibility matter. The repository is private, so
the deployment host needs GHCR read access.

To upgrade upstream, change only the submodule commit, apply the patch to a
fresh export, run the focused authentication test, and review the resulting
image before deployment.
