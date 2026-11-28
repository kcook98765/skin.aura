# Online discovery — Stage 6

## Explicit widgets, unchanged defaults

The widget picker offers five sources under **Online Discovery (TMDb)** when
TMDb Helper is enabled. Each leaf names its media category and includes
**(Online, TMDb)**. Assign each source explicitly through the existing editor.
Opening the picker makes no provider directory request. An assigned Home widget
loads through Kodi's normal lifecycle.

Stage 6C-B adds Popular Movies, Popular TV Shows and Upcoming Movies. It preserves
both Trending routes, all 51 historical binding tuples, every default, the optional
Discover anchor and existing preferences. Dependencies and runtime packaging file
membership stay unchanged. All five sources reuse the generic widget runtime.
The picker supplies no preassignments, new settings or credentials.

These sources browse online TMDb metadata and artwork. Normal list requests,
artwork traffic and caching apply. Metadata listings carry no promise of playback
availability.

## Stage 6C-A: optional Discover home shortcut

The common shortcut chooser offers localized **Discover (Online)**. Packaged
Home defaults exclude this entry. Adding it starts with no widget assignments.
Its local `noop` action leaves Select inert. Press **Down** to enter assigned
widgets through the existing horizontal Home menu.

### Add, configure and remove

1. Open Skin Settings → customise home menu. Use **+ / Add** to create a blank
   shortcut. Keep populated entries intact. The editor supports up to 12 menu
   items. Stop if the menu is full.
2. Select the blank entry and open **Choose shortcut** (control 401).
   Choose **Common → Discover (Online)**. Translated wording may vary.
3. Open its widget editor. Choose **Online Discovery (TMDb)** and an explicitly
   named source for each desired empty slot. Keep other assignments intact.
   Keep “Online” or another clear network indication in custom labels.
4. Back out to save. Return Home, highlight Discover and press **Down**.
   Movie Select and TV folder navigation follow the interaction rules below.
5. Use **Set label** to rename the entry and the existing Up/Down controls to
   reorder it. Both operations retain its widget assignments.
6. Remove or replace an individual widget through its slot. Use **Delete** on
   Discover to remove that entry and its own configuration. Back out to save.
   Keep Reset/restore defaults unused to preserve other assignments.

### Assignment safeguards

Official Skin Shortcuts 2.0.3 source in
`resources/lib/skinshorcuts/gui.py:2054–2126` handles choosing and replacing
shortcuts through control 401. `_duplicate_listitem` (`2428–2506`) retains the
label ID and additional properties. Control 401 then calls `find_default_widget`
and writes primary widget fields whenever it returns a matching default
(`2099–2112`). `find_default` (`2616–2646`) can match retained label IDs and
default IDs. Replacement can encounter historical defaults.

Discover has no `widgetdefaultnode`, `widgetdefault`, `propertydefault`, smart
properties or preset. Manual assignment into new blank slots preserves control
over each widget. Existing defaults and dependency replacement behavior stay
unchanged.

### Independent Stage 6C-A results

Independent checks used the exact disposable Flathub Kodi 21.3 environment.
Adding Discover started with no assignments. Physical keyboard, remote-style
and mouse Home actions passed. Add, rename, reorder, widget replacement, remove
and restart passed. Previous saved labels, order and widget paths stayed intact.
The native Live TV shortcut coexisted as a saved entry. The environment had no
configured PVR channels.

Both Trending rows stayed empty after connectivity returned. Reload skin then
populated them in **12.22 s**. Local widgets remained usable during the outage.

## Stage 6C-B: exact route ledger

All entries use TMDb Helper **5.4.16**. The table identifies each dispatch,
returned media type and category marker. XML stores URI `&` characters as `&amp;`.

| Picker label / stable widget ID | Helper dispatch → TMDb API v3 path | Returned media / category marker |
| --- | --- | --- |
| Trending Movies (Online, TMDb) / `AuraDiscoverTrendingMovies` | `info=trending_week&tmdb_type=movie` → `trending/movie/week` | movies (`movie`) / `Aura Online Discovery` |
| Trending TV Shows (Online, TMDb) / `AuraDiscoverTrendingTVShows` | `info=trending_week&tmdb_type=tv` → `trending/tv/week` | series (`tvshow`, container `tvshows`) / `Aura Online Discovery TV` |
| Popular Movies (Online, TMDb) / `AuraDiscoverPopularMovies` | `info=popular&tmdb_type=movie` → `movie/popular` | movies (`movie`) / `Aura Online Discovery` |
| Popular TV Shows (Online, TMDb) / `AuraDiscoverPopularTVShows` | `info=popular&tmdb_type=tv` → `tv/popular` | series (`tvshow`, container `tvshows`) / `Aura Online Discovery TV` |
| Upcoming Movies (Online, TMDb) / `AuraDiscoverUpcomingMovies` | `info=upcoming&tmdb_type=movie` → `movie/upcoming` | movies (`movie`) / `Aura Online Discovery` |

```text
plugin://plugin.video.themoviedb.helper/?info=trending_week&tmdb_type=movie&widget=true&limit=12&nextpage=false&cacheonly=true&fanarttv=false&plugin_category=Aura%20Online%20Discovery&reload=0
plugin://plugin.video.themoviedb.helper/?info=trending_week&tmdb_type=tv&widget=true&limit=12&nextpage=false&cacheonly=true&fanarttv=false&plugin_category=Aura%20Online%20Discovery%20TV&reload=0
plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie&widget=true&limit=12&nextpage=false&cacheonly=true&fanarttv=false&plugin_category=Aura%20Online%20Discovery&reload=0
plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=tv&widget=true&limit=12&nextpage=false&cacheonly=true&fanarttv=false&plugin_category=Aura%20Online%20Discovery%20TV&reload=0
plugin://plugin.video.themoviedb.helper/?info=upcoming&tmdb_type=movie&widget=true&limit=12&nextpage=false&cacheonly=true&fanarttv=false&plugin_category=Aura%20Online%20Discovery&reload=0
```

### Popularity and release semantics

Trending uses TMDb's weekly trending list. Popular uses TMDb's popularity-ranked
catalogue. TMDb determines list ranking. These routes supply no `sort_key`.
Popularity, ratings, library addition dates and release dates
describe separate measures.

Upcoming uses TMDb's regional upcoming theatrical-release list. Region and cache
age can affect its entries and dates. Local premiere dates and streaming or
playback availability require separate verification. Titles can overlap across
the five sources.

Popular adds broad movie and series browsing. Upcoming adds forward-looking
movie discovery. Airing Today (`airing_today`) and On the Air (`on_the_air`)
overlap as series-schedule lists. They fall outside this small set. Configurable
genre discovery requires genre IDs, filter selection and a larger configuration
contract. `now_playing` dispatches to `movie/now_playing`, labeled “In Theatres”
by Helper. Calling that regional theatrical window “Recently Released” would
misstate its scope. The picker excludes these routes.

## Provider source and settings ledger

The inspected source comes from the retained official Kodi add-on package for
TMDb Helper 5.4.16. Its `addon.xml:2–4` declares that version. All paths below
are relative to the upstream add-on root. Setting defaults describe the package.
Existing configured preferences remain in effect.

| Area | Relative upstream source | Behavior |
| --- | --- | --- |
| Dispatch and media | `resources/tmdbhelper/lib/addon/consts.py:202–260`, `resources/tmdbhelper/lib/items/basedir.py:760–823`, `resources/tmdbhelper/lib/api/tmdb/lists.py:6–36` | All five routes use `ListBasic` and the `results` key. Popular supports movie/TV/person in Helper. Upcoming supports movies in its directory. Aura exposes the five movie/TV pairs above. |
| Dates | `resources/tmdbhelper/lib/api/tmdb/methods/lists.py:316–415`, `resources/tmdbhelper/lib/api/tmdb/mapping.py:394–418` | List processing reads `results` and pagination metadata. It leaves the Upcoming/Now Playing top-level `dates` minimum/maximum object unused. Mapping sends movie `release_date` and TV `first_air_date` to premiered/year. Detailed regional `release_dates` remain separate metadata. Aura adds no rolling date calculation or date bounds. |
| Language and country | `resources/settings.xml:16–99`, `resources/tmdbhelper/lib/addon/plugin.py:39–42`, `resources/tmdbhelper/lib/addon/consts.py:11–18`, `resources/tmdbhelper/lib/api/tmdb/api.py:59–80,127–132` | **Language and country** defaults to index 18, `en-US`, which also supplies the fallback. The first two characters supply language and the last two supply country. `get_request_sc` adds language, image/video language preferences and `region=iso_region`. Helper uses its own language setting independently of Kodi's UI locale. |
| Regional release filter | `resources/settings.xml:95–99`, `resources/tmdbhelper/lib/api/tmdb/api.py:70–80` | **Ignore region release filter** defaults to false. Enabling it sets `iso_region=None`. Endpoint behavior determines the effect of the region request. Aura preserves this preference. |
| Watched and unaired items | `resources/tmdbhelper/lib/items/container.py:97–127,229–255,282–286`, `resources/tmdbhelper/lib/addon/consts.py:65–66` | Existing watched/unaired filtering and label preferences apply. Upcoming belongs to `NO_UNAIRED_CHECK` and bypasses usual hide-unaired removal. It can retain unaired label formatting. Popular can be filtered by existing preferences. |
| Limits and pagination | `resources/tmdbhelper/lib/items/container.py:166–209`, `resources/tmdbhelper/lib/api/tmdb/api.py:34,111–119`, `resources/tmdbhelper/lib/api/tmdb/methods/lists.py:316–415`, `resources/settings.xml:713–723` | `widget=true` and `nextpage=false` suppress provider next-page items. `limit=12` requests a limit. Helper returns the current response before applying that limit when more pages exist. Existing `pagemulti_tmdb` defaults to 1 and supports 1–3 internal API pages. Aura retains the user-selected Home item limit. API page counts and Home card counts are separate constraints. |
| Automatic enrichment | `resources/tmdbhelper/lib/items/container.py:114–127,186–198,268–275` | `cacheonly=true` and `fanarttv=false` disable uncached automatic detail/FanartTV enrichment for the list. List requests, cached details and normal TMDb artwork traffic remain possible. Native Info can request further details. |
| Cache | `resources/tmdbhelper/lib/api/tmdb/methods/lists.py:325–327`, `resources/tmdbhelper/lib/api/tmdb/api.py:127–132`, `resources/tmdbhelper/lib/addon/consts.py:1`, `resources/settings.xml:918–947` | Lists use `get_request_sc` with `cache_days=CACHE_SHORT`, 1 day. Existing dependency request caching, cache-location/memory preferences and Kodi artwork caching remain in charge. |
| Category markers | `resources/tmdbhelper/lib/items/container.py:379`, `resources/tmdbhelper/lib/items/listitem.py:set_params_to_info` | The category override becomes `ListItem.Property(widget)`. Movie and TV markers retain their generic native More-view titles across the five leaves. |
| TV Select | `resources/tmdbhelper/lib/items/listitem.py:_Tvshow._set_params_reroute_details`, `resources/tmdbhelper/lib/addon/plugin.py:get_flatseasons_info_param` | The provider keeps series-folder navigation. Existing preferences choose seasons, flat seasons or related information. |

Public list browsing uses Helper's existing API access and requires connectivity.
It needs no personal TMDb or Trakt login and no new key or credentials. Aura
leaves optional account features, local-library matching and provider preferences
unchanged. Metadata browsing supplies no media or player configuration.

## Native Info, Select and empty-state reload

Tagged movies with DBType `movie` and no positive local DBID use
`Action(Info,home)` for Select. Missing, zero and negative DBIDs qualify.
Positive local matches retain native Select. TV retains provider folder
navigation. Physical Info opens native details.

`DialogVideoInfo.xml` captures the subject category in `Aura.Info.Category` and
DBID in `Aura.Info.DBID` at OnLoad. It clears both at OnUnload. The visible Play
entry requires the existing stock-control gate. It hides for either discovery
marker when the subject lacks a positive local DBID. Stock Play control 8,
Trailer and other buttons retain their existing behavior. Draft PR #43 and issue
#42 record the detailed local-match and playback scope.

The movie onclick condition uses per-item fields. Kodi 21.3 evaluates
`CGUIAction::HasActionsMeetingCondition` before item-aware `ExecuteActions`.
Per-item fields keep the condition scoped to the clicked subject across both
evaluations. The dialog gate continues to track its captured subject as focus
moves among dialog controls.

The three widget guards compare the active slot path with each complete URI
using `String.IsEqual`. They control empty headings, status and duplicate Show
More suppression. Custom, reordered and untagged URLs stay outside the allowlist.
Kodi's native More item remains available. The original title and BasedOnLabel
controls keep their layout and visibility rules.

A settled empty curated row shows “Unavailable or no results. Check your
connection.” This message covers an empty result or unavailable source.
It provides no specific network diagnosis. Its **Reload skin** action invokes
`ReloadSkin()` for the whole skin. Back returns to the Home menu. The action
requires a visible curated header, zero items and no container update. Its
conditional spacer reserves the normal row extent for readable focus.

Literal terminal `reload=0` keeps assignments stable. Skin Shortcuts 2.0.3's
`resources/lib/skinshorcuts/library.py:add_widget_reload` returns paths that
already contain `reload=`. This prevents injection of a variable library-refresh
trigger. Helper's `ListBasic` ignores the literal value for list query/cache
purposes. Reload skin uses normal caching and leaves cache policy unchanged.
Dependency cache policy determines whether a request fetches fresh data.
Aura adds no retry loop, refresh monitor, timer or cache buster.

Helper 5.4.16 with request library 0.2.28 has a **15-second connection-error
backoff**. Restore connectivity and allow that backoff to expire before choosing
reload. An immediate reload during an outage or backoff can remain empty.
Recovery depends on the provider and network.

## Historical Stage 6B evidence

The Flathub Movies campaign found an empty last-slot widget during an outage.
After connectivity returned, an ordinary revisit left it empty. **Power menu →
Reload skin** repopulated ten movie cards plus Kodi's More item. All **171 Aura
settings** stayed semantically unchanged.

The inline Reload skin correction first reached focus below the default
non-mouse Home viewport. The screenshot showed clipped Stage Four Queue cards
and an unreadable empty state. A conditional `widget_poster_spacer` reserved the
normal row extent after the action. An ID-less spacer then held Down navigation
on Categories for **17 inputs**. Kodi 21.3 wires direct grouplist children by
numeric ID, including hidden and nonfocusable children. The correction assigned
the spacer `4$PARAM[id]`, alongside header `2$PARAM[id]` and action `3$PARAM[id]`.
For slot `03009`, those controls are `403009`, `203009` and `303009`.
Shared layout constants and populated local rows stayed unchanged.

The corrected disposable Flathub pilot verified readable last-slot Movies status
and inline Reload skin. That action recovered the row in **6.69 s**. Cached runs
measured **0.41–0.50 s**. Offline removal and persistence checks passed.
The pilot also verified a warm offline checkpoint.

The Trending TV campaign verified cold isolated startup and visible last-slot
status/action. Inline Reload skin recovered ten shows plus Kodi's More item in
**6.40 s**. Physical Info opened the correct unmatched show details with Play
hidden. Select opened Seasons from idle. Both Trending widgets and local rows
coexisted. These historical timings describe the exercised Trending paths.

Earlier Info checks found a visible Play entry on an unmatched title. That
finding motivated the subject-scoped visible Play gate. An earlier movie Select
condition depended on Home and widget containers and left Home unchanged.
Physical Info opened accurate details. The per-item condition addressed the two
Kodi action-evaluation contexts.

## Independent Stage 6C-B results and scope

Independent validation passed **42 focused tests** and all **128 packaged XML
parses**. The exact Omega Toolkit syntax, manifest, path and package gates and
kdk checks ran independently. They matched the existing diagnostic signatures.
Existing warnings and findings remain part of the validation record.

One live session showed all five rows. Each row displayed **ten cards plus
Kodi's More item**. Native Info opened the correct title for each added category.
Unmatched titles had no visible Play entry. Popular TV Select opened **Seasons**.
Warm cached directory calls took **0.382–0.892 s**.

A cold isolated restart rendered the empty state and reload action on all five
rows. Local TV and movie widgets remained operative.

Draft PR #43 and issue #42 retain the detailed network, local-match and full
native acceptance records. The results listed here cover the verified scenarios
above. PVR-channel behavior falls outside this environment's checks because it
had no configured channels. Playback availability and release readiness require
separate evidence and approval.
