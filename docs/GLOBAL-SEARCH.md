# Global Search integration (Omega)

Contract reviewed against **Global Search 9.0.7**, official exact ZIP:
<https://mirrors.kodi.tv/addons/omega/script.globalsearch/script.globalsearch-9.0.7.zip>.
This is source-level evidence, not native Kodi acceptance.

| Surface | Invocation / behaviour |
| --- | --- |
| Existing Search in `1080i/Includes_Items.xml` (`Items_View`) | `RunScript(script.globalsearch)` keeps the user's category preferences. If absent, `SendClick(8)` retains native search; if present, `SetFocus(50)` precedes launch. |
| Adjacent Search movies | `RunScript(script.globalsearch,movies=true)` only in the video library window while Search is enabled and `System.AddonIsEnabled(script.globalsearch)` is true; `SetFocus(50)` precedes launch. Uses the existing `extras/icons/film.png` to distinguish it from Search. |
| Reusable item | `Items_ScopedSearch` takes a localized `label`, supported `category` and optional `icon` (default `special://skin/extras/icons/search.png`); movies supplies `film.png`. It shares the existing top-bar list layout. Only movies is instantiated. |
| Results | Existing `1080i/script-globalsearch.xml` and related includes are unchanged. |

In 9.0.7, `default.py` parses one ampersand-separated argument map and prompts
with Kodi's keyboard when no `searchstring` is supplied. `lib/defs.py` starts
category flags false. In `lib/gui.py`, an empty map loads category settings;
a nonempty map uses `_parse_argv` instead, enabling only exact lower-case `true`
values. `_fetch_items` dispatches only enabled categories, so `movies=true`
does not search every category and then filter results. Neither action writes
category settings. Future categories must use supported top-level keys below;
multiple flags belong in one argument (`&amp;` in skin XML), not extra comma
arguments. No extra categories, online or PVR actions are introduced here.

## Category inventory (9.0.7)

From `lib/defs.py` (`CATEGORIES`) and `resources/settings.xml`, not just the
README (which omits `tvactors`):

| Role | Exact keys |
| --- | --- |
| Top-level library categories; settings default true | `movies`, `tvshows`, `episodes`, `musicvideos`, `artists`, `albums`, `songs` |
| Top-level categories; settings default false | `actors` (movie actors), `directors` (movie directors), `tvactors` (TV actors), `livetv` |
| Internal person drilldowns; no category setting | `actormovies`, `directormovies`, `actortvshows` |
| Internal hierarchy drilldowns; no category setting | `tvshowseasons`, `seasonepisodes`, `artistalbums`, `albumsongs` |

All definition flags start false, independently of settings defaults. Internal
keys support result navigation and its query/ID context; they are not ordinary
top-level text-search actions. No additional category entries are added by Aura.

## Focus validation guidance and regression

When validating in an authorized Kodi session, check `MyVideoNav.xml`'s default
view 50, menu control 300 and native Search button 8. Verify `Topbar_Menu` /
`Topbar_Menu_Layout` keyboard/remote left-right traversal, up/down routes to 50,
shared normal/focused icon slots, focused label and mouse hit areas. Confirm the
film icon distinguishes Search movies, and that it is hidden when Global Search
is absent or disabled. Keep ordinary Search's existing presence-based fallback
and invocation unchanged. Check that both launches focus 50 before the native
keyboard/results dialog, then exercise pointer selection, cancel/return focus
and label readability. These are validation guidance, not runtime acceptance;
Kodi rendering and interaction remain untested here.

Run the self-contained source regressions (no external dependency checkout):

```sh
python3 -m unittest discover -s tools -p 'test_global_search.py' -v
```

These verify placement, invocations, localization, XML well-formedness and the
authored native/focus contract, not Kodi runtime behaviour or a full skin schema.
