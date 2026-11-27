# Local library widgets in Aura Omega

Both choices are opt-in under **Skin Info Service (library widgets)** in the
existing Skin Shortcuts picker. Saved widget paths, layouts and defaults are
preserved.

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

Aura passes its existing
`reload=$INFO[Window(Home).Property(SkinInfo.Library.Refreshed)]` suffix to both
queries. The local service debounces applicable scan, clean, update and remove
notifications for two seconds. The provider's two directories disable
disk caching. A favourites-only edit may become visible on the next widget
reload because such an edit can occur without a library notification.
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
