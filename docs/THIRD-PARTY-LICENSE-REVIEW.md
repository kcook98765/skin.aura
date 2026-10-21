# Third-party license review

**UNRESOLVED PUBLIC DISTRIBUTION BLOCKERS**

This is a bounded review of supplied notices and identified provenance gaps,
not legal advice, permission from rightsholders or legal clearance. Do not
infer clearance from historical inclusion, a free download, a noncommercial
project license, or a successful build/check. Public source distribution can
redistribute assets just as packages do; the blockers apply to both.

These are inherited asset issues, not newly introduced Omega problems. Phase 2
does not remove or change fonts, binary assets or supplied notices. Preserve
**every supplied notice in full**, including the PDF and embedded font
metadata. This summary supplements them and must not replace or truncate them.

## Project attribution and scope

- Original Aura: [jurialmunkey/skin.aura](https://github.com/jurialmunkey/skin.aura).
- Fork: [kcook98765/skin.aura](https://github.com/kcook98765/skin.aura).
- Add-on identity: `skin.aura`.
- Project license: **Creative Commons Attribution-NonCommercial-ShareAlike
  4.0 International (CC BY-NC-SA 4.0)**,
  https://creativecommons.org/licenses/by-nc-sa/4.0/ . Retain attribution and
  identify changes; this does not relicense third-party assets.

`LICENSE.txt` is retained verbatim, including its historical “Unported” wording.
No third-party permission is inferred from that project-level notice.

## Restrictive or unclear lyric-font terms

All paths below are relative to the project root. Read each supplied notice
before making a distribution decision.

| Asset | Supplied notice and finding | Unresolved distribution question |
| --- | --- | --- |
| `fonts/lyrics/SF Distant Galaxy.ttf` | `fonts/lyrics/SF Distant Galaxy_Readme.txt`, lines **134–139**, allows free Internet distribution but explicitly prohibits inclusion **“as part of another product”** or a CD-ROM compilation and requires the complete original font package/documentation for the stated website distribution. Lines 146–147 also prohibit renaming or editing. | Bundling in a skin is not cleared by “freeware.” Resolve the product-inclusion restriction and original-package requirement before public distribution. |
| `fonts/lyrics/nasalization-rg.ttf` | `fonts/lyrics/nasalization_license.pdf`, **page 1 §2.5**, prohibits distribution, dissemination and giving away, among other transfers. **Page 1 §1.4** supplies a narrow exception for free fonts within the same company or household with the agreement included. **Page 2 §5** identifies custom licensing for uses beyond the agreement, including applications and OEM. | The company/household exception is not a public skin-distribution grant. Establish applicable application/OEM redistribution rights; do not substitute newer website terms for this bundled agreement without matching provenance. |
| `fonts/lyrics/Geomancy - Extra Bold.ttf` | `fonts/lyrics/Geomancy License.txt` describes personal-use freeware and permits distribution, but prohibits edited versions, renaming and selling; commercial use requires contacting the author. | The permission is conditional, not unrestricted redistribution or relicensing. Confirm the exact font is unmodified and the intended distribution/use fits the personal-use, free and no-renaming terms. |
| `fonts/lyrics/BOXING.ttf` | `fonts/lyrics/BOXING License.txt` permits personal use, calls for a donation for commercial use, and says not to sell/distribute for profit or alter fonts without asking first. | Do not infer unrestricted redistribution from personal-use permission or a donation statement. Confirm applicable redistribution rights and unmodified provenance; altered or for-profit distribution is not authorized without permission. |
| `fonts/lyrics/Theboldfont.ttf` | `fonts/lyrics/Theboldfont License.txt` contains a link, attribution and the description “free font”; it does not supply an explicit redistribution license. | “Free font” is insufficient evidence of permission to bundle, modify or relicense the font. Obtain terms applicable to the exact supplied file. |

Do not delete these notices, remove fonts, rewrite font names or silently swap
assets as part of a documentation fix. Resolution requires a separate,
reviewed rights/provenance decision and, if needed, an authorized asset change.

## SIL Open Font License 1.1 assets

The supplied notices provide conditional OFL permissions. Preserve their full
copyright and license text, distribute font software under the OFL, do not
sell fonts by themselves, and respect the Reserved Font Name rules for modified
versions unless the required permission exists. Do not claim these fonts are
relicensed under Aura's CC license.

| Asset | Notice to preserve | Stated Reserved Font Name(s) |
| --- | --- | --- |
| `fonts/lyrics/Exo2-BlackItalic.ttf` | `fonts/lyrics/Exo2 License.txt` | `Exo` |
| `fonts/lyrics/PollerOne.ttf` | `fonts/lyrics/Poller One_licence.txt` | `Poller`, `Poller One` |
| `fonts/lyrics/Fredoka One.ttf` | `fonts/lyrics/Fredoka One_license.txt` | `Fredoka` |
| `fonts/lyrics/Ranchers-Regular.ttf` | `fonts/lyrics/Ranchers-Regular_license.txt` | `Ranchers` |

Confirm the exact binaries and any modifications against their provenance.
The presence of an OFL notice alone is not a completed file-by-file compliance
review; retaining the notices and reserved-name conditions remains mandatory.

## Apache License 2.0 assets and Roboto provenance

`fonts/lyrics/Luckiest Guy.ttf` is accompanied by
`fonts/lyrics/Luckiest Guy_LICENSE.txt`, containing Apache License 2.0. Retain
that entire license. The five bundled Roboto files identify Apache licensing
in embedded metadata:

- `fonts/Roboto-Regular-LineSpacingMod.ttf`
- `fonts/RobotoCondensed-Bold.ttf`
- `fonts/RobotoCondensed-Light.ttf`
- `fonts/RobotoCondensed-Regular.ttf`
- `fonts/RobotoMono-Bold.ttf`

Apache §4 requires a license copy for recipients, prominent change notices in
modified files, retention of applicable copyright/attribution notices, and
preservation of applicable upstream NOTICE attributions when supplied. Preserve
embedded metadata as well; a metadata license reference is not by itself proof
that all distribution obligations have been met. Check the eventual payload
for complete license and attribution coverage for Luckiest Guy and all five
Roboto binaries rather than assuming a nearby license covers everything.

The source and modification history of **`Roboto-Regular-LineSpacingMod.ttf`
are unknown**. Its name signals a modification, not who made it or which exact
upstream source it derives from. Establish that provenance and the required
modification notices before treating the Apache obligations as satisfied. This
review does not invent an author, date or permission for that change.

## iconmonstr and other image rights

Retain the existing attribution: **Icon images from iconmonstr.com; see its
separate license terms** at https://iconmonstr.com/license/ .

The current agreement reviewed on **2026-10-20** permits use in template or
application design where the work is not the basis or main component. It also
restricts selling, redistributing, sublicensing, sharing or transferring the
work. Application-design permission must not be treated as a blanket grant to
redistribute reusable standalone icon assets in a source repository or archive.
Third-party logos and brands can require additional rights.

The original acquisition date, applicable terms and exact source-to-asset
mapping for the bundled icons are **unverified**. Current website terms do not
prove the terms under which those files were acquired. Establish that mapping
and the applicable distribution terms; attribution alone does not clear it.
No complete rights inventory for all other artwork is claimed by this bounded
review.

## Why Arial is not a workaround

`1080i/Font.xml` references the relevant lyric fonts in **both `Default` and
`Arial` fontsets**. Selecting Arial, disabling lyrics or leaving a feature
unused does not remove font binaries from a source tree or package and does
not cure redistribution restrictions. No assets or notices are removed here.

## Unresolved public-distribution gate

Before distributing source or packages, resolve and document:

1. SF Distant Galaxy's product-bundling restriction and Nasalization's public
   redistribution/application rights under the supplied agreements.
2. Applicable permission and exact-file provenance for Geomancy, BOXING and
   Theboldfont, including their personal-use, modification and distribution
   conditions rather than treating “free” as clearance.
3. OFL notice/reserved-name compliance and Apache license, attribution and
   modification-notice delivery, including the unknown LineSpacingMod history.
4. iconmonstr acquisition terms and asset mapping, plus any outstanding artwork
   rights not established by this bounded review.

Every supplied notice remains authoritative evidence and is preserved. A later
permission, compliance or replacement decision needs its own documented basis;
this review clears none of these blockers. Separately, candidate version checks,
repository-appropriate authentic screenshots, fresh static checks and future
disposable runtime acceptance remain candidate gates. **No runtime testing was
performed in Phase 2.**
