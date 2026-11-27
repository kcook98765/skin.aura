# Global Search integration (Omega, Stage 3)

Contract reviewed against **Global Search 9.0.7**, official exact ZIP:
<https://mirrors.kodi.tv/addons/omega/script.globalsearch/script.globalsearch-9.0.7.zip>.
Evidence: its `default.py`, `lib/defs.py` and `lib/gui.py`. This is source-level
evidence, not native Kodi acceptance.

## Entry points and picker

The ordinary **Search** item in `1080i/Includes_Items.xml` (`Items_View`) is
unchanged byte-for-byte, including its native fallback: without Global Search,
`SendClick(8)` invokes Kodi's handler; with it, `SetFocus(50)` precedes
`RunScript(script.globalsearch)`. That no-argument invocation continues to use
normal Global Search category preferences; Aura never sets those preferences.

The adjacent Stage 2 movie-only item is replaced by one localized **Search by
category** entry. It is visible only in the actual `MyVideoNav.xml` and
`MyMusicNav.xml` library windows, with native Search enabled and Global Search
enabled. Ordinary all-media Search remains immediately adjacent, one action
away; its scope still follows the user's normal preferences. The picker uses
existing `extras/icons/playlist2.png`, distinct from ordinary Search's unchanged
search icon.

The entry retains the origin library's menu focus (300) before opening modal
dialog **1141**, `1080i/Custom_1141_SearchCategories.xml`. Unlike forcing view 50,
this remains usable when a different library view is active. The small shared
`SearchCategories_Row` include in `Includes_Items.xml` reuses Aura's
`Dialog_Standard_ListButton` style and is consumed only by this picker;
the enclosing panel and title reuse `Dialog_Standard_Group` and
`Dialog_Standard_Header` (the existing standard label style in this checkout).
Kodi 21.3's `CGUIIncludes::Load_Internal` requires an `<includes>` root, so the
row definition lives in the existing shared includes file loaded through
`Includes.xml`, not inside the `<window>` file. The dialog has no self-file
include references. Existing overlay and panel/button art are reused. Video has six rows in a
640×556 panel; Music has three rows in a 640×334 panel. A normal vertical
grouplist supplies mouse hit areas and remote/keyboard navigation.

| Origin | Rows in display order | Exact single script argument | Kodi label ID |
| --- | --- | --- | --- |
| Video | Movies | `movies=true` | 342 |
| Video | TV shows | `tvshows=true` | 20343 |
| Video | Episodes | `episodes=true` | 20360 |
| Video | Actors | `actors=true&tvactors=true` | 344 |
| Video | Directors | `directors=true` | 20348 |
| Video | Music videos | `musicvideos=true` | 20389 |
| Music | Artists | `artists=true` | 133 |
| Music | Albums | `albums=true` | 132 |
| Music | Songs | `songs=true` | 134 |

Labels use Kodi's IDs from 9.0.7's definitions, except **Actors** deliberately
uses Kodi's generic 344 instead of Global Search's add-on-local movie/TV actor
labels. Skin string 31933 is repurposed from “Search movies” to “Search by
category”; there is no unused movie-only label.

**Actors is one launcher, not two.** It enables both upstream `actors` (movie
cast) and `tvactors` (TV cast) together. Global Search retains its distinct movie
actor and TV actor result tabs and drilldowns; Aura does not merge results.
**Directors** means movie directors (`VideoLibrary.GetMovies` upstream), not an
invented TV-director search.

## Invocation and return contract

In 9.0.7, `default.py` parses one ampersand-separated argument map and prompts
with Kodi's keyboard when no `searchstring` is supplied. `lib/defs.py` starts
category flags false. In `lib/gui.py`, an empty map loads category settings;
a nonempty map uses `_parse_argv` instead, enabling only exact lower-case `true`
values. `_fetch_items` dispatches only enabled categories: scoped launch does
not search everything and then filter results. Multiple flags belong in **one**
argument (`actors=true&amp;tvactors=true` in XML), never comma-separated arguments.

Each row force-closes only dialog 1141, then invokes
`RunScript(script.globalsearch,<exact argument above>)`. There is no delay,
settings write, alternate search engine, explicit origin-window activation or
unload focus handler. Back from the picker uses normal modal dismissal; cancel
from the native keyboard and Back from results return to the originating
library, whose usable menu focus was established before opening the picker.
No jump to Home, another library, or a hard-coded Video origin is authored.
Actual Kodi focus restoration still needs native verification.

## Why PVR stays native

No Live TV/PVR or online row is added. Global Search's optional `livetv` category
is not equivalent to Kodi's native guide search and its PVR-specific controls,
filters and backend behaviour. Keep Aura's existing native PVR windows and
`DialogPVRGuideSearch.xml` unchanged. Ordinary Search preferences remain intact,
including any user-selected upstream Live TV preference; this picker neither
sets nor overrides those preferences.

Upstream also defines internal drilldowns (`actormovies`, `directormovies`,
`actortvshows`, `tvshowseasons`, `seasonepisodes`, `artistalbums`, `albumsongs`).
Those require result-navigation context and are not picker launch categories.
Existing `1080i/script-globalsearch.xml` and related result includes are unchanged.

## Regression and future native verification

Run the self-contained source regressions (no external dependency checkout):

```sh
python3 -m unittest discover -s tools -p 'test_global_search.py' -v
```

These check the original Search bytes, placement, context gates, row order,
labels, exact single-argument calls, close-before-launch ordering, unique dialog
ID, reused styles, compact geometry, authored focus targets and XML parsing.
They do not emulate Kodi's include/condition engine or prove rendered focus.
`1080i/Custom_1141_SearchCategories.xml` is a **required runtime member** for
future packaging. The historical packaging approval manifest remains pinned;
an exact private workspace artifact requires separate supervisor preparation
and must include this new dialog. No packaging artifact is created here.

In a separately authorized native session, check Video and Music independently:
menu 300 traversal and pointer selection, picker row order and readable labels,
first-row focus, keyboard/remote up/down wrapping, mouse selection, Back from
picker, keyboard cancellation, empty results and Back from populated results.
Verify the originating window and usable focus remain intact in every case,
including non-default library views. Confirm both actor result tabs, movie-only
Directors, unchanged preferences, native PVR search and hidden category entry
when Global Search is absent/disabled. These are future acceptance steps, not
runtime claims for this source-only stage.
