# Local library widgets in Aura Omega

Both choices are opt-in in the Skin Shortcuts widget picker: **Recently Added
Episodes (Grouped)** is under **Recently Added Video**, and **Next Up
(Favourites)** is under **Continue Watching & Next Up**.

## Picker taxonomy (Stage 5, issue #38)

The top-level order is **Continue Watching & Next Up**, **Recently Added Video**,
**Movies**, **TV Shows & Episodes**, **Local Recommendations**, **Music**,
**Live TV & Recordings**, **Library & Sources**, **Playlists**, **Add-ons**.
Local Recommendations contains Similar and Recommended movies/shows. All seven
Skin Info Service choices retain their add-on-enabled guard; mixed native/provider
categories remain available without the provider.

Library & Sources retains the direct movie, TV and music node widgets, native
Video/Music Library browsers and their source folders, Pictures sources and the
typed files/source widgets. Playlists has native Video and Music branches;
Add-ons retains the original native browsers and fixed list shortcuts, without
duplicate video/audio browsers elsewhere. None and Custom item remain supplied
by Skin Shortcuts. Curated headings do not dynamically sort or browse providers.

All 51 authored shortcuts remain reachable once, with byte-identical paths and
unchanged IDs, types, targets and icons. Saved paths, layouts and defaults are
not migrated or rewritten. Only the NewTvShows picker label changes to **Recent
Shows with Unwatched Episodes**; supported `widgetName="$LOCALIZE[31367]"` keeps
its original default row name. No routes or defaults are added. This uses Skin
Shortcuts 2.0.3's `build_node_listing` / `get_node` hierarchical node model.

## Widget sources

| Choice | Skin Info Service 2.0.2 arguments | Row behavior |
| --- | --- | --- |
| Recently Added Episodes (Grouped) | `action=recent_episodes_grouped&include_watched=true&limit=25` | One row per show from the first 25 shows in Kodi's descending show `dateadded` order. A show with a single unwatched episode returns that episode. Otherwise, if the two most recent episodes were added on the same calendar date, the row opens the show. In other cases it plays the most recent episode. Fully watched series are eligible. |
| Next Up (Favourites) | `action=next_up_favourites&limit=25` | One next-unwatched episode per eligible favourite show in Kodi favourites order. Starting a show is optional. Fully watched, missing and non-library shows are skipped. |

The grouped playlist uses the provider's TV-show and episode metadata, artwork
and destination paths. Its ordering follows the show's library date. An
episode added to an older show may leave that show's position unchanged.
To populate the favourites queue, add a TV show from the Kodi library to
Favourites. The provider reads the TV show DBID from the library favourite's
window path. Episode and arbitrary add-on favourites are ignored.

Both new queries use only the static supported action parameters shown above,
without a `reload=$INFO[Window(Home).Property(SkinInfo.Library.Refreshed)]`
suffix. Kodi 21.3 Omega's `xbmc/guilib/listproviders/DirectoryProvider.cpp`
(lines 266–305) invalidates populated typed results on applicable
`OnScanFinished`, `OnCleanFinished`, `OnUpdate`, `OnRemove`, `OnRefresh` and
certain player events. These native events refresh the populated typed lists;
an already-empty widget or a favourites-only edit can require reopening or
reloading the view after a change. The provider's two directories disable
disk caching. The existing five SIS widgets remain unchanged.

After one managed runtime exited with code 139 following playback, logs showed
native invalidation of both new plugin directories on playback/library
notifications, followed by a separate invocation batch when
`SkinInfo.Library.Refreshed` changed. Removing the suffix eliminates that proven
duplicate invocation trigger for these two widgets only. The segfault cause
remains unclassified; this is not a claim to have fixed the crash. No custom
polling, window wiring or dependency changes are introduced.
The existing Aura display limit still applies to both lists.

## Existing options and alternatives

- Aura's Recently Added Episodes remains an episode-by-episode list. The
  existing native **Video Library**, **Playlists** and **Music Library**
  branches already cover unwatched media, recently added media, custom tag
  collections, recent and top albums, and other smart-playlist rules.
- Embuary Helper 2.0.8 offers `info=getnewshows` with `showall` and optional
  show `tag`. Its grouped behavior overlaps the new source. Its `info=getnextup`
  filters in-progress shows by `tag` and/or `playlist`, with OR across multiple
  playlist values. Both routes query at most 25 shows. A future picker could
  offer a useful tag or playlist selector if it can persist the chosen value.
- Skin Info Service's existing Similar Movies and Similar TV Shows use stable
  local DBIDs. The provider supports a `watched` filter and a playlist
  candidate-pool `path`. Recommended Movies and Recommended TV Shows use
  recent local viewing history. The provider offers `min_rating`,
  `strict_rating`, `history_size`, `multi` and `recency` tuning. The current
  choices retain their existing behavior.
- Skin Shortcuts 2.0.3 stores the chosen widget ID, type, target and path from
  Aura's `shortcuts/overrides.xml`. Home continues to use its existing
  `shortcuts/template.xml` and `1080i/Includes_Widgets.xml` rendering.

Sources inspected were the official Omega ZIPs for
[Skin Info Service 2.0.2](https://mirrors.kodi.tv/addons/omega/script.skin.info.service/script.skin.info.service-2.0.2.zip)
(`lib/plugin/widgets/video.py` and `lib/service/library/refresh.py`),
[Embuary Helper 2.0.8](https://mirrors.kodi.tv/addons/omega/script.embuary.helper/script.embuary.helper-2.0.8.zip)
(`resources/lib/plugin_content.py`) and
[Skin Shortcuts 2.0.3](https://mirrors.kodi.tv/addons/omega/script.skinshortcuts/script.skinshortcuts-2.0.3.zip)
(`resources/lib/skinshorcuts/library.py`).
