# Patch queue

Apply numbered `NNNN-name.patch` files in lexical order to a clean upstream export.
Never edit tracked files under `vendor/new-api`. Keep one behavior per patch:

- `0001-dsh-zitadel-bearer.patch`: native OIDC authentication and first-login provisioning, with Go regression tests. Billing, relay keys, groups, and PAT authorization remain upstream-owned.
- `0002-source-notice.patch`: visible modified-source link beside the preserved upstream attribution. Release preparation embeds the exact public source release URL.

To update a patch, initialize a disposable exported tree as a Git repository, commit the pristine baseline, edit and test there, then export `git diff --binary`. New files must be included in the diff. Review upstream contract changes; never force a rejected patch through fuzz or drop its tests. `scripts/prepare.py` fails when any patch does not apply.

The patch queue is licensed under AGPL-3.0, as is the resulting modified application. See the root LICENSE and upstream notices in every source export and image.
