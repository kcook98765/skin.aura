# Person exploration — Stages 7A and 7B

Target: **Kodi 21.3 Omega / Aura 2.1.1**. Stages 7A and 7B passed native
acceptance on the retained disposable Flathub Kodi 21.3 pilot.

## Verified native results

Local Movie, Show and Episode Info preserved native actor search, cast roles,
artwork and fallback, ratings, and playback. Explicit profiles verified were:

* Robert Downey Jr. / Tony Stark from **Iron Man**.
* Zooey Deschanel / Jessica Day from **New Girl** and **Pilot**.
* Amitabh Bachchan / Ashwatthama from unmatched discovery movie **Kalki 2898-AD**.
* Dominic West / Jimmy McNulty from unmatched discovery TV **The Wire**.

Each credited person ID and return path passed. Mouse, physical keyboard and
remote-style interaction passed. The supplied SIS person screen showed library
and online filmography separately. Metadata was ready in **4.58 s**. The cached
isolated presentation took **27.53 s** to fully render. Cold native actor
name/role dispatch was repaired with whole escaped key arguments. Title-scoped
checks remain in place.

A scoped temporary HTTPS outage left local Video Info working. The outage path
returned in **3.67 s**. Explicit retry restored **Gwyneth Paltrow** in **3.15 s**
without restarting. The quiet period recorded **zero connections**. No
background enrichment toggles were changed.

Crew passed on **Iron Man**. The native director action opened exact credited
**Jon Favreau**. The supplied writer chooser selected exact credited **Mark
Fergus**. Both returned to the original title and focus. Settings were preserved.
Director biography data was ready in **4.74 s** and visible after **26.63 s**.
Writer biography data was ready in **4.64 s** and visible after **21.51 s**.
Measured director traffic was **one metadata and 19 artwork connections**.
Writer traffic was **one metadata and seven artwork connections**.

Crew actions depend on known movie IDs and existing local credits. Other roles
use Discovery's existing typed provider view, with no extra routes. Broader
personalized local crew filmography and strict same-name collision
disambiguation are outside these supported paths. Native receipts are recorded
in **draft #45** and **child #44**.

## Interaction and identity contract

Native Cast **50 Select stays Kodi's offline local-appearances search**. Its
cards, role labels, icon binding, missing-portrait behavior and layout stay
native. Info, Play, ratings, artwork tools, saved discovery assignments and all
enrichment/account/matching preferences are unchanged.

Compact explicit online actions share the existing credits row in `DialogVideoInfo.xml`:

Public labels use Aura's English (`en_gb`) fallback:
**31950** Online cast & crew (TMDb), **31951** Online person (TMDb). Button 9551 uses
the standard focused-color default. Its redundant override was removed without
changing geometry, routing or control IDs.

* **Online person (TMDb)** for supported native movie/TV/episode subjects.
  Prefer a positive `Container(9550).ListItem.Property(person_id)` from the
  actual visible, populated, settled fallback row. Otherwise send the captured
  positive **subject DBID and typed DBType**, selected cast name and role to SIS
  `action=dialog_actor_info,auto_search=false`. Movie/TV context matching also
  requires a captured positive title TMDb ID or `tt` IMDb identifier. Episode
  matching sends the actual **library episode DBID**. SIS reads its show and
  season/episode information. An episode TMDb ID is never used as a show ID.
* **Online cast & crew (TMDb)** for either existing discovery marker, with a captured
  positive typed movie/TV TMDb title ID. This uses SIS `action=dialog_video_info`
  even if native cast is absent, and even if the discovery subject has a local
  match. SIS's supplied title dialog then opens its cast by numeric `person_id`.
  A missing/invalid discovery title ID hides the action. No IMDb/name guess.

The explicit button does **not** require automatic online enrichment enabled.
It is deliberate permission for an online dialog, not an enrichment-setting
change. SIS must be enabled and Cast must not be hidden in skin settings.
Empty/loading cast contexts offer no native-person action. Unsupported native
seasons, sets and music videos get no new person route. Missing data returns
through the existing navigation. The button never starts a global name search.

Down from cast enters the secondary action when visible, otherwise the next
existing row. Up/Back returns to the visible cast container without resetting
its selected index. If neither exists it returns to the top controls. SIS's
`focus=50` / `focus=9550` restores the originating card after actor-dialog close
or resolution failure. Discovery uses `focus=9551`. Up/Back then returns to its
cast row or top controls. Native return paths passed in the scenarios above.

Actor names/roles use Kodi **whole-argument** escaping:
`$ESCINFO[Window(movieinformation).Property(Aura.Info.Cast50.Name),name=]`
and the equivalent `role=` form, not `name=$ESCINFO[...]`, URL encoding or raw
`$INFO`. Native 50 snapshots name/role/position/subject DBID on focus/blur. A
freshness guard rejects a stale snapshot and returns to cast without a request.
These properties clear on new title/unload. Capture and whole-argument dispatch
passed in Stage 7A. Stage 7B leaves them unchanged.
`separator=` keeps a single selected name intact (including ` / `). Typed IDs
come from OnLoad-captured `Aura.Info.*`, never a subsequently focused cast or
Similar item's DBID. No new request occurs on dialog open or focus. Existing
opt-in background/fallback content policy is not changed. Old explicitly
enabled fallback-card Select and legacy online menu entry reuse this one SIS
dispatch. Their Embuary global name-only queries are removed. Offline fallback
still opens the appropriate literal native actor browser for manual selection.

## Stage 7B — bounded native movie crew

The existing 60-pixel action row (9552) retains person action **9551** and adds
compact **9553 Online directors (TMDb)** / **9554 Online writers (TMDb)**,
localized as **31952/31953**. These IDs were unused before this extension. No
new runtime file, dependency, settings option, widget assignment or person UI.
Native 50 Select, local director display/search, Info/Play/ratings/artwork and
existing enrichment/account preferences are not replaced.

Both new actions require enabled SIS, visible credits preference, a native
**movie** with positive captured library DBID and positive captured **movie
TMDb ID**, and a nonempty corresponding OnLoad-captured Director/Writer value.
These strings gate availability only: they are **never sent as a person name**.
Opening each new title replaces them. Unload clears them. Missing role, missing
IDs, IMDb-only identity, TV, episodes, seasons, sets and music videos hide the
unsupported action. The presence of a local credit does not guarantee TMDb has
the corresponding credit. The provider may return without opening a dialog.

Select alone dispatches:

```text
RunScript(script.skin.info.service,action=dialog_actor_info,crew=director,dbtype=movie,tmdb_id=<captured positive movie ID>,auto_search=false,focus=9553)
RunScript(script.skin.info.service,action=dialog_actor_info,crew=writer,dbtype=movie,tmdb_id=<captured positive movie ID>,auto_search=false,focus=9554)
```

No `name`, `query`, guessed person ID or focused cast/Similar-item ID is passed.
SIS 2.0.2 `lib/script/person.py:51–96,185–232` uses the typed title's crew credits,
opens the one exact credited person, or supplies its own photo/job picker when
several exist. Cancel/miss returns safely. Script focus restoration returns to
9553/9554. `lib/data/api/person.py:get_crew_from_tmdb` filters supported crew jobs
and deduplicates by person ID. Its writer category can include writing jobs
beyond the literal Writer credit. Aura does not match the native names against
TMDb or start global name search. Existing provider caches/preferences apply.
An explicit action can make network requests even with enrichment disabled.

Left/Right skips hidden actions. Down from cast/top-without-cast enters the
first available action. Up/Back returns to the prior cast container without
resetting its index, or top controls if there is no cast. The same row can show
director/writer actions without any cast. No API call is added on render/focus.

Discovery movie/TV items keep the **single existing exact SIS title view**,
now labeled Online cast & crew. No duplicate director/writer buttons appear,
including on discovery items with a local match. That provider view's exact person-ID
crew includes directors, writers, producers and other credits. Online-title
crew exploration remains there, not a new Aura route or Stage 8 redesign.

Focused source tests cover exact roles and typed IDs, missing credits, unsupported
media, focus, hidden-action navigation, consent, and preserved Discovery routing.
Native execution and return paths are recorded above.

## Exact provider comparison

The retained official provider package sources were inspected read-only.
Their manifests identify SIS **2.0.2**, Embuary Info and Helper **2.0.8**,
TMDb Helper **5.4.16**, and
Global Search **9.0.7**. The authenticated pilot confirmed these versions.
Minimum manifest imports are not claims that every older satisfying provider
has these dialog APIs.

| Component | Cast, biography and pictures | Filmography / crew and identity |
| --- | --- | --- |
| Kodi 21.3 | Existing native 50 supplies actor names, roles and portraits/icons. No new online biography or image gallery is supplied by this change. | Core Select remains local appearances, based on library cast identity/name, not a TMDb-person guarantee. Director/writer display remains unchanged. Kodi/local art and texture caching are separate from provider caches. Tagged-core behavior is inherited from the earlier source audit, not a new native-core audit here. |
| Skin Info Service 2.0.2 | `dialog_actor_info` supplies biography, profile and images. `lib/plugin/cast.py:75–106` maps name/role to Label/Label2, icon/thumb (DefaultActor fallback), and online numeric `person_id`. | Actor dialog supplies library movies/TV, online movies/TV/all acting credits, crew credits and images. Exact person ID avoids matching. Typed DBID+name/role resolves against title/episode credits with auto-search disabled. Within-credit exact/name/fuzzy matching is still possible, not strict identity proof. Crew resolution supports director, writer and creator. Aura exposes director and writer actions for identified local movies. |
| Embuary Info 2.0.8 | Own person/video dialogs provide biography/profile images, cast roles, filmography and title crew. | Actual `tmdb_id` supports exact `call=person/movie/tv`. README examples misspell it `tmbd_id`. Implementation reads `tmdb_id`. DBID resolution can fall back to title/year, and person queries use global search. Person filmography in this version uses movie/TV **cast** credits (with filtering/local-match annotations). That is not a dedicated person crew-filmography list. A second dialog stack/cache would duplicate the chosen SIS experience. No new route added. |
| Embuary Helper 2.0.8 | Local cast utilities expose names, roles, thumbnails, not the rich person-biography/gallery dialog used here. | `info=getitemsbyactor` with `dblabel` filters local movies/shows. With DBID it selects a random top cast member, not the selected card. `info=getdirectedby` supplies local director movies. These name/library routes do not establish numeric online-person identity. |
| TMDb Helper 5.4.16 | Typed title `info=cast` / `info=crew` return person listings. Person details/images and acting/crew directories exist. | `info=details&tmdb_type=person&tmdb_id=…`, `stars_in_movies/tvshows/both`, `crew_in_movies/tvshows/both`, `credits_in_both`, `images` are relevant alternatives. Typed movie/TV/person IDs matter because namespaces overlap. Existing discovery listings remain here. Adding parallel person directories/dialogs would split navigation/provider requests. |
| Global Search 9.0.7 | Library actor thumbnails/results, not an online biography/profile-image catalogue. | `RunScript(script.globalsearch,searchstring=…&actors=true&tvactors=true)` searches local movie/TV cast by name (one ampersand-delimited argument, URL-encoded query). `directors=true` is movie-only. Internal actormovies/actortvshows/directormovies drilldowns use library filters. No online filmography, writer/person-crew identity route is introduced. Existing category search remains unchanged. |

### SIS route and default-control evidence

Paths below are relative to `script.skin.info.service/`:

* `script.py` → `lib/script/script.py`. Actor handler **674–734**, video handler
  **764–833**, registered **873–875**. Actor accepts `person_id`, or
  `dbid,dbtype,name,role,auto_search`. `focus` restoration is **660–671**. Video
  accepts typed `tmdb_id` (or library DBID). Untyped ambiguous title IDs are not
  safe. Aura always supplies type.
* `lib/script/person.py:253–326` resolves library actor context.
  `lib/data/api/person.py:94–137,149–253,293–359` resolves episode parents and
  credits, and tries exact, fuzzy-role, name-only and reversed-name matches
  **within those credits** (including credit crew fallback). Only `auto_search`
  enables the subsequent global search dialog. Aura explicitly disables it.
* `lib/dialog/actor.py:39–66,69–92` binds library and online filmography, crew and
  images, then opens the provider's `default/1080i` actor XML. No Aura person
  window or separate list request is introduced.
* Actual `resources/skins/default/1080i/script-skin-info-service-DialogActorInfo.xml`:
  biography **5001**, library movies/TV **1500/1501**, online movies/TV/all
  **1502/1503/1504**, crew **1505**, images **1506**. Titles dispatch back through
  `dialog_video_info` with typed IDs. Images use `dialog_image_viewer`.
* Actual default `script-skin-info-service-DialogVideoInfo.xml`: cast **1510**
  dispatches `dialog_actor_info,person_id=…`. Recommendations **1511** and local
  similar **1512** use typed video routes. Crew **1513** uses exact person IDs.
  These are the inspected **default** controls, not assumed Estuary overrides.
  `lib/dialog/video.py:55–93` binds cast with `online=true` and typed title IDs.

Competitor implementation anchors: Embuary Info `resources/lib/main.py:19–148`
(dispatch/ID/search), `person.py:23–172` (cast filmography/images),
`helper.py:60–67` (simplecache, default 336-hour writes). Embuary Helper
`resources/lib/plugin_content.py:697–813,946–1000` (director/actor/cast).
TMDb Helper `resources/tmdbhelper/lib/addon/consts.py:274–428,830–839`,
`items/basedir.py` (person menu), `api/tmdb/lists.py:191–204` (cast/crew).
Global Search `lib/defs.py:159–247`, `lib/gui.py:119–244,654–685`.

### Requests and cache boundaries

SIS person details use its person-data cache (`lib/data/api/person.py:407–419`).
Title credits/details, online metadata, library rollcall and artwork have their
own provider/Kodi caching. An explicit title dialog can load multiple supplied
rows and online metadata sources under existing provider preferences. **One
provider dispatch is not one HTTP request**, nor a promise of TMDb-only traffic.
The TMDb label identifies cast/person metadata, not all possible title enrichment.
No uncached/offline availability guarantee, cache flush, cache buster, second
provider request or custom cache is added. TMDb Helper's cast/crew containers
set cache-only *enrichment* after obtaining their lists. That does not eliminate
the initial provider request. Existing discovery `cacheonly=true` similarly
does not prohibit explicit Info traffic. Global Search/local library filtering
does not add an online metadata cache. Provider account options and cache,
language, matching, filtering and automatic-enrichment settings remain untouched.

## Source verification and release packaging

The independent comparison used Stage 6C merge base
`dfe4836e1885322fef18d2f84ec70b579c2ad0d1`. All **75 focused tests passed**:
28 actor and crew, 5 actor artwork, 13 search, 6 widget picker, 17 discovery,
and 6 local widget. All **128 packaged XML files** parsed. Toolkit syntax,
manifest, path and package checks passed. Type checks were inapplicable to
this skin package. `git diff --check` passed.

The comparison reported the same inherited full-suite failures and error
signatures, Toolkit official checker diagnostics, and kdk diagnostics as Stage
6C. The existing packaging-approval gate still requires owner approval for
`1080i/Custom_1141_SearchCategories.xml` at final release. Stage 7 adds no runtime
paths. The updated legacy actor check covers the existing native cast card,
literal local fallback and the new typed SIS action. Other checker rules remain
as established at the merge base.
