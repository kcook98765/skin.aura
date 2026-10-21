# Bounded Omega source-publication proposal

Aura 2.1.0 is a personal Kodi 21.3 continuation and a **development candidate**,
not an officially validated release. Keep its implementation and appearance.
This proposal authorizes no commit, push, repository-setting change or release.

## Preserve the repository layout

| Ref | Intended state |
| --- | --- |
| `matrix` | Exact commit `203aba5117f185a34fef773134d3cf955cbf2c7a` |
| `main` | Existing Omega lineage plus reviewed documentation/notice packaging changes |
| `master` | Unchanged at `203aba5117f185a34fef773134d3cf955cbf2c7a` |
| `Nexus` | Unchanged at `3d1e74416e8df80bf17eb87ae4de049c40676037` |
| Historical tags | All retained unchanged |

## Source publication versus an installable release

Public development source can precede full runtime acceptance if its incomplete
status is stated accurately and its redistribution rights are addressed.
Screenshot dimensions and unfinished runtime tests are not themselves GitHub
source-hosting requirements.

The actual remaining source concerns are the inherited asset restrictions and
permission gaps listed in [THIRD-PARTY-NOTICES.txt](../THIRD-PARTY-NOTICES.txt).
In particular, the supplied SF Distant Galaxy and Nasalization terms do not
establish public skin-bundling permission. The other disclosed icon/font/flag
and artwork questions remain unresolved. A notice, personal purpose or an
existing public copy does not supply missing rights. This proposal does not
declare the source cleared for redistribution or require an unrelated redesign.

An installable release additionally needs representative runtime acceptance,
honest compatibility claims, and resolution of applicable checker findings.
The official Omega checker currently fails five legacy 1366x768 screenshots
and reports three warnings (two offline URLs and the retained font-license PDF).
An official repository submission needs compliant screenshots and review; a
local test ZIP is not that submission or a validated release.

## Proposed later publication steps - approval required

1. Review the notice-only changes and the specific unresolved source concerns.
   Make a separate decision about any permission or targeted asset work; no
   further broad investigation or asset replacement is authorized here.
2. Obtain approval for the exact local commit and intended publication. No
   pending working-tree change is included merely by pushing the existing HEAD.
3. Recheck local/remote refs; stop if they changed unexpectedly. Retain original
   attribution, licenses and all historical branches/tags. Do not rewrite history.
4. Dry-run an explicit push of only `matrix` and `main`; inspect the result, then
   publish only those refs after approval. Do not use force, mirror, all-tags or
   branch-deletion options. No default-branch/settings change is implied.
5. Verify the published hashes and unchanged historical refs. Keep 2.1.0 marked
   as a candidate; do not create a release/tag or deploy to Kodi as part of this.

Existing history continues to contain inherited assets. A later file deletion
would not withdraw those historical copies; any repository-wide removal policy
would need separate authorization.
