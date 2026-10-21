# Compatibility decisions

## Target and preserved history

`main` is the proposed Omega development line targeting **Kodi 21.3** and
`xbmc.gui` **5.17.0**. This is a local branch proposal, not a claim that branches
or releases have been published. Lowercase `matrix` preserves the exact history
at `203aba5117f185a34fef773134d3cf955cbf2c7a`; capitalised `Nexus` and historical
`master` retain their existing history. Do not rewrite these branches to apply
Omega decisions. No fresh Matrix or Nexus runtime support is established here.

The GUI import is a minimum API dependency, not a maximum Kodi version or proof
of behaviour on other releases. Omega evidence is pinned to Kodi source commit
[`a3a448d26b8d560a65655dab2cd122994dc4e146`](https://github.com/xbmc/xbmc/tree/a3a448d26b8d560a65655dab2cd122994dc4e146),
including the
[`xbmc.gui` manifest](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/addons/xbmc.gui/addon.xml).
Moving development documentation is not a substitute for release-pinned source.

The public **2.1.0 DEVELOPMENT CANDIDATE** label is an intended version, not proof
of matching manifest and tooling bytes. Verify their agreement before packaging;
the historical **2.0.23** baseline is a separate comparison artifact.
Earlier Phase 2 results are recorded in [Testing](TESTING.md): 85 tests and 399 source
checks passed, while the official Omega checker failed with five errors and
three warnings. Phase 2 preserves
and imports the existing migration and prepares publication metadata, packaging
and documentation; it includes no Kodi runtime testing.

## Retain Player.Cutlist

`1080i/Includes_Statusbar.xml` uses `Player.Cutlist`. Leave it unchanged. In the
pinned Omega source:

- [`xbmc/GUIInfoManager.cpp`, lines 922–924](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/xbmc/GUIInfoManager.cpp#L922-L924)
  retains the `cutlist` and `editlist` mappings as equivalents.
- [`xbmc/guilib/guiinfo/PlayerGUIInfo.cpp`, lines 639–644](https://github.com/xbmc/xbmc/blob/a3a448d26b8d560a65655dab2cd122994dc4e146/xbmc/guilib/guiinfo/PlayerGUIInfo.cpp#L639-L644)
  handles the corresponding edit-list information.

It is not an Omega removal requiring repair. Substituting `Player.Cuts` changes
semantics to cuts rather than the equivalent edit-list representation; it is
not a compatibility-only rename. This pinned source decision is not a claim
that the status-bar rendering has been runtime-tested in Phase 2.

## Existing candidate implementation direction

These describe the imported migration's source choices to review and test,
not new skin features added by publication preparation or completed functional
acceptance:

| Area | Decision and limit |
| --- | --- |
| Seek visibility | Use `Player.HasPerformedSeek(3)` rather than the removed `Player.DisplayAfterSeek`; static expression checks do not prove timing or rendering. |
| Settings / colour selection | Use native Omega settings templates and the colour-picker dialog; the predefined palette does not recreate automatic poster-derived colours. |
| Favourites / video management | Use the Omega media-window/dialog structure; focus, context and return paths still need runtime acceptance. |
| Confirmations / first home | Keep generic Yes/No confirmation behaviour separate from menu initialization; discover the confirmation regression tests along with the full suite. |
| PVR / EPG | Preserve native event context and actions; the skin alone cannot establish backend feature support. |
| Airing calendar | A library-oriented calendar using the current provider is not feature-identical to the old Next Aired guide. Empty or unavailable provider data must be handled. |
| Backup | Use `script.xbmcbackup` with an explicitly configured destination, Add-on Data and custom asset folders. Do not claim compatibility with old Skin Helper archives. |

## Official dependencies and optional enrichment

`addon.xml` is the authoritative list of direct dependency IDs and minimum
versions. Resolve non-core dependencies through the **official Kodi Add-on
repository** and let Kodi handle the transitive graph for Omega. The current
choices include Skin Shortcuts, Global Search, Image Resource Select, Embuary
Info/Helper, TMDb Helper, Skin Info Service, Backup and the declared image
resources. The old manual Skin Helper / CherryPy ZIP chain is not the migration
path. The offline audit compares declarations with an explicitly supplied
official Omega index and pinned core providers; it does not install add-ons.

Online metadata enrichment is optional and **off by default**. Stored library
ratings remain the baseline; extra scores, awards and artwork depend on
provider coverage. Rotten Tomatoes Tomatometer/audience percentages are not the
former critic-average metric, and stored TVDB ratings are not a live lookup.
No credential or account setup is required by this guide. A default-off skin
option is not a promise that all dependency activity is offline.

Saved widgets referencing removed providers are not automatically migrated.
Manually reselect each affected source in the menu/widget editor and verify
the results in a disposable profile. Do not delete caches or reset a working
profile as a prerequisite.

## Assets are separate release gates

The five legacy screenshots, `resources/screenshot-01.jpg` through
`resources/screenshot-05.jpg`, are **1366 × 768** and fail repository screenshot
dimension requirements. They remain unchanged pending authentic captures at an
appropriate accepted resolution. Static source checks cannot supply captures.

Bundled-font restrictions and icon provenance are inherited review issues, not
new Omega incompatibilities. The relevant lyric fonts are referenced in both
the `Default` and `Arial` fontsets in `1080i/Font.xml`; choosing Arial does not
remove the assets or resolve distribution rights. See the explicit
[PUBLIC DISTRIBUTION BLOCKERS](THIRD-PARTY-LICENSE-REVIEW.md).
