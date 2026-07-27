# Verified update policy

Interactive Map Builder checks for official stable releases at the beginning of a Skill task. The
check is deliberately separate from map construction: network failure, a modified installation, or
an unsupported install must never prevent inspection or building.

## Commands

```bash
interactive-map-builder update --check
interactive-map-builder update --apply
interactive-map-builder update --auto
```

- `--check` reports the latest stable GitHub Release without modifying files.
- `--apply` applies an available update when the installation passes every safety check; failures
  return a non-zero exit code.
- `--auto` is the Agent preflight. It applies an update when safe, but always returns successfully
  when offline or when the installation requires manual attention.

Checks are cached for 24 hours. Use `--force` to bypass the cache. Set
`IMB_DISABLE_AUTO_UPDATE=1` to disable the preflight. The updater sends no telemetry.

## Trust and integrity

The updater reads only the repository's latest public, non-prerelease GitHub Release. A managed
Skill ZIP update requires both the versioned Skill archive and `SHA256SUMS.txt` from that Release.
It then verifies:

1. the archive SHA-256;
2. safe ZIP paths with no symlinks, traversal, duplicate paths, or files outside the package root;
3. the packaged `PACKAGE_MANIFEST.json` name and version;
4. every listed file size and SHA-256;
5. that the extracted file set exactly matches the manifest.

Release downloads have conservative size limits. An unexpected asset host, malformed version,
missing checksum, or additional unlisted file stops the update.

## Installations eligible for automatic updates

Automatic updates are intentionally narrow:

- a clean `main` checkout whose `origin` is the official repository; or
- an unmodified Skill directory installed from a versioned Release ZIP and still matching its
  package manifest.

Dirty Git checkouts, forks, non-`main` branches, locally edited managed files, read-only directories,
and copied folders without a manifest are not overwritten. The command reports a manual update
requirement and the map task continues.

## Transaction and rollback

A Git checkout records its current commit, fast-forwards to the verified release tag, reinstalls the
Python package, and runs the offline `doctor` check. A managed ZIP installation backs up every
manifest-owned file before replacement, reinstalls the package, and runs the same doctor check.

If installation or doctor verification fails, the updater restores the previous Git commit or every
previous managed file, reinstalls the previous package, and reports the failure. User data, map
projects, examples outside the managed manifest, and generated output directories are never part of
the replacement set.

## Agent behavior after an update

When `--auto` reports `updated`, the Agent re-reads `SKILL.md` before continuing. A running task may
then use the new deterministic engine immediately; newly loaded instructions are guaranteed on the
next Skill invocation.
