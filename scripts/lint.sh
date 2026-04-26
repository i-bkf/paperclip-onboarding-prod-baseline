#!/usr/bin/env bash
set -euo pipefail

status=0
while IFS= read -r file; do
  if ! bash -n "$file"; then
    status=1
  fi
done < <(find scripts tests -type f -name '*.sh' | sort)

while IFS= read -r file; do
  if ! python3 -m py_compile "$file"; then
    status=1
  fi
done < <(find app tests -type f -name '*.py' | sort)

if [ "$status" -ne 0 ]; then
  echo "lint failed"
  exit "$status"
fi

echo "lint passed"
