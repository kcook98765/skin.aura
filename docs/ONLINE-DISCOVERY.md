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
To opt out, replace/remove that slot in the same editor. All other slots and
saved bindings are retained. Exact editor wording may vary.

## Network, limits and information

This is online TMDb metadata browsing, not a catalogue of playable files.
The installed TMDb Helper dispatches `info=trending_week&tmdb_type=movie`.
The curated URL adds `widget=true&limit=12&nextpage=false&cacheonly=true&fanarttv=false&reload=0`.
`ListBasic` applies the list limit; the existing user widget item limit still
applies and may show fewer titles. The redundant skin Show More is suppressed
only for this bounded source.

`cacheonly=true` limits per-item detail enrichment; it does **not** prevent the
online list fetch. `fanarttv=false` limits auxiliary artwork-provider use.
TMDb list/artwork traffic and normal Helper/Kodi caching remain possible; there
is no variable reload trigger, clock/query-time cache buster, retry loop or secondary provider.
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

For this exact source, Select on a movie without a positive local DBID requests
Kodi native Info. Locally matched movies retain native click behaviour; non-title
items are not intercepted. An idle empty row retains its heading with
“Unavailable or no results. Check your connection.” This is not diagnosis of a
specific network/provider error and creates no fake focusable result or retry.

Templates expose `content` as the active menu's slot path InfoLabel, not the
shortcut widget ID. Conditions therefore compare that InfoLabel against the
entire curated literal URL with `String.IsEqual`, including `info=trending_week`
and every flag. They do not match arbitrary Helper lists or all online widgets.
The original title and BasedOnLabel controls remain separate and unchanged,
including their offsets, styling and visibility. One new noninteractive label
shows the unavailable message only for this exact online URL when the container
has no items and is not updating. Other widget sources retain their existing
empty-state behaviour.

## Existing Video Info buttons — assessed, not changed

`DialogVideoInfo.xml` already uses native buttons alongside skin actions:
Play (8), Trailer (11, visible when a trailer exists), Refresh (6), Userrating
(7), Artwork (10), and cast/navigation controls. There is no dedicated Resume
button in this dialog source; any resume choice depends on native playback.
Its extended-information and artwork actions retain their existing enrichment,
provider and local-DBID guards. This stage does not change that dialog, install
players, configure playback, or promise that an online title can play. Actual
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
not establish Toolkit or official checker validation. No native acceptance is
claimed; no network actions are part of the source checks.
