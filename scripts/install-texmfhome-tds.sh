#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  install-texmfhome-tds.sh install ARCHIVE.tds.zip [TEXMFHOME]
  install-texmfhome-tds.sh uninstall ARCHIVE.tds.zip|PACKAGE [TEXMFHOME]

TEXMFHOME defaults to the value reported by kpsewhich.
EOF
  exit 2
}

die() {
  printf 'install-texmfhome-tds.sh: %s\n' "$*" >&2
  exit 1
}

[[ $# -ge 2 && $# -le 3 ]] || usage
action="$1"
archive_arg="$2"

case "$action" in
  install)
    [[ "$archive_arg" == *.tds.zip && -f "$archive_arg" ]] \
      || die "expected an existing .tds.zip archive: $archive_arg"
    archive_dir="$(cd -- "$(dirname -- "$archive_arg")" && pwd -P)"
    archive="$archive_dir/$(basename -- "$archive_arg")"
    package_id="$(basename -- "$archive_arg")"
    package_id="${package_id%.tds.zip}"
    ;;
  uninstall)
    package_id="$(basename -- "$archive_arg")"
    package_id="${package_id%.tds.zip}"
    ;;
  *)
    usage
    ;;
esac

[[ "$package_id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] \
  || die "invalid package name: $package_id"

if [[ $# -eq 3 ]]; then
  texmfhome="$3"
elif [[ -n "${TEXMFHOME:-}" ]]; then
  texmfhome="$TEXMFHOME"
else
  command -v kpsewhich >/dev/null 2>&1 || die "kpsewhich is required to locate TEXMFHOME"
  texmfhome="$(kpsewhich -var-value=TEXMFHOME)"
fi
[[ -n "$texmfhome" ]] || die "TEXMFHOME is empty"
mkdir -p -- "$texmfhome"
texmfhome="$(cd -- "$texmfhome" && pwd -P)"
[[ "$texmfhome" != / ]] || die "refusing to operate on the filesystem root"

command -v mktexlsr >/dev/null 2>&1 || die "mktexlsr is required"
manifest_dir="$texmfhome/.pdfannex-tds-manifests"
manifest="$manifest_dir/$package_id.files"
[[ ! -L "$manifest_dir" ]] || die "refusing to use symlinked manifest directory: $manifest_dir"

validate_member() {
  local member="$1"
  local component
  local -a components
  [[ -n "$member" && "$member" != /* && "$member" != *\\* ]] \
    || die "unsafe archive path: $member"
  IFS='/' read -r -a components <<< "$member"
  for component in "${components[@]}"; do
    [[ -n "$component" && "$component" != . && "$component" != .. ]] \
      || die "unsafe archive path: $member"
  done
}

check_no_symlink_parents() {
  local relative="$1"
  local parent
  local component
  local current="$texmfhome"
  local -a components
  parent="$(dirname -- "$relative")"
  IFS='/' read -r -a components <<< "$parent"
  for component in "${components[@]}"; do
    [[ "$component" == . ]] && continue
    current="$current/$component"
    [[ ! -L "$current" ]] || die "refusing to follow symlinked directory: $current"
  done
}

if [[ "$action" == install ]]; then
  command -v unzip >/dev/null 2>&1 || die "unzip is required"
  command -v zipinfo >/dev/null 2>&1 || die "zipinfo is required"
  [[ ! -e "$manifest" ]] || die "$package_id is already installed; uninstall it first"

  stage="$(mktemp -d)"
  trap 'rm -rf -- "$stage"' EXIT
  unzip -Z1 "$archive" > "$stage/members" \
    || die "cannot list archive: $archive"
  zipinfo -l "$archive" > "$stage/details" \
    || die "cannot inspect archive: $archive"
  if awk 'substr($1, 1, 1) == "l" { found = 1 } END { exit !found }' "$stage/details"; then
    die "symbolic links are not allowed in TDS archives"
  fi

  members=()
  while IFS= read -r member; do
    [[ -n "$member" ]] || die "archive contains an empty path"
    is_directory=0
    if [[ "$member" == */ ]]; then
      is_directory=1
      member="${member%/}"
    fi
    validate_member "$member"
    [[ "$is_directory" -eq 1 ]] || members+=("$member")
  done < "$stage/members"
  [[ ${#members[@]} -gt 0 ]] || die "archive contains no files"
  duplicates="$(printf '%s\n' "${members[@]}" | sort | uniq -d)"
  [[ -z "$duplicates" ]] || die "archive contains duplicate file paths"

  unzip -q "$archive" -d "$stage/tree" \
    || die "cannot extract archive: $archive"
  for member in "${members[@]}"; do
    source="$stage/tree/$member"
    target="$texmfhome/$member"
    [[ -f "$source" && ! -L "$source" ]] \
      || die "archive member is not a regular file: $member"
    check_no_symlink_parents "$member"
    [[ ! -e "$target" && ! -L "$target" ]] \
      || die "target already exists; refusing to overwrite: $target"
  done

  mkdir -p -- "$manifest_dir"
  manifest_tmp="$manifest_dir/.$package_id.files.$$"
  installed=()
  rollback() {
    local member
    for member in "${installed[@]}"; do
      rm -f -- "$texmfhome/$member"
    done
    rm -f -- "$manifest_tmp"
  }

  for member in "${members[@]}"; do
    target="$texmfhome/$member"
    if ! mkdir -p -- "$(dirname -- "$target")" \
      || ! cp -p -- "$stage/tree/$member" "$target"; then
      rollback
      die "failed to install archive member: $member"
    fi
    installed+=("$member")
  done
  if ! printf '%s\n' "${members[@]}" > "$manifest_tmp"; then
    rollback
    die "cannot write install manifest"
  fi
  if ! mktexlsr "$texmfhome"; then
    rollback
    mktexlsr "$texmfhome" >/dev/null 2>&1 || true
    die "mktexlsr failed; installation was rolled back"
  fi
  if ! mv -- "$manifest_tmp" "$manifest"; then
    rollback
    mktexlsr "$texmfhome" >/dev/null 2>&1 || true
    die "cannot save install manifest; installation was rolled back"
  fi
  printf 'Installed %s into %s\n' "$package_id" "$texmfhome"
else
  [[ -f "$manifest" ]] || die "no recorded installation for $package_id in $texmfhome"
  while IFS= read -r member; do
    [[ -n "$member" ]] || continue
    validate_member "$member"
    check_no_symlink_parents "$member"
    target="$texmfhome/$member"
    if [[ -d "$target" && ! -L "$target" ]]; then
      die "refusing to remove a directory in place of an installed file: $target"
    fi
    rm -f -- "$target"
  done < "$manifest"
  rm -f -- "$manifest"
  rmdir -- "$manifest_dir" 2>/dev/null || true
  mktexlsr "$texmfhome" || die "mktexlsr failed after uninstall"
  printf 'Uninstalled %s from %s\n' "$package_id" "$texmfhome"
fi
