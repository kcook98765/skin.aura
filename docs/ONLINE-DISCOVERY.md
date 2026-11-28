# Online discovery — Stage 6 source candidate

## Explicit widget, unchanged defaults

In the existing widget picker, the final **Online Discovery (TMDb)** heading
offers **Trending Movies (Online, TMDb)** and **Trending TV Shows (Online, TMDb)**
when TMDb Helper is enabled. Their stable shortcut IDs are
`AuraDiscoverTrendingMovies` and `AuraDiscoverTrendingTVShows`. This does not assign a
widget, automatically add a home menu entry, change settings/dependencies, enable a monitor,
or require an account. Opening the curated picker is not a provider directory
request. Only choosing and assigning this source opts that widget into loading;
an assigned home widget may subsequently load through Kodi's normal lifecycle.

Practical flow: open Skin Settings → customise home menu, choose the desired
existing menu item and widget slot, open its widget source picker, choose
Online Discovery (TMDb) → either explicitly named source, and save/back out.
Keep the online heading or another equally explicit name. Return home to browse.
In the observed native run, the widget showed ten movie cards at the existing
Home widget item limit, plus Kodi's own More folder opening the same provider
directory. This native folder is distinct from the skin's duplicate Show More,
which is suppressed for this path.
To opt out, replace/remove that slot in the same editor. All other slots and
saved bindings are retained. Exact editor wording may vary.

## Network, limits and information

This is online TMDb metadata browsing, not a catalogue of playable files.
The versioned TMDb Helper 5.4.16 dispatches `info=trending_week&tmdb_type=movie`
or `info=trending_week&tmdb_type=tv`. Both curated URLs add
`widget=true&limit=12&nextpage=false&cacheonly=true&fanarttv=false` and terminal
`reload=0`. Movies retains `plugin_category=Aura%20Online%20Discovery`; TV uses
`plugin_category=Aura%20Online%20Discovery%20TV`.
In Helper 5.4.16, `Container.get_directory` accepts this category override and
`_make_item` → `set_params_to_info` maps it into `ListItem.Property(widget)` as
`Aura Online Discovery` or `Aura Online Discovery TV`. The provider category tag
also supplies the plain-language title in its native More view. Only these two
curated routes supply those exact markers. The older curated URI existed only in disposable draft
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
suppressed for these two exact paths, not Kodi's native More folder. The fixed one-page
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
Helper 5.4.16 source supports local-library matching when explicitly enabled.
This capability is separate from verifying a controlled TV match; Aura does not
enable matching or change provider preferences on the user's behalf.

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
guards compare that InfoLabel against either
entire curated literal URL with `String.IsEqual`, including `info=trending_week`
and every flag. They do not match arbitrary Helper lists or all online widgets.
The original title and BasedOnLabel controls remain separate and unchanged,
including their offsets, styling and visibility. One new noninteractive label
shows the unavailable message only for either exact online URL when the container
has no items and is not updating. Other widget sources retain their existing
empty-state behaviour.

## Stage 6B Movies reliability — explicit Reload skin

Earlier in the native Flathub campaign, the assigned last Movies widget was
empty during an outage. Its noninteractive message was not reachable or visible
while navigating populated local rows. In the same Kodi process, connectivity
returned, but one ordinary revisit still left it empty. Aura's existing **Power
menu → Reload skin** then repopulated ten movies plus Kodi's own More folder,
using the normal TMDb cache. All 171 Aura settings were confirmed semantically
unchanged. This observation does not establish that every revisit stays empty
or that a reload guarantees recovery.

The source correction adds one **Reload skin** button to that assigned widget's
settled empty state. The initial campaign check verified vertical controller
focus from local rows: generated slot `03009` resolves to button control
`303009`. However, on
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
An ID-less spacer subsequently caused Down to remain on Categories for 17
inputs: Kodi 21.3 wires direct grouplist children into navigation by numeric ID,
including hidden/nonfocusable children. The reviewed spacer therefore has the
unique slot-derived ID `4$PARAM[id]` (control `403009` for slot `03009`), alongside
header `2$PARAM[id]` and action `3$PARAM[id]`.

After these corrections, the exact disposable Flathub pilot verified readable
last-slot Movies status and the inline Reload skin action. Invoking that action
recovered the widget in the same session in **6.69 s**; cached runs measured
**0.41–0.50 s**. Offline removal and persistence checks passed, and a warm
offline checkpoint was verified. These campaign observations supersede the
earlier outstanding focus/viewport/reload reliability status for Movies. They
do not establish that every revisit or reload will recover under all conditions.

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
Kodi or establish viewport readability by themselves; the native observations
above verify the exercised Movies path separately. TV reuses this reviewed
action, spacer and navigation without changing their layout or IDs; only the
exact-route header gate expands.

## Opt-in Trending TV — provider folder navigation

The exact TMDb Helper package inspected in the Stage 1 report has manifest
version 5.4.16. In its `resources/tmdbhelper/lib/addon/consts.py`,
`trending_week` maps to `trending/{tmdb_type}/week` via `ListBasic`.
`items/listitem.py` defaults `is_folder=True`; `_Tvshow._set_params_reroute_details`
keeps that folder and uses `flatseasons_info_param` for default Select.
`addon/plugin.py:get_flatseasons_info_param` selects `seasons` or `flatseasons`
according to the existing provider preference. A nondefault `default_select`
preference can instead select related information; Aura changes neither setting.
`items/container.py:add_items` passes the provider's folder flag to Kodi.

TV Select therefore keeps native series/season browsing. Use physical Info for
show details; Aura adds no TV Select interception or season/episode override.
The existing Movies-only per-item Select condition remains byte-for-byte
unchanged: only marker `Aura Online Discovery`, DBType `movie` and no positive
DBID qualify. The TV marker cannot qualify, even if an item reports movie type.
Both exact curated routes receive settled-empty status/reload and duplicate
Show More suppression. The visible Info Play gate recognizes only their two
exact subject markers; arbitrary Helper routes/categories retain native behavior.
No defaults, provider settings, dependencies or broader provider catalogue are added.

The native TV campaign verified cold isolated startup and a visible last-slot
status/action. The inline Reload skin action recovered ten shows plus Kodi's
More folder in the same session in **6.40 s**. Physical Info on an unmatched
title opened the correct native show details without a visible Play action;
native Select opened Seasons while idle. Both curated widgets and local rows
were also observed together. These are verified exercised paths, not a claim
that every provider response or setting combination behaves identically.

Controlled TV local-match qualification and the final combined checkpoint remain
separate qualification evidence in PR #41. The observations documented here do
not claim their completion or outcome.

## Existing Video Info buttons — visible Play gate

`DialogVideoInfo.xml` already uses native buttons alongside skin actions:
Play (8), Trailer (11, visible when a trailer exists), Refresh (6), Userrating
(7), Artwork (10), and cast/navigation controls. There is no dedicated Resume
button in this dialog source; any resume choice depends on native playback.
The existing `Items_Info` list hides its visible Play action only when the
dialog subject has exact category `Aura Online Discovery` or
`Aura Online Discovery TV` and no positive local DBID.
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

## Stage 6C-A: opt-in Discover home shortcut

Based on merged Stage 6B `f83b495`, the common home shortcut chooser now offers
localized **Discover (Online)**. It is absent from packaged Home defaults and
does not add itself on startup or upgrade. Movies/TV and their defaults remain
unchanged. This reuses the horizontal Home menu, existing Widgets and editor;
there is no new window, runtime file, service, dependency or Stage 6C-B work.

Before opting in: these are **online metadata/artwork** sources, not a promise
of playable files. Assigning either widget permits normal provider list/artwork
traffic and caching, even without pressing Select on a title. Automatic
enrichment preferences are preserved, not enabled or disabled by this shortcut.
The chooser itself supplies only the local inert `noop` action, never a plugin
invocation. Select on the Home anchor intentionally does nothing; use **Down**
to enter its assigned widgets through existing Home navigation.

### Add, configure and remove without resetting other assignments

1. Open Skin Settings → customise home menu. Use the existing **+ / Add** control
   to create a **blank shortcut**; do not repurpose Movies, TV or another populated
   shortcut. The existing editor allows up to 12 menu items; if full, stop rather
   than deleting a configured item just to follow this example.
2. With that blank selected, open **Choose shortcut** (control 401), then
   **Common → Discover (Online)**. Exact translated chooser wording may vary.
   No widget is preassigned. Choosing the anchor is separate from choosing a
   widget and does not browse a provider directory.
3. Open that entry's widget editor. In its empty primary slot choose
   **Online Discovery (TMDb) → Trending Movies (Online, TMDb)**. In a separate
   empty additional slot choose **Trending TV Shows (Online, TMDb)** from the same
   heading. The heading is visible when TMDb Helper is enabled. Use the existing
   picker, not a custom URL or preset; both qualified Helper 5.4.16 URLs and their
   inert `reload=0` stay unchanged. Leave every other assigned slot untouched.
4. Back out to save, return Home, highlight Discover and press **Down** to browse
   its widgets. Movies retains the Stage 6B native Info behavior; TV keeps native
   series/season navigation and physical Info. Playback is a separate available
   action, not something the chooser initiates.
5. To **rename**, select only this entry in the same editor and use **Set label**;
   keep “Online” or another clear network indication. To **reorder**, use its
   existing Up/Down arrow controls. Neither operation requires reassigning widgets.
6. To opt out of one widget, remove/replace only its slot. To **remove Discover**,
   select only that menu entry and use **Delete**, then back out to save. Other
   menu items and their assignments stay in place; do not use Reset/restore
   defaults. Removing an entry discards its own configuration, not a backup of it.

### Why manual widgets, not a default or preset

Official **Skin Shortcuts 2.0.3** source, `resources/lib/skinshorcuts/gui.py:2054–2126`:
control **401** handles both choosing on a blank and replacing an existing
shortcut. `_duplicate_listitem` (`2428–2506`) retains the original label ID and
additional properties, including widget assignments, but control 401 then calls
`find_default_widget` and **unconditionally writes the primary widget fields if
a matching default is returned** (`2099–2112`). There is no blank-only guard.
`find_default` (`2616–2646`) can match either retained label ID or default ID;
a replacement may also encounter historical defaults.

Consequently this change adds **no Discover `widgetdefaultnode`, `widgetdefault`,
`propertydefault`, smart properties or widget preset**, and changes none of the
historical defaults. Manual selection into new blank slots avoids that overwrite
risk; this change does not patch the dependency's replacement behavior or migrate
user assignments. All 51 historical picker bindings and the two curated online
choices remain intact.

### Recovery and verification boundary

Retain Stage 6B's explicit **Reload skin** on a settled empty curated widget.
It invokes `ReloadSkin()` for the **whole skin**, not just Discover or one row;
the existing Power menu action is also available. Restore connectivity and allow
Helper 5.4.16 / request library 0.2.28's **15-second connection-error backoff** to
expire before choosing reload. Immediate reload during outage/backoff can still
be empty. There is no automatic retry, timer, cache busting or provider-setting
change, and reload does not guarantee recovery.

Independent review passed **40 focused tests**, **128 XML parses**, and Toolkit
syntax, manifest, path and package checks. Baseline diagnostics remain unchanged;
this is not warning-free validation or official-repository approval.

The native qualifier observed the Common shortcut, manual Trending Movies and TV
assignments, unchanged other saved widget paths, both populated rows, physical
**Down** navigation and cold offline messaging. Further native results and their
exact scope belong to the qualification report and draft PR; these observations
do not establish universal provider behavior or full native acceptance. This
documentation edit repeats no tests or native operations.

## Evidence boundary

Focused static tests target Omega 21.3 contracts and retain all 51 historical
picker bindings plus the two separately counted curated sources, and all 12
direct requirements remain unchanged. These checks are not
GUI condition evaluation, provider/network tests or native acceptance. They do
not by themselves establish Toolkit or official checker validation. Campaign
validation recorded **37 focused tests passing** and **128 runtime XML parses
passing**. Static Toolkit warnings, unrelated full-suite historical findings and
kdk diagnostics match baseline; they remain recorded findings, not a claim of
warning-free validation or official-repository approval. The native observations
reported above are separate evidence, not a result of these source checks or a
claim of full native acceptance. On an earlier native build, physical Info
opened true DialogVideoInfo with the correct title and plot, but its inherited
Play action appeared primary despite no confirmed local item or configured
player. That evidence motivated the narrow visible Play gate above. The earlier
native campaign also found that Select with explicit `Action(Info,home)`
left Home unchanged while its condition referred to `Container(300)` and the
widget container, despite physical Info opening accurate Video Info. The
per-item onclick correction above addresses the two evaluation contexts and is
preserved by this TV slice. The verified Movies reliability and TV startup,
recovery, unmatched Info and idle Seasons paths are reported above; coverage is
no longer source-only for those observed paths. Controlled TV matching and the
final combined checkpoint are separate PR #41 qualification evidence, not
implied by coexistence of the widgets and local rows or by the static passes.
These bounded results do not establish full add-on acceptance or universal
playback/local-match behavior. This documentation-only update repeats no tests,
Toolkit/official checker validation or native operations.
