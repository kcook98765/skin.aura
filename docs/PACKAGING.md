# Packaging the development candidate

**PUBLIC DISTRIBUTION BLOCKERS are unresolved.** This describes local artifact
preparation, not approval to distribute source or binaries. Read
[Third-party license review](THIRD-PARTY-LICENSE-REVIEW.md). A ZIP's consistency
does not establish rights, dependency installation, repository acceptance or
Kodi runtime behaviour.

## Prerequisites and version limits

Run from the repository root with Python 3.10 or newer and Git available.
Use a source checkout retaining baseline commit
`203aba5117f185a34fef773134d3cf955cbf2c7a` and its required history. Both current
source and baseline modes consult Git for the baseline inventory and provenance.
A shallow export, a GitHub source archive or a checkout missing that commit is
not sufficient; a shallow clone is usable only if the needed history is retained.

Candidate packaging must enforce `skin.aura`, `Aura`, provider `kcook98765` and
matching **2.1.0** manifest/tooling versions. Historical baseline packaging uses
**2.0.23** and must remain clearly distinguished. Verify the actual source
agreement before building; a mismatch is a build failure, not something to fix
by renaming a ZIP. The **2.1.0 DEVELOPMENT CANDIDATE** label is not a release.

The current-source payload requires the reviewed exact file list at
`tools/runtime-files.txt`. Keep it with the source tooling; do not reconstruct
it from an unchecked disk scan or use an export that omits development files.
Missing, unlisted or non-regular runtime files must be resolved through source
review before packaging, including files hidden by Git ignore rules.

## Local build command

Use an existing native Linux `/tmp` parent. The output directory must be new,
outside the source tree and have no symlink ancestors. For example, if
`/tmp/aura-build` does not already exist:

```sh
python3 -B tools/build_omega.py --output /tmp/aura-build
```

The builder creates a `skin.aura/` stage, a ZIP and `receipt.json` in that output
directory. It snapshots its selected payload, uses sorted entries, fixed ZIP
timestamps and normalized file/directory modes, then checks CRCs and source,
stage and ZIP readback consistency. Those checks are packaging checks only;
the builder explicitly does not run validation. The notice-only candidate now
approves **1,802 payload files**, adding only `THIRD-PARTY-NOTICES.txt` to the
previous 1,801-file inventory. The exact current manifest's SHA-256 is
`200b1d2aa5d11e83afa0cc725d3feb112900d74a4681a805304044ef8e831979`.
Raw build receipts and artifact hashes stay outside this source tree; consult
[Testing](TESTING.md) for the separate checker outcome and retained blockers.

For a separate historical comparison, use a different new output directory:

```sh
python3 -B tools/build_omega.py --baseline --output /tmp/aura-build-baseline
```

Baseline mode packages historical bytes using Git archive. Baseline failures
against current Omega checks remain failures, not exemptions or candidate proof.
Keep comparison artifacts clearly distinguished from the current candidate.

## Payload and archive policy

The builder's payload rules live in `tools/omega_common.py`, with exact
current-source membership in `tools/runtime-files.txt`; they are not derived
from `.gitignore` or the new archive attributes. The reviewed list covers runtime
directories and named root files, including `README`, `LICENSE.txt`,
`changelog.txt` and `THIRD-PARTY-NOTICES.txt`. The root notice is mandatory for
current builds and omitted from the genuine historical baseline. Once the
reviewed changes are committed, it will also be retained in source archives;
unlike `docs/`, it is not export-ignored. Uncommitted files are not in HEAD's archive.
Development tooling, generated shortcut includes and saved user
data do not belong in that list. The new `docs/` directory is development-only.
All bundled font notices, including the Nasalization PDF, remain assets in the
runtime tree; do not strip notices to quiet a checker or shrink a package.

`.gitattributes` marks development docs, tools and Git/editor policy files
`export-ignore`. These files, including tests, remain in Git. Git archive
exclusion is source-export hygiene only. A repository download or `git archive`
is **not documented as a supported Kodi installer** and does not replace the
builder's payload review. The new license review being excluded from the local
payload does not remove the obligation to deliver every required license,
attribution and modification notice in any eventual distribution. The root
notice and every existing supplied font license are delivered without replacing
or truncating them. Adding the notice does not clear unresolved permissions.

## Outstanding package gates

- Resolve font distribution restrictions, provenance and notice compliance;
  retain every supplied notice. A project-level license alone is insufficient.
- Candidate metadata, exact payload membership and builder expectations passed
  fresh static checks; recheck them after any subsequent implementation change.
- Replace the five legacy `resources/screenshot-01.jpg` through
  `resources/screenshot-05.jpg` only with authentic captures at an appropriate
  repository-accepted resolution. They are all **1366 × 768** and fail the
  repository screenshot dimension requirement. They remain unchanged here;
  resizing or fabricating images would not supply authentic candidate captures.
- Retain the fresh static/checker results and every warning, repeat affected
  checks after changes, and perform separately authorized disposable runtime
  acceptance. No runtime testing was performed in Phase 2.

Keep raw receipts and reports outside the source/package. They may contain
machine-specific locations and need sanitization before public sharing.
