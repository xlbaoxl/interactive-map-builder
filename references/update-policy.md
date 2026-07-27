# Verified update policy

Interactive Map Builder checks the official stable release at the beginning of a Skill task. The
check is deliberately separate from map construction: network failure, a modified installation, or
an unsupported install must never prevent inspection or building.

## Commands

```bash
interactive-map-builder update --check
interactive-map-builder update --apply
interactive-map-builder update --auto --force
```

- `--check` reports the latest stable GitHub Release without modifying files. Without `--force`, a
  valid result may be reused for up to 24 hours.
- `--apply` verifies an exact copied install when necessary, adopts it into manifest management, and
  applies an available update. Failures return a non-zero exit code.
- `--auto --force` is the Agent preflight. It performs a fresh official-release request on every
  Skill invocation, adopts and updates when safe, but always returns successfully so the map task
  can continue when offline or when manual attention is required.

Set `IMB_DISABLE_AUTO_UPDATE=1` to disable the preflight. The updater sends no telemetry.

## Cache integrity

A cached result is accepted only when all of the following still match:

1. the running package version;
2. the active Skill root when one is known;
3. the 24-hour validity window;
4. an official version that is not older than the running package.

Changing the local version or switching between Skill installations invalidates the cache. A
successful update rewrites the state as current for the newly installed version. This prevents an
older cache from producing contradictory results such as “local 0.4.1, latest 0.4.0, current.”

## Trust and integrity

The updater reads only the repository's latest public, non-prerelease GitHub Release. A managed
Skill update requires both the versioned Skill archive and `SHA256SUMS.txt` from that Release. It
then verifies:

1. the archive SHA-256;
2. safe ZIP paths with no symlinks, traversal, duplicate paths, or files outside the package root;
3. the packaged `PACKAGE_MANIFEST.json` name and version;
4. every listed file size and SHA-256;
5. that the extracted file set exactly matches the manifest.

Release downloads have conservative size limits. An unexpected asset host, malformed version,
missing checksum, or additional unlisted file stops the update.

## Installations eligible for automatic updates

Automatic updates support:

- a clean `main` checkout whose `origin` is the official repository;
- an unmodified Skill directory installed from a versioned Release ZIP and still matching its
  package manifest; or
- starting with v0.4.3, an unmanaged copied Skill whose manifest-owned files exactly match the
  checksum-verified official Release for its current version.

The third case covers normal repository-copy installers that do not preserve `.git` and do not
create `PACKAGE_MANIFEST.json`. The updater first downloads the Release for the running version,
verifies it, compares every managed file, and writes only the official manifest. Extra repository
files, user projects, data, and generated outputs remain outside management and are preserved.

Dirty Git checkouts, forks, non-`main` branches, locally edited files, read-only directories,
unverifiable copies, and ambiguous duplicate standard installations are not overwritten. The
command returns `manual_update_required` and the map task continues.

Versions before v0.4.3 do not contain the adoption logic. An already installed unmanaged
v0.3.2–v0.4.2 copy therefore needs one official v0.4.3 reinstall; subsequent compatible releases can
update normally.

## Result contract

The preflight returns structured JSON. Agents must read it rather than infer success from the exit
code:

- `current`: local and official versions match;
- `local_newer`: the running package is newer than the latest public Release;
- `updated`: the verified update completed and the offline doctor passed;
- `manual_update_required`: the latest release may be known, but the installation cannot be safely
  adopted or updated automatically;
- `update_apply_failed`: checking succeeded but download, installation, or verification failed;
- `update_check_failed`: the official latest release could not be confirmed;
- `disabled`: the environment opt-out is active.

Application failures preserve `latest_version`, `release_url`, `source`, and
`update_available=true` when those facts were already confirmed. They are never rewritten as “no
update available.” `--auto` returns exit code zero for all states so update trouble cannot block a
map task; `--apply` returns non-zero for the three failure states.

## Transaction and rollback

A Git checkout records its current commit, fast-forwards to the verified release tag, reinstalls the
Python package, and runs the offline `doctor` check. A managed installation backs up every
manifest-owned file before replacement, reinstalls the package, and runs the same doctor check.

If installation or doctor verification fails, the updater restores the previous Git commit or every
previous managed file, reinstalls the previous package, and reports the failure. User data, map
projects, examples outside the managed manifest, and generated output directories are never part of
the replacement set.

## Agent behavior after an update

At the beginning of every Skill task, run `interactive-map-builder update --auto --force` from the
Skill root and report a compact version-preflight line. When the result is `updated`, re-read
`SKILL.md` before continuing. When the result is a failure state, disclose the known official
version and reason before proceeding with the non-blocked map task.
