# Development policy

## Candidate scope

The current documentation describes the Aura Omega **2.1.0 DEVELOPMENT
CANDIDATE** for Kodi 21.3 / GUI 5.17.0. It is not a release announcement.
The add-on ID remains `skin.aura`. Candidate metadata and tooling expectations
must agree on `2.1.0`; historical baseline packaging remains distinct. Verify
that agreement against the actual source before building. Phase 2 preserves the
original, imports the existing migration into an isolated clone, and prepares
metadata, documentation, Git attributes and strict packaging with regressions.
No runtime testing was performed in Phase 2.

Original Aura: [jurialmunkey/skin.aura](https://github.com/jurialmunkey/skin.aura).
Fork: [kcook98765/skin.aura](https://github.com/kcook98765/skin.aura).
Preserve original attribution, `LICENSE.txt` and every supplied third-party
notice. The project license is CC BY-NC-SA 4.0 International; it does not replace
font or icon terms. Read [the license review](THIRD-PARTY-LICENSE-REVIEW.md).

## Local branch proposal

| Branch | Intended role | Preservation rule |
| --- | --- | --- |
| `main` | Omega development | Candidate work, not a release or support guarantee. |
| `matrix` | Historical Matrix line | Preserve the exact history at `203aba5117f185a34fef773134d3cf955cbf2c7a`; do not reconstruct it from an export. |
| `Nexus` | Retained Nexus line | Keep the capital `N` and existing history. |
| `master` | Preserved historical branch | Keep existing history; do not repurpose it as the Omega line. |

This is a proposed local layout, not a claim of publication, remote default
branch changes, tags or releases. Retained history is not fresh compatibility
acceptance. A working source checkout must also retain the builder's baseline
history; see [Packaging](PACKAGING.md).

## Source and Git policy

- Keep regression tests in Git, including both `tools/test_omega.py` and
  `tools/test_confirmation.py`. Archive exclusions are not ignore rules and
  must not be used to remove tests from source history.
- `.gitattributes` uses `* text=auto eol=lf`: Git detects text rather than
  forcing every file through text conversion. Explicit binary rules include
  fonts, images, PDF notices, ZIPs, audio and texture bundles.
- The old `addon.xml merge=ours` and `changelog.txt merge=ours` attributes were
  removed. `ours` is not a built-in content merge driver; those attributes
  depend on external driver configuration and can misleadingly imply that
  conflicts or version changes will be handled correctly. Resolve manifest
  and changelog conflicts explicitly using normal review. No custom driver
  is configured by this policy.
- Do not renormalize the whole tree or rewrite historical commits to apply
  this policy. Review line-ending changes only in files intentionally edited.
- `docs/`, `tools/` and root Git/editor policy files are marked `export-ignore`.
  They remain source development files. This governs Git archive selection,
  not Kodi installation support; the local builder has its own payload rules.
- Keep generated shortcut includes, bytecode and local work products out of
  Git under the existing ignore rules. Put build/check output outside the
  project; do not add saved profiles, backups or settings to a package.

## Review boundaries

Use project-relative commands from the repository root, as documented in
[Testing](TESTING.md) and [Packaging](PACKAGING.md). Retain complete diagnostics,
warnings and exit statuses for review. Before making anything public, sanitize
reports and captures: remove personal identifiers, machine-specific locations,
network details, secrets and saved user data.

Fresh preparation checks passed 85 regression tests and 399 source assertions;
the official Omega checker failed with five errors and three warnings. See
[Testing](TESTING.md) for the exact scope and retained limits. Publishing is
blocked until the [third-party issues](THIRD-PARTY-LICENSE-REVIEW.md), repository
asset requirements and candidate version consistency are checked and appropriate
static and runtime acceptance is recorded.
