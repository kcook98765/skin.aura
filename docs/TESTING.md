# Testing status and procedure

## Current status

Phase 2 covers local preservation, isolated preparation and static validation.
**No runtime testing was performed in Phase 2.**
The following results are **PENDING fresh validation** for the resulting
candidate; no historical count or pass is adopted here:

| Area | Status |
| --- | --- |
| Exact XML/XSP inventory and embedded Python-expression counts | PENDING |
| Focused source assertions, failures and warnings | PENDING |
| Full discovered regression suite, including confirmation tests | PENDING |
| Official-index required, optional and active-provider closure | PENDING |
| Toolkit / official addon-check stages and warnings | PENDING |
| Exact package inventory, hashes and readback results | PENDING |
| Kodi rendering, navigation, installation and functional acceptance | Not tested in Phase 2 |

Source inspection, static checks, package consistency and actual Kodi execution
are distinct evidence. None provides legal clearance; the
[public distribution blockers](THIRD-PARTY-LICENSE-REVIEW.md) remain unresolved.

## Project-relative static commands

Run commands from the repository root with Python 3.10 or newer. The source
checker and suite require Git and the retained baseline history described in
[Packaging](PACKAGING.md). No command below starts Kodi.

Run the **full** suite using the discovery pattern, rather than only the older
single-file invocation:

```sh
python3 -B -m unittest discover -s tools -p 'test_*.py' -v
```

This includes `test_confirmation.py`, `test_omega.py` and `test_packaging.py`,
covering confirmation-dialog preservation, first-home initialization and strict
runtime-manifest regressions.
Some tests build temporary local fixtures; they do not demonstrate Kodi UI
behaviour. Do not change expected assertions to hide candidate failures.

For an offline dependency audit, supply your own existing, decompressed
**official Omega** `addons.xml`. Record its origin, retrieval date and hash.
Replace `INDEX_FROM_USER` below with that file's location; it is a placeholder,
not an included snapshot. These tools do not download an index or dependencies.

```sh
python3 -B tools/check_official_dependencies.py --index "INDEX_FROM_USER" --manifest addon.xml
python3 -B tools/check_omega.py --index "INDEX_FROM_USER" --report /tmp/aura-omega-check.json
```

The report destination must be a new file outside the project with an existing
parent. The closure audit checks required declarations, available optional
branches and their required descendants. The focused checker additionally
examines authored active-provider references. Index freshness, live resolution
and platform installation remain separate questions. Without `--index`, the
focused checker explicitly reports that official recursive closure was not
checked; that run is incomplete dependency evidence.

The `preservation:baseline-runtime` assertion compares changes against the
historical baseline and an explicit reviewed scope. Preserve unexpected-delta
failures and review them rather than expanding the scope simply to force a pass.
Verify candidate manifest and builder expectations agree on `2.1.0`; baseline
comparisons retain their historical `2.0.23` identity. The current-source exact
payload list, `tools/runtime-files.txt`, must be present and match the runtime
tree; an incomplete tooling checkout is not a successful validation environment.

When an isolated Omega-capable Kodi Agent Toolkit environment and explicit
offline index cache are available, validate the staged payload from the
[local build](PACKAGING.md), for example:

```sh
kodi-toolkit validate /tmp/aura-build/skin.aura --branch omega --cache "CACHE_FROM_USER"
```

`CACHE_FROM_USER` denotes a separately prepared toolkit cache, not the single
dependency-index file. If that environment, cache, checker branch or required
coverage is unavailable, record the stage as blocked or incomplete. Do not
silently substitute Nexus stubs or claim type coverage for XML rendering.
Inspect every stage and retain complete output, exit statuses, warnings,
skips, errors and unresolved URL checks. A zero exit is not proof that every
required stage ran or that the package satisfies repository rules.

## Future disposable runtime acceptance

These are planned checks, **not Phase 2 results**. Use synthetic media and a
disposable, recoverable Kodi 21.3 profile. Keep Estuary available and record the
actual Kodi version, platform and candidate bytes being tested.

1. Confirm official dependencies actually resolve, install and remain enabled.
   Start with optional online enrichment off; inspect stored library data and
   graceful behaviour when extra metadata or providers are unavailable.
2. Exercise first home, menu/widget editing, ordinary Yes/No confirmations,
   settings, native colour selection, favourites, video management and seek OSD
   with remote/keyboard focus, cancel and return paths.
3. Manually reselect affected old widget sources and verify returned items,
   empty lists and disabled-provider behaviour without resetting the profile.
4. Check the library airing calendar and PVR/EPG navigation with synthetic
   programmes; verify event context, date selection and information dialogs.
   Any tuning, recording or backend mutation needs its own test scope.
5. Configure Backup destination, enable **Add-on Data** and include custom asset
   folders before backing up. Verify restore in the disposable profile. Old
   Skin Helper archives are not supported; installation alone is not a backup.
6. Return through **Settings → Interface → Skin → Estuary**. Confirm the profile
   remains usable; skin rollback does not restore previous settings or widgets.

Do not include credentials, account-entry captures, saved settings or personal
content in public reports. Capture authentic screenshots at a repository-
appropriate resolution only during a later authorized runtime session. The five
legacy 1366 × 768 screenshots remain unchanged and fail repository dimensions.
