#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: scripts/prepare.sh OUTPUT_DIRECTORY" >&2
  exit 2
fi

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
destination=$1
if [ -e "$destination" ]; then
  echo "output directory already exists: $destination" >&2
  exit 2
fi
mkdir -p "$destination"
git -C "$root/vendor/new-api" archive HEAD | tar -x -C "$destination"
cd "$destination"
git apply --check "$root/patches/0001-dsh-zitadel-bearer.patch"
git apply "$root/patches/0001-dsh-zitadel-bearer.patch"
