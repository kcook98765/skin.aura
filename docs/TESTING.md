# Testing status and procedure

## Notice-only preparation results - 2026-10-20

The simplified preparation changes only documentation, a shipped notice and
packaging/regression tooling. It is an **uncommitted worktree candidate**, not a
new release or runtime test. The earlier full-suite results below remain separate.

| Check | Result |
| --- | --- |
| Documentation, links, attribution and unchanged manifest | 6 tests passed |
| Focused packaging, notices, confirmation and selected manifest/source regressions | 30 tests passed |
| Source assertions | 399 passed, 0 failed, 8 retained coverage warnings |
| Parsed source | 127 XML, 19 XSP, 32 AST-only expressions |
| Explicit cached Omega dependency audit | Passed; no live index fetch or dependency installation |
| Toolkit syntax, manifest, paths and package | Passed on the 1,802-file candidate |
| Runtime Python typing | Not applicable: no runtime Python files |
| Official checker | Completed, failed: five screenshot errors / three warnings; exit 1 |
| ZIP inspection | Notice verbatim; all 10 supplied font notices and LICENSE.txt preserved; CRC/source/stage/readback passed |
| Kodi runtime acceptance | Not performed or newly established |

The exact manifest adds only `THIRD-PARTY-NOTICES.txt` to the previous candidate.
The genuine 2.0.23 baseline still has its original 1,802 files and omits that
notice; equal file counts do not mean equal inventories. Existing skin XML,
fonts, artwork, manifest and license files are unchanged. The current full suite
was not rerun; 36 focused tests plus source/toolkit checks cover this bounded edit.

The five screenshot errors and all three official warnings are the same findings
listed below. The eight source-coverage warning categories also remain. None is
suppressed or treated as a pass, and technical validation supplies no missing
redistribution permission. No broad asset investigation or replacement occurred.

## Earlier Phase 2 results

Phase 2 covers local preservation, isolated preparation and static validation.
**No runtime testing was performed in Phase 2.**
Fresh local results recorded on **2026-10-20** for implementation commit
`a426f21b1c2d29a204d198dcee24b89bddc446df`; subsequent result recording changes
documentation only. These results belong to that checkpoint, not automatically
to later notice/packaging changes:

| Area | Status |
| --- | --- |
| Exact XML/XSP inventory and embedded Python-expression counts | 127 XML, 19 XSP, 32 AST-parsed expressions |
| Focused source assertions, failures and warnings | 399 passed, 0 failed, 8 retained warnings; exit 0 |
| Full discovered regression suite, including confirmation/packaging tests | 85 passed, no failures/errors/skips; exit 0 |
| Official-index required, optional and active-provider closure | No failures with supplied snapshot; exit 0; not live installation proof |
| Toolkit syntax, manifest, paths and package stages | Passed against the built 1,801-file payload |
| Toolkit Python typing | Not applicable: no runtime Python source; no Omega-stub or rendering proof |
| Official addon-check | Completed, failed: five errors / three warnings; exit 1 |
| Exact package inventory and readback | 1,801 approved files; deterministic-fixture, CRC and source/stage/ZIP readback checks passed |
| Kodi rendering, navigation, installation and functional acceptance | Not tested in Phase 2 |

Source inspection, static checks, package consistency and actual Kodi execution
are distinct evidence. None provides legal clearance; the
[public distribution blockers](THIRD-PARTY-LICENSE-REVIEW.md) remain unresolved.

### Official checker errors and warnings retained

Each of `resources/screenshot-01.jpg`, `screenshot-02.jpg`, `screenshot-03.jpg`,
`screenshot-04.jpg` and `screenshot-05.jpg` is **1366 × 768**. Each produces one
error because the checker requires **1280 × 720 or 1920 × 1080**. These inherited
assets were not resized, fabricated or replaced by untested candidate captures.

All three official warnings remain:

1. Offline replay leaves `https://forum.kodi.tv/showthread.php?tid=328558`
   unverified.
2. Offline replay leaves `https://github.com/kcook98765/skin.aura` unverified.
3. `fonts/lyrics/nasalization_license.pdf` has a non-whitelisted extension.
   The supplied license is intentionally preserved, not deleted to suppress it.

There were no official dependency errors in this run. The offline replay used
the explicitly prepared cache and the official checker completed; this is not
a clean pass or live repository-submission approval.

### Eight focused-source warning categories retained

1. Embedded Python is AST-parsed only; no Kodi modules are executed.
2. Dependency installation, native dialogs, focus and rendering need runtime tests.
3. Style/include checks cover known patterns, not full Kodi include expansion.
4. Migration assertions are scoped guards, not a full condition evaluator/renderer.
5. Offline index provenance/freshness and live availability remain separate.
6. Declared-optional branch audits found no failures but have separate coverage limits.
7. Active-provider audit covered 17 IDs with no unavailable optional edges or
   published-optional failures; this is source evidence, not provider execution.
8. Legacy Next Up/Extended Info window localization references remain diagnostic;
   localization-only references do not establish provider availability or behavior.

The separate dependency audit used a supplied official Omega snapshot with
2,336 entries and SHA-256
`5d8dcda715ee7ff4d8ae8dd327df4066bcfcf1165937c09fc64da3cf4ef2b408`.
This audit is not a fresh network fetch. Complete raw reports, process exit
receipts and artifact hashes are retained privately outside the repository.

## Project-relative static commands

Run commands from the repository root with Python 3.10 or newer. The source
checker and suite require Git and the retained baseline history described in
[Packaging](PACKAGING.md). No command below starts Kodi.

Packaging fixtures use Python's temporary-directory policy (`TMPDIR` when
provided); no workstation-specific directory is required. Use a native Linux
temporary parent under `/tmp` for builder fixtures and staged validation.

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
