#!/usr/bin/env python3
"""Export exact upstream commits and apply the ordered patch queue outside Git discovery."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def export(repo, destination, revisions, prefix=""):
    revision = git(repo, "rev-parse", "HEAD")
    revisions[prefix or "."] = revision
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError(f"upstream checkout is dirty: {repo}")
    with tempfile.TemporaryFile() as archive:
        subprocess.run(["git", "-C", str(repo), "archive", revision], stdout=archive, check=True)
        archive.seek(0)
        with tarfile.open(fileobj=archive) as source:
            source.extractall(destination, filter="data")
    for entry in git(repo, "ls-tree", "-r", revision).splitlines():
        metadata, name = entry.split("\t", 1)
        mode, kind, expected = metadata.split()
        if mode != "160000":
            continue
        child = repo / name
        if not (child / ".git").exists() or git(child, "rev-parse", "HEAD") != expected:
            raise RuntimeError(f"initialize pinned submodule first: {child}")
        export(child, destination / name, revisions, f"{prefix}{name}/")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--source-url", default="https://github.com/ahdg6/newapi/releases")
    args = parser.parse_args()
    if not re.fullmatch(r"https://github.com/ahdg6/newapi/releases(?:/tag/[A-Za-z0-9._-]+)?", args.source_url):
        parser.error("source URL must be this repository's public release URL")
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    revisions = {}
    export(ROOT / "vendor/new-api", destination, revisions)
    # Without this, git apply can discover an ancestor repository and silently
    # skip every patch when the export lives under an ignored build directory.
    environment = dict(os.environ, GIT_CEILING_DIRECTORIES=str(destination.parent))
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        environment.pop(key, None)
    patches = sorted((ROOT / "patches").glob("[0-9][0-9][0-9][0-9]-*.patch"))
    if not patches:
        raise RuntimeError("patch queue is empty")
    for patch in patches:
        for options in (("--check",), ()):
            subprocess.run(["git", "apply", *options, str(patch)], cwd=destination, env=environment, check=True)
    # This assertion also detects a silently skipped authentication patch.
    if not (destination / "middleware/dsh_oidc.go").is_file():
        raise RuntimeError("authentication patch was not applied")
    footer = destination / "web/src/components/layout/components/footer.tsx"
    content = footer.read_text()
    source_marker = "https://github.com/ahdg6/newapi/releases"
    if content.count(source_marker) != 1:
        raise RuntimeError("modified-source notice missing or ambiguous")
    footer.write_text(content.replace(source_marker, args.source_url))
    manifest = {"distribution_revision": git(ROOT, "rev-parse", "HEAD"),
                "modified_at": git(ROOT, "show", "-s", "--format=%cI", "HEAD"),
                "upstream": revisions, "patches": [p.name for p in patches],
                "source_url": args.source_url}
    (destination / "DSH-BUILD.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (destination / "DSH-MODIFICATIONS.md").write_text(
        "# DSH modified New API\n\nNative OIDC access-token authentication and first-login provisioning; "
        "modified-source footer link. Upstream billing and authorization remain upstream-owned.\n\n"
        + "Modified at: " + manifest["modified_at"] + "\n\n" + args.source_url + "\n")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    main()
