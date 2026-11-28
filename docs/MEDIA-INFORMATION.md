# Media information — Stage 8 guide and audited capabilities

## Scope and evidence identity

**8A (movies), 8B (TV) and 8C (music) passed native qualification in the same
retained Flathub Kodi 21.3 Omega pilot. No release is claimed.** Aura is **2.1.1**.
The capability inventory below records the pre-implementation audit of accepted
Stage 7 tree `473bf67580d706ac8e0b00d0bdde66e5856b8609`; its existing/gap
descriptions and line references are historical, not a description of remaining
Stage 8 work. The guide and confirmed results follow that inventory.

The installed Toolkit addon-development, addon-validation and version-compatibility
skills guided the original source review. Native results below are retained
implementation evidence, separate from that audit. Provider settings were
preserved. This documentation update adds no runtime changes or release approval.

Citation conventions avoid exposing private evidence locations:

* Audit source paths are relative to this repository at the commit above.
* Helper paths begin with their exact retained add-on ID, followed by the path
  inside that package. These are source citations, not installed-device paths.
* `Core/<file>` identifies the supplied **21.3-Omega tagged-source** copy by
  basename. The six supplied files are `GUIDialogVideoInfo.cpp`,
  `GUIDialogMusicInfo.cpp`, `GUIDialogSongInfo.cpp`, `GUIInfoManager.cpp`,
  `VideoGUIInfo.cpp` and `MusicGUIInfo.cpp`. No moving master documentation or
  unsupplied database implementation is treated as inspected evidence.

### Exact retained manifests

Each package's actual `addon.xml` was read, not inferred from Aura's minimum
imports. Minimum imports do not guarantee every older satisfying version has the
same routes.

| Retained package and manifest | Exact version | Declared entry points relevant to selection |
| --- | --- | --- |
| `script.skin.info.service/addon.xml:2–16` | 2.0.2 | `plugin.py`, `script.py`, `service.py`, Python API floor 3.0.1 |
| `plugin.video.themoviedb.helper/addon.xml:2–20` | 5.4.16 | `resources/plugin.py`, `resources/script.py`, `resources/service.py`, module extension, Python API floor 3.0.1 |
| `script.embuary.info/addon.xml:2–16` | 2.0.8 | `plugin.py`, `default.py`, `service.py`, Python API floor 3.0.0 |
| `script.embuary.helper/addon.xml:2–13` | 2.0.8 | `plugin.py`, `default.py`, `service.py`, Python API floor 3.0.0 |
| `script.globalsearch/addon.xml:2–6` | 9.0.7 | `default.py`, local-library search, Python API floor 3.0.0 |

Aura `addon.xml:1–17` declares `skin.aura` 2.1.1, GUI API 5.17.0 and
1920 × 1080 layouts. Its SIS floor is 2.0.0 and Global Search floor is 9.0.5.
That distinction must survive any later compatibility or packaging decision.

## Audited capability inventory (Stage 7 baseline)

### Movie and shared video information

* **Existing subject capture.** `1080i/DialogVideoInfo.xml:9–43` snapshots
  DBID, DBType, discovery category, TMDb, IMDb, parent-show IDs, season/episode
  and escaped Director/Writer values on load, then clears them on unload.
  IMDb fallback accepts an `IMDBNumber` beginning `tt`, not an arbitrary default
  unique ID. Keep requests bound to that subject when Cast or Similar takes focus.
* **Existing native behavior.** `Core/GUIDialogVideoInfo.cpp:158–239,343–441`
  dispatches native play, rating, art, trailer, director search and Cast 50
  Select. Cast Select searches local appearances, while a collection's 50 opens
  its movie. Native name/role and thumbnail/icon construction remain core-owned.
  Aura's hidden 8, 7, 10, 11, 12 and 6 are not replacement provider controls.
  `1080i/Includes_Items.xml:196–244,268–328` exposes Play, Plot, Series List,
  Movie Set, trailer, user rating, art and refresh through those mechanisms.
* **Existing collection and crew.** Movie Set uses native `ListItem.SetID`
  and the literal `videodb://movies/sets/` route, not an online collection
  lookup. Hidden 9997 duplicates that destination
  (`DialogVideoInfo.xml:921–928`). Director stays in the footer at 749–750,
  Writer and Set are in the information section at 698–708. Keep these and
  Stage 7's explicit 9553/9554 crew actions, not a new collection/crew provider.
* **Partial release metadata.** `Includes_Labels.xml:296–299` deliberately
  reduces movies/sets to Year in `Label_Premiered`. The shared showcase line at
  388–395 uses it. There is no dedicated movie full-release-date row among
  `DialogVideoInfo.xml:676–718`, despite native Premiered support. The existing
  Date added row at 685–688 is not a release date.
* **Partial ratings.** `Includes_Labels.xml:7–60` already prefers native IMDb,
  `themoviedb` then `tmdb`, and TVDb aliases, followed by qualified SIS library
  or opt-in online properties. IMDb has matching votes. TMDb and TVDb currently
  have score variables but no corresponding source-specific vote variables.
  `Includes_Object.xml:1225–1472` renders those sources, percentages and Top250.
  Do not describe this as missing multi-source infrastructure.
* **Context-dependent reachability.** `Object_Info` in
  `Includes_Object.xml:4–201` uses container content, including the literal
  `seaons` typo. Its ratings include at 116–128 is conditioned on MyVideoNav,
  Home or Global Search visibility, not explicitly on Video Info. Its 80-pixel
  rating area also contains native/user stars. Bottom `Object_Flags` defaults
  `ratings=false` at 955–991. Thus definitions alone do not prove a full ratings
  strip in every information-dialog entry context. Native proof must cover
  library, Home and search entry, not merely XML presence.
* **Potential misleading duplicate.** `Object_Ratings_Content:1416–1453`
  falls back to unqualified `ListItem.RatingAndVotes` or `ListItem.Rating` when
  IMDb is absent. That can repeat the default TMDb score already shown elsewhere.
  A default score does not prove IMDb provenance. The nearby IMDb icon is gated
  independently by `Aura.ItemIMDB`. A later dialog-specific compact presentation
  should use exact sources, not relabel this generic fallback as IMDb.
* **Existing local related rows.** Director Movies 9501, Similar 9502, Images
  9504 and Extras 9505 are at `DialogVideoInfo.xml:511–622`. SIS
  `action=similar` here is a locally ranked library result, not TMDb online
  recommendations. `script.skin.info.service/lib/plugin/widgets/video.py`
  `_similar_seed`, `_similar_pool`, `handle_similar` at 1218–1382 distinguish
  library candidates from an optional online seed. Do not replace this row.
* **Existing online gates.** `Includes_Labels.xml:7–8,100–115` gates SIS
  property fallback, online cast and online Similar seeding. Awards at
  `DialogVideoInfo.xml:714–718` use `Aura.ItemOnline`. Review/download art at
  969–982 needs enrichment, enabled SIS and positive captured library DBID.
  Native art and local folders remain separate. Title matching in
  `Aura.ItemLibrary` is not unique identity proof, and the online Home-property
  consumer lacks a per-result subject-ID comparison. Rapid-switch stale data
  remains a native gate, not something new labels would fix automatically.

### Explicit online title details and provider overlap

**Already selected SIS route.** Discovery's existing 9551 action is
`DialogVideoInfo.xml:427–455`, with `Aura.PersonDiscovery`, `Aura.PersonAction`
and `Aura_PersonLabel` in `Includes_Object.xml:383–409`. Both discovery markers,
including locally matched discovery results, get **31950 Online cast & crew
(TMDb)**. Typed movie/TV and positive captured TMDb ID are required. SIS must be
enabled and Cast must not be hidden. This explicit Select action does not require
automatic enrichment enabled. Native person **31951 Online person (TMDb)** is
different and must not be overwritten with a title action.

The exact existing title dispatch is:

```text
RunScript(script.skin.info.service,action=dialog_video_info,dbtype=$INFO[Window.Property(Aura.Info.DBType)],tmdb_id=$INFO[Window.Property(Aura.Info.TMDB)],focus=9551)
```

`script.skin.info.service/lib/script/script.py:660–671,764–833,874` restores
focus, accepts only movie/tvshow (normalizing tv), reads `dbid`, `tmdb_id` and
`imdb_id`, and can resolve unique IDs from a typed DBID. It explicitly rejects
unsupported types. Movie and TV TMDb namespaces overlap, so always pass type.
`lib/dialog/video.py:55–93,96–132` fetches online data and binds cast, crew,
TMDb recommendations, local similar, posters and optional local details.
The supplied default `resources/skins/default/1080i/`
`script-skin-info-service-DialogVideoInfo.xml` has cast **1510**, online
recommendations **1511**, local similar **1512** and crew **1513** at
148, 229, 332 and 435. Recommendation Select at 236 passes typed TMDb IDs.
Local Similar Select at 339 passes typed library DBID. This is already the
provider-owned title/details/recommendations experience to reuse.

**Unused and duplicate alternative.** Aura still defines hidden Embuary title
button **9005** at `DialogVideoInfo.xml:945–953`. It is enrichment-gated and
dispatches local movie/TV DBIDs or parent-show DBID. Its topbar menu item in
`Includes_Items.xml:247–256` is commented out. Do not call it a currently visible
online-details button. Reintroducing it would duplicate SIS's title stack.
Studio row **9503** is commented out at `DialogVideoInfo.xml:561–573`, yet
navigation and hidden 9006 still reference it. These are pre-existing navigation
risks to test, not permission to redesign unrelated rows in Stage 8.

| Candidate | Verified source mechanism | Selection |
| --- | --- | --- |
| Kodi native | Tagged dialog controls, stored video/music tags, collection navigation | Baseline for local metadata and native actions |
| SIS 2.0.2 | Typed `dialog_video_info` above, supplied title dialog and `tmdb_recommendations` alongside local `similar` | One explicit online title/detail provider, keep existing person/crew/art integration |
| TMDb Helper 5.4.16 | `resources/tmdbhelper/lib/addon/consts.py:262–272,472–480` has typed recommendations, similar and collection directories. `lib/items/basedir.py:1099–1130` builds details for movie, TV, season, episode and person | Retain existing Discovery listings. Do not add a parallel detail directory or replace native collections |
| Embuary Info 2.0.8 | `resources/lib/main.py:19–148,153–166` implements movie/TV/person/season dialogs. DBID resolution may fall back to title/year search. `resources/lib/video.py:22–60,141–258` supplies seasons, collection, similar and images | Capable but duplicate title experience. Do not revive hidden 9005 for this slice |
| Embuary Helper 2.0.8 | `resources/lib/plugin_content.py:75–111,700–813` uses local JSON-RPC. Director movies are local. Actor DBID chooses a random top-cast member, while `dblabel` is a name filter | Keep existing bounded local uses, not an exact online title/person provider |
| Global Search 9.0.7 | `lib/defs.py:21–39,45–149` declares VideoLibrary/AudioLibrary categories. `lib/gui.py` builds local result items and local musicdb drilldowns | Retain local search. Not online recommendations or artist/album discovery |

### Optional OMDb is not a requirement for native ratings

SIS `resources/settings.xml:102–145,282–286` exposes optional OMDb key and
ratings-source preferences. `lib/kodi/settings.py:54–56` reads the preference.
`lib/data/api/omdb.py:20–35,77–102` reads the configured key, returns without a
key and excludes episode ratings. `lib/data/online.py:58–86,222–308` shows the
explicit title fetch can combine TMDb, OMDb, MDBList and Trakt, merging in that
order. MDBList can override OMDb keys. Do not assume every title fetch is
TMDb-only or that one script invocation equals one request. The aggregate title
fetch itself does not visibly consult the ratings-source toggle before calling
the OMDb fetch function, so do not promise that toggle blocks all dialog OMDb
traffic. Existing keys, account preferences, caches and service settings stay
untouched.

Embuary Info's `resources/lib/omdb.py:15–39,56–74` separately reads its own
optional key and supplies IMDb, critic/audience fields, awards and DVD date.
TMDb Helper separately declares `omdb_apikey` and `omdb_apikey_access` in
`resources/settings.xml:402–412`. None establishes mandatory OMDb setup for
Aura. Stored native IMDb/TMDb scores, their votes and native Premiered do not
need a live OMDb request. A source name describes the stored rating provenance,
not the service contacted by the skin today.

### TV information

**Existing/partial.** The shared Video Info supplies native cast and person
actions, a Next Up 9501 alternative for non-movies, Similar 9502 and the same
information section. `Includes_Labels.xml:159–173` already prefers native
`ListItem.Status`, then SIS library/online status and next/last episode metadata.
However, the status/date line in `Includes_Object.xml:69–78` is gated by
`Container.Content(tvshows)` and control 500 visibility. Watched/total appears
in `Label_ShowCase_InfoLine` at `Includes_Labels.xml:391` only through a
container-content branch. Episode aired date is also present in a
container-specific label at 372. These are partial mechanisms, not a reliable
dialog-subject contract for every Home, search, season and episode entry.

**Tagged support and limits.** `Core/GUIInfoManager.cpp:7084` maps Status,
and `Core/VideoGUIInfo.cpp:390–392` returns the video's `m_strStatus`.
`GUIInfoManager.cpp:5091–5116` documents `ListItem.Property(TotalEpisodes)`,
`WatchedEpisodes` and `UnWatchedEpisodes` for TV shows/seasons. It distinguishes
filter-dependent `NumEpisodes`. These are item properties, not
`Container.TotalWatched`. The supplied files do not establish every database
population or refresh path for those properties. A dialog may receive an item
without them. Supported names are source-auditable now, guaranteed availability
and freshness are not.

`Core/VideoGUIInfo.cpp:223–238` returns localized `ListItem.Premiered` from
valid first-aired first, otherwise valid premiered. This supports a native
aired/premiered label without borrowing a widget's selected episode. Status
should be show-only. Counts should be show/season-only and only when actually
present. No new calendar, scheduling lookup, next-air request or account feature
belongs in slice B.

### Music and the song-info filename

There is **no Aura `1080i/DialogSongInfo.xml`**. This is not evidence that song
information has a separate missing layout. Tagged
`Core/GUIDialogSongInfo.cpp:111–119` constructs the song dialog with
**`DialogMusicInfo.xml`**. Audit and any later fix must cover song, album and
artist semantics in that shared file.

**Existing local metadata.** `DialogMusicInfo.xml:43–89` reuses `Object_Info`
with square art. Its information section at 121–184 displays file/path, artist
Born, Died, Formed, Disbanded, Instrument, Mood, Style, album Mood, Style, Theme,
Type and Label through `ListItem.Property(...)`. Duplicate Mood/Style includes
have different artist/album sources and normally collapse when empty. Do not
merge away that distinction without fixtures. Native loading at
`Core/GUIDialogMusicInfo.cpp:79–141` fills artist/album tags and properties from
the music database, songs and stored discography. Stored artist discography can
include previously scraped non-library albums, not just owned albums.

**Partial/gaps.** Year and artist/genre are already in
`Includes_Labels.xml:341–358`. The music layout has no explicit
`ListItem.ReleaseDate` or `ListItem.OriginalDate` row. Generic info lines at
375–376 use `Container.Property(Album_Label)`, which is not safe evidence for
the current dialog subject. Existing album Label at `DialogMusicInfo.xml:180–183`
is item-scoped and should remain. Song title versus album title must be proved
because `Label_MainTitle` can choose Album under songs content. The inherited
Director footer and hidden YouTube action 9003 at 226–251 do not constitute
artist/album online discovery.

**Native control mismatch needing proof, not a silent rewrite.** Tagged music
core defines refresh **6**, user rating **7**, play **8**, art **10**,
artist-info **12** and list **50**. Song core uses **12** for album-info and
**50** for role/contributor-to-artist navigation
(`GUIDialogMusicInfo.cpp:52–58,371–419,534–588`,
`GUIDialogSongInfo.cpp:34–40,155–192,234–272`). Aura currently declares hidden
6, 7, 10 and 12 but no native play 8 or list 50 in `DialogMusicInfo.xml`.
Control 12 is described as Get Fanart and explicitly artist-only at 273–278,
while core means Artist information for an album and Album information for a
song. `Items_Info` sends clicks to native IDs and checks enabled state, not
necessarily visibility. Therefore source proves native capabilities and an
Aura exposure mismatch, not working artist/album links or their final labels.
Retain the native song-info engine, album/artist controls and semantics rather
than substitute an online window. Any exposure correction needs separate
implementation approval and native tests.

**Verified local SIS capabilities are not blanket online discovery support.**

* `script.skin.info.service/lib/plugin/dbid.py:236–316` supports positive typed
  artist/album `action=getdetails` DBIDs, not song in that handler. It returns
  one local detail ListItem. `lib/kodi/library.py:149–209` fetches artist with
  local albums, or album with local songs, through AudioLibrary. This is not a
  music dialog route or remote catalogue. In `dbid.py:314–337`, music items
  receive properties rather than a VideoInfoTag. Do not assume a fully populated
  native MusicInfoTag/Info action without checking the result contract.
* `lib/plugin/plugin.py:305–322,408–411` registers `artist_albums`,
  `artist_musicvideos`, `genre_artists` and `similar_artists`.
  `lib/plugin/widgets/music.py:13–61,277–410` resolves typed DBID to a name,
  then may resolve that name back to the first local artist ID. Artist albums
  are AudioLibrary results, artist music videos are VideoLibrary results and
  genre artists are random local results. Passing a DBID does not eliminate
  first-artist selection or same-name ambiguity. These are qualified local
  routes, not new global artist/album search.
* **Do not call similar_artists offline-only.**
  `lib/plugin/widgets/music.py:239–274` filters its final results to local
  AudioLibrary artists, but `lib/data/music.py:485–506` fetches Last.fm artist
  information on a cache miss. Local-only results do not mean local-only work.
  Defer this route from the local baseline. SIS also contains online music
  enrichment and caches, but that does not turn `dialog_video_info` into an
  artist/album dialog. Its type check rejects them.
* The inspected Embuary Info and TMDb Helper dispatch surfaces select video
  titles/persons, not music artists/albums. Global Search offers local music
  categories. No supported general online artist/album discovery integration
  for Aura is established by these sources. Do not pass music DBIDs to a movie,
  TV or person route, equate a music artist with a TMDb person, or invent a SIS
  `dialog_music_info` action.

## Using media information

### 8A — Movies

Open a local movie's **Info** for its release date, local/online origin and
stored, named IMDb/TMDb ratings with same-source vote counts. Release date is
distinct from Date added; a stored rating's source name does not mean a live
request to that service. Use **Movie Set** for the existing native collection
route, and native Play/Resume, rating and artwork actions as before.

Select **Online details & recommendations (TMDb)** for explicit typed local
movie details through SIS **2.0.2**. Related titles can open their own Info;
Back returns to the originating title and focus. This does not enable automatic
enrichment. Discovery retains its single existing Stage 7 title action rather
than gaining a second online-details button or a Play action for an unmatched
title.

### 8B — TV

Show Info displays native series status and date. Show/season counts use direct
native local total, watched and unwatched episode properties, not online totals
or the underlying container. Episode Aired uses the actual FirstAired value;
an undated episode stays undated. Status and Resume use high-priority native
predicates, with their labels kept separate.

Explicit typed TV details also use SIS **2.0.2**, match the exact local TV DBID
and preserve return focus. The episode detail lookup is exact episode DBID plus
type, using SIS local `getdetails` only for actual FirstAired; it is not a
show-ID substitution or an online episode lookup.

Both slices preserve native play/browse, rating/artwork and Stage 7 routes.
Explicit typed details may use other already configured SIS providers; the
TMDb label is not a TMDb-only traffic guarantee. No OMDb dependency is added,
and no key or provider-setting change is required.

### 8C — Music

Open **Artist Info** for local biography and native discography on Kodi control
**50**; album selection uses Kodi's native local album handling. Native album
rows show tracks, while song rows show contributor context when present.

Artist, album and song Info share `DialogMusicInfo.xml`. Native control **12**
provides **Artist Info** from an album and **Album Info** from a song. Native
Play uses control **8** for a positive native album or song. Local biography,
labels, artwork, ratings and management remain native. Release date and a
distinct original date follow Kodi's locale/ISO preference.

Music adds no online workflow, mandatory dependency or selected runtime
filename. Provider and skin preferences remain unchanged.

## Confirmed native results — retained Flathub Kodi 21.3

These are observations from the retained 8A/8B/8C verification, not new
executions by this documentation update. Official owner fixtures are synthetic.
Timings and connection classifications describe their measured windows, not
general performance or attribution guarantees. The retained Stage 13
provider/artwork measures below are unchanged.

### 8A — PASS

* Local Info opened in **0.445–0.516 s**, showing stored named **IMDb 7.9 /
  2,111 votes** and **TMDb 8.6 / 133 votes**, release date and local/online
  origin. Existing Movie Set navigated to the fixture collection.
* Native Resume selected the exact file at **11.705 s**, then returned to idle.
* Typed local movie details used SIS **2.0.2**, matched the local DBID, opened
  **Iron Man 3** related Info and returned to the originating title/focus.
  Properties were ready in **4.873 s**, with **zero observed TLS** in that
  window; the **8.770 s** repeat observed **zero metadata / eight artwork**
  connections.
* An unmatched Discovery title had no Play and retained its only existing
  Stage 7 action.
* The isolated cached **Apollo 13** overlay returned to local Info in
  **7.482 s**; an explicit same-session retry took **4.464 s**. The quiet
  restore interval observed **27 artwork / zero classified metadata**
  connections due to retained artwork work; exact attribution was not inferred.

### 8B — PASS

* Native series status and date displayed correctly. Direct native local counts
  were **3 total / 1 watched / 2 unwatched**, and **Season 1: 2 / 1 / 1**.
* Exact episode DBID+type SIS **2.0.2** local `getdetails` supplied only actual
  FirstAired. The dated **2025-02-03** episode and undated episode gap were
  preserved, alongside native status/Resume predicates and label separation.
  Native Resume selected the exact file at **12.215 s**, then returned to idle.
* Typed **New Girl** related-information properties were ready in **5.790 s**.
  Related **Three's Company** took **7.324 s**, with **one metadata / nine
  artwork** connections; the cached repeat took **9.003 s**, with **six artwork
  / zero metadata** connections.
* Exact local TV DBID matching, safe unmatched **The Wire** behavior and return
  focus passed. All three automatic toggles stayed off; settings were preserved.

### 8C — PASS (offline)

* **Studio Rune** displayed its local biography and **Copper Sessions / Silver
  Sessions** discography. Native artist-to-album selection opened **Copper
  Sessions**, with edition dates **06/11/2020** and **03/02/2019**, **Fixture
  Records** and available artwork. The absent cover on **Silver Sessions** left
  the fallback in place.
* The **Various Artists** compilation contained both exact tracks. **Paper
  Suite** Song Info opened **Album information**; physical Escape returned.
  Native Play opened the exact synthetic audio file, then stopped to idle.
* Provider and skin preferences were preserved.

### Separately verified existing regressions

Actor ID **3223** and director ID **15277**, artwork/rating open and cancel,
mouse Plot, Global Search, all **five saved Discover rows** and local widgets
were separately verified. An unavailable online action returned safely to local
Info in **4.907 s**. These results do not add an online music workflow.

## Source contracts

Relevant movie source contracts include source-keyed Rating/Votes mapping at
`Core/GUIInfoManager.cpp:10673–10694`, retrieval at
`Core/VideoGUIInfo.cpp:174–214` and the default unique-ID behavior at
`Core/VideoGUIInfo.cpp:149–152`. Same-source IMDb votes and the matching
`themoviedb`/`tmdb` alias matter: a generic default rating is not IMDb provenance.
The audited row include is `Includes_Object.xml:204–232`; the historical
information block is `DialogVideoInfo.xml:624–719`. Typed SIS dispatch and TV
native property contracts are cited in the inventory above.

Music uses the source-audited shared layout `DialogMusicInfo.xml`, not a separate
song layout. Release/original-date mappings
are `Core/GUIInfoManager.cpp:7178–7179` and `Core/MusicGUIInfo.cpp:303–321`;
native music rating/votes are at `MusicGUIInfo.cpp:192–218,300–302`, not
source-keyed video ratings. Native song/album/artist controls and local navigation
are qualified above. Historical gated SIS music artwork controls are at
`DialogMusicInfo.xml:280–292`; audited
local music routes do not establish general online artist/album discovery.

## Validation and packaging status

The historical static target is **Omega**. Its documented isolated lane pins
Kodistubs **21.0.0**, mypy **2.4.0** and official checker **0.0.36**, using
CPython 3.12/Linux tooling. These tool versions do not identify Kodi's embedded
Python or establish native behavior.

* All **110 focused tests** passed: 35 media information, 28 actor and crew,
  five actor artwork, 13 search, six widget picker, 17 Discovery and six local
  widget tests. All **128 packaged XML files** parsed.
* Toolkit syntax, manifest, package and path checks passed. Type checks were
  inapplicable to the skin package. The official checker, full suite and kdk
  recorded the same diagnostic signatures as the accepted Stage 7 baseline.
* The package retained all **1,807 existing runtime paths**. Stage 8 changed
  five established runtime files. The final package uses the configured
  default label font and defers Artist Info and Album Info enablement to Kodi.
* The Stage 3 required runtime manifest path
  `1080i/Custom_1141_SearchCategories.xml` remains part of the final packaging
  approval gate; see `GLOBAL-SEARCH.md` and `PERSON-EXPLORATION.md`.
