# Online discovery — Stage 6 source candidate

## Explicit widget, unchanged defaults

In the existing widget picker, the final **Online Discovery (TMDb)** heading
offers **Trending Movies (Online, TMDb)** when TMDb Helper is enabled.
The stable shortcut ID is `AuraDiscoverTrendingMovies`. This does not assign a
widget, add a home menu entry, change settings/dependencies, enable a monitor,
or require an account. Opening the curated picker is not a provider directory
request. Only choosing and assigning this source opts that widget into loading;
an assigned home widget may subsequently load through Kodi's normal lifecycle.

Practical flow: open Skin Settings → customise home menu, choose the desired
existing menu item and widget slot, open its widget source picker, choose
Online Discovery (TMDb) → Trending Movies (Online, TMDb), and save/back out.
Keep the online heading or another equally explicit name. Return home to browse.
In the observed native run, the widget showed ten movie cards at the existing
Home widget item limit, plus Kodi's own More folder opening the same provider
directory. This native folder is distinct from the skin's duplicate Show More,
which is suppressed for this path.
To opt out, replace/remove that slot in the same editor. All other slots and
saved bindings are retained. Exact editor wording may vary.

## Network, limits and information

This is online TMDb metadata browsing, not a catalogue of playable files.
The installed TMDb Helper dispatches `info=trending_week&tmdb_type=movie`.
The curated URL adds `widget=true&limit=12&nextpage=false&cacheonly=true&fanarttv=false&plugin_category=Aura%20Online%20Discovery&reload=0`.
In Helper 5.4.16, `Container.get_directory` accepts this category override and
`_make_item` → `set_params_to_info` maps it into `ListItem.Property(widget)` as
`Aura Online Discovery`. The provider category tag also preserves the plain-language
title `Aura Online Discovery` in its native More view. Only this curated route
supplies that marker. The older curated URI existed only in disposable draft
test profiles; no prior Aura release contained the curated route, so no existing
released user assignment requires migration. Draft test assignments need
reselecting to receive the marker; the exact guards intentionally do not broaden
to untagged or third-party widget routes.
In TMDb Helper 5.4.16, `ListBasic` passes `limit=12`, but
`get_paginated_items` returns the entire current response ahead of applying that
limit when `total_pages>1`. The URL therefore does not guarantee a 12-title cap.
Separately, live native testing observed one provider page of 20 movies; Aura's
existing Home widget item limit rendered ten movie cards, with Kodi's own More
folder for the same provider directory. Only the skin's duplicate Show More is
suppressed for this exact path, not Kodi's native More folder. The fixed one-page
`widget=true` / `nextpage=false` flags and the unchanged user-selected skin item
limit bound the widget experience.

`cacheonly=true` limits per-item detail enrichment; it does **not** prevent the
online list fetch. `fanarttv=false` limits auxiliary artwork-provider use.
TMDb list/artwork traffic and normal dependency (Helper/Kodi) caching remain
possible; neither the cache flags nor `limit=12` guarantee a cached 12-title list.
The current provider response and the skin item limit are separate constraints.
There is no variable reload trigger, clock/query-time cache buster, retry loop or
secondary provider.
No provider settings are changed. Native Info can request additional details
through the directory provider, independently of this bounded list request.

The terminal literal `reload=0` is inert. Native Skin Shortcuts 2.0.3 assignment
otherwise appended `&reload=$INFO[Window(Home).Property(widgetreload-movies)]`,
breaking Aura's exact-path guards and allowing library refresh changes to cause
unnecessary calls. Its versioned `library.py` function `add_widget_reload`
returns the original path immediately when it already contains `reload=`.
The static value therefore prevents assignment from injecting that variable
trigger and keeps the saved URI identical to every exact-path match. In TMDb
Helper 5.4.16, the normal `ListBasic` list operation ignores this inert parameter
for query/cache purposes; it does not force refresh or bypass normal caching.

For items marked `ListItem.Property(widget) = Aura Online Discovery`, Select
requests Kodi native Info with the explicit Home window target,
`Action(Info,home)`, only when `ListItem.DBType` is `movie` and
`!Integer.IsGreater(ListItem.DBID,0)` holds. Missing, zero and negative DBIDs
therefore qualify; positive local matches retain native click behaviour.
Untagged items, other categories and non-movie items are not intercepted.
The onclick condition uses only these per-item fields, not the slot URL,
`Container(300)` or `Container(widget)`. In Kodi 21.3,
`CGUIBaseContainer::OnClick` first calls `CGUIAction::HasActionsMeetingCondition`
without an item; `ExecuteActions` then evaluates the same condition with the
clicked `CFileItem`. Cross-container conditions are unsafe across those two
contexts. An idle empty row retains its heading with
“Unavailable or no results. Check your connection.” This is not diagnosis of a
specific network/provider error and creates no fake provider result.

Templates expose `content` as the active menu's slot path InfoLabel, not the
shortcut widget ID. The three widget label/empty-state and duplicate Show More
guards still compare that InfoLabel against the
entire curated literal URL with `String.IsEqual`, including `info=trending_week`
and every flag. They do not match arbitrary Helper lists or all online widgets.
The original title and BasedOnLabel controls remain separate and unchanged,
including their offsets, styling and visibility. One new noninteractive label
shows the unavailable message only for this exact online URL when the container
has no items and is not updating. Other widget sources retain their existing
empty-state behaviour.

## Stage 6B Movies reliability — explicit Reload skin

The current native Flathub campaign found the assigned last Movies widget
empty during an outage. Its noninteractive message was not reachable or visible
while navigating populated local rows. In the same Kodi process, connectivity
returned, but one ordinary revisit still left it empty. Aura's existing **Power
menu → Reload skin** then repopulated ten movies plus Kodi's own More folder,
using the normal TMDb cache. All 171 Aura settings were confirmed semantically
unchanged. This observation does not establish that every revisit stays empty
or that a reload guarantees recovery.

The source correction adds one **Reload skin** button to that assigned widget's
settled empty state. The campaign verified vertical controller focus from local
rows: generated slot `03009` resolves to button control `303009`. However, on
default non-mouse Home the focused button remained below the viewport. The
screenshot showed Stage Four Queue local cards clipped at the bottom, with
neither the unavailable message nor Reload skin visible. Focus reachability
alone therefore did not establish readability.

This source revision adds a nonfocusable spacer immediately after the action,
visible only when that action is visible. It reserves `widget_poster_spacer`,
the normal row extent, so the short empty state has room to scroll its heading
and focused action into view despite the non-mouse Home end spacers of `-250`
and `-210` (Big Submenu). Shared constants and populated/local row layouts are
unchanged; hidden, loading, populated or unassigned online slots add no space.
Native viewport verification of this extent correction remains outstanding.

Select explicitly invokes the same Kodi `ReloadSkin()` action as the existing Power
menu, reloading the whole skin, not just the provider row. Back returns to the
Home menu. The button is a direct child of the vertical widget grouplist with a
slot-derived control ID, not a child of the decorative horizontal heading
grouplist. The original title, BasedOnLabel and status label remain unchanged.
Its visibility requires the existing exact-curated-URI header to be visible,
zero items and no container update. Thus hidden slots, populated/loading rows,
local widgets and other Helper URLs gain no focus stop or action. There is no
synthetic provider item, automatic retry, timer or cache busting; the literal
URI (including inert `reload=0`), normal caching and automatic enrichment remain
unchanged, as do local bindings/defaults, dependencies and playback predicates.

Helper 5.4.16 with request library 0.2.28 has a 15-second connection-error
backoff. Restore connectivity and allow that backoff to expire before explicitly
reloading; reloading immediately during an outage/backoff may still yield no
results. Aura adds no waiting logic, network probe or automatic recovery.
The focused regressions guard vertical XML placement, action, combined
visibility scope and conditional scroll extent, not styling. They do not execute
Kodi or establish viewport readability. No install or Kodi run is part of this
source-only revision. No TV discovery is added.

## Existing Video Info buttons — visible Play gate

`DialogVideoInfo.xml` already uses native buttons alongside skin actions:
Play (8), Trailer (11, visible when a trailer exists), Refresh (6), Userrating
(7), Artwork (10), and cast/navigation controls. There is no dedicated Resume
button in this dialog source; any resume choice depends on native playback.
The existing `Items_Info` list hides its visible Play action only when the
dialog subject has category `Aura Online Discovery` and no positive local DBID.
`DialogVideoInfo` captures the category from `ListItem.Property(widget)` at
OnLoad alongside `Aura.Info.DBID`, and clears it at OnUnload. The gate therefore
uses the actual Info subject, not whichever cast or other control gains focus;
it works independently of the Select entry point, including normal remote Info.
A positive local match retains the original `Control.IsEnabled(8)` path, as do
untagged items and all other categories. Native stock control 8 and its behaviour
remain unchanged; only the list's visible Play entry is gated. Trailer and all
other options/defaults are unchanged. This is not a provider-player capability
test and does not install players, configure playback or promise playability.
Extended-information and artwork actions retain their existing enrichment,
provider and local-DBID guards. Actual
available buttons, provider Info dispatch, focus/return, local matches and
playback outcomes depend on Kodi 21.3, the provider and available media; static
source checks do not establish these runtime outcomes.

## Future proposal only: opt-in Discover home menu

A later, separately approved change could offer an explicitly added **Discover
(Online)** home menu item. It should never replace Movies/TV, appear by default,
assign itself during upgrades, or silently enable enrichment/accounts. Explain
online metadata/artwork traffic before the user adds it; reuse the existing menu
editor, picker and removable widget slots, initially offering only this source.
The proposed flow is Add menu item → choose Discover (Online) → explicitly choose
an online widget → save → browse → Info → separately choose available playback.
Removing the entry should restore the prior layout without resetting defaults.

## Evidence boundary

Focused static tests target Omega 21.3 contracts and retain all 51 historical
picker bindings plus this one separately counted source. These checks are not
GUI condition evaluation, provider/network tests or native acceptance. They do
not establish Toolkit or official checker validation. The native observation
reported above is separate evidence, not a result of these source checks or a
claim of full native acceptance. On the observed native build, physical Info
opened true DialogVideoInfo with the correct title and plot, but its inherited
Play action appeared primary despite no confirmed local item or configured
player. That evidence motivates the narrow visible Play gate above. Owner-supplied
native verification also found that Select with explicit `Action(Info,home)`
left Home unchanged while its condition referred to `Container(300)` and the
widget container, despite physical Info opening accurate Video Info. The
per-item onclick correction above addresses the two evaluation contexts; its
runtime outcome remains unverified. The category marker and visible Play gate
are also source-tested only. Broader validation remains incomplete.
