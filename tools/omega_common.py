"""Local-only payload/provenance helpers; no Kodi imports or network access."""

import functools
import io
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

START = "203aba5"
DIRECTORIES = (
    "1080i", "colors", "extras", "fonts", "language", "media", "resources",
    "shortcuts", "themes",
)
ROOT_FILES = (
    "addon.xml", "README", "LICENSE.txt", "changelog.txt", "icon.png", "fanart.jpg",
)
OPTIONAL_DOCS = (
    "OMEGA.md", "DEPENDENCIES-OMEGA.md", "MIGRATION-DECISIONS.md",
    "OFFICIAL-DEPENDENCY-RESEARCH.md", "PVR-EPG-DESIGN-RESEARCH.md", "MIGRATION-RESULTS.md",
)
GENERATED = "1080i/script-skinshortcuts-includes.xml"
REMOVED_RUNTIME = frozenset("1080i/" + name + ".xml" for name in (
    "DialogFavourites", "script-skin_helper_service-ColorPicker",
    "Includes_NextAired", "script-NextAired-TVGuide", "script-NextAired-TVGuide2",
    "Custom_1116_ColorBoxAdvancedSettings",
))
ADDED_RUNTIME = frozenset("1080i/" + name + ".xml" for name in (
    "DialogColorPicker", "MyFavourites", "DialogVideoManager",
    "Custom_1140_AiringCalendar", "Includes_PVR_Omega",
))
FOCUSED_DELTA = frozenset((
    "addon.xml", "README", "shortcuts/overrides.xml", *OPTIONAL_DOCS,
    # New calendar/PVR/settings labels in the three bundled locales.
    "language/resource.language.en_gb/strings.po", "language/resource.language.en_us/strings.po",
    "language/resource.language.de_de/strings.po",
    *("1080i/" + name + ".xml" for name in (
        "Custom_Overlay", "Defaults", "DialogAddonSettings", "DialogFavourites",
        "DialogSeekBar", "DialogSettings", "Includes_Dialog", "Includes_Labels",
        "Includes_OSD", "SettingsCategory", "DialogColorPicker", "MyFavourites",
        "DialogVideoManager", "DialogConfirm",
        "Home", "Startup", "SkinSettings", "Includes", "Includes_Global",
        "Includes_Images", "Includes_Items", "Includes_Object", "Includes_Topbar",
        "Includes_Widgets", "MyVideoNav", "script-skinshortcuts", "DialogMusicInfo",
        "DialogVideoInfo", "DialogAddonInfo", "DialogPVRInfo", "MyPVRGuide", "MyPVRChannels",
        "Custom_1140_AiringCalendar", "Includes_PVR_Omega",
        "script-skin_helper_service-ColorPicker", "Includes_NextAired",
        "script-NextAired-TVGuide", "script-NextAired-TVGuide2",
        "Custom_1116_ColorBoxAdvancedSettings",
        "Custom_1118_EnableRatings",
        # Official-only cleanup of optional legacy launchers/artwork consumers.
        "Includes_Defs", "DialogExtendedProgressBar", "script-script.extendedinfo-DialogVideoInfo",
    )),
))


def git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def payload_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return False
    if name == GENERATED:
        return False
    if len(path.parts) == 1:
        return name in ROOT_FILES + OPTIONAL_DOCS
    if path.parts[0] not in DIRECTORIES:
        return False
    if any(part.startswith(".") or part.lower() in {
        "__pycache__", "node_modules", "tools", "tests", "cache", "caches",
        "evidence", "userdata", "addon_data", "profiles", "accounts", "accountcache",
    } for part in path.parts):
        return False
    # Settings.xml is a required skin WINDOW, not saved account settings.
    if name != "1080i/Settings.xml" and path.name.lower() in {"settings.xml", "guisettings.xml", "profiles.xml", "accounts.xml"}:
        return False
    return not name.lower().endswith((
        ".py", ".pyc", ".pyo", ".bak", ".orig", ".rej", ".tmp", ".swp",
        ".swo", ".log", "~", "/thumbs.db", "/desktop.ini",
    ))


class Source:
    """Baseline reads use git show; only the builder requests an archive snapshot."""

    def __init__(self, root, baseline=False, archive=False):
        self.root = Path(root).resolve()
        self.baseline = baseline
        self.starting_commit = git(self.root, "rev-parse", START + "^{commit}").decode().strip()
        self.head = git(self.root, "rev-parse", "HEAD").decode().strip()
        self.branch = git(self.root, "branch", "--show-current").decode().strip() or "(detached)"
        records = git(self.root, "ls-tree", "-rz", self.starting_commit).split(b"\0")
        self.original_files = set()
        for record in filter(None, records):
            metadata, name = record.split(b"\t", 1)
            name = name.decode("utf-8")
            if payload_path(name):
                if metadata.split()[0] != b"100644":
                    raise ValueError("Unexpected baseline file mode: " + name)
                self.original_files.add(name)
        self._archive = None
        if baseline:
            self.files = sorted(self.original_files)
            if archive:
                data = git(self.root, "archive", "--format=tar", self.starting_commit,
                           "--", *DIRECTORIES, *(name for name in ROOT_FILES + OPTIONAL_DOCS
                                                 if name in self.original_files))
                self._archive = {}
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as tree:
                    for member in tree:
                        if member.isdir() or not payload_path(member.name):
                            continue
                        if not member.isfile():
                            raise ValueError("Non-regular archive member: " + member.name)
                        with tree.extractfile(member) as stream:
                            self._archive[member.name] = stream.read()
                if set(self._archive) != self.original_files:
                    raise ValueError("Baseline archive inventory mismatch")
        else:
            files = []
            for directory in DIRECTORIES:
                base = self.root / directory
                if base.is_symlink() or not base.is_dir():
                    raise ValueError("Missing or symlinked runtime directory: " + directory)
                for parent, dirs, names in os.walk(base, followlinks=False):
                    for child in list(dirs):
                        path = Path(parent) / child
                        relative = path.relative_to(self.root).as_posix()
                        if not payload_path(relative + "/payload"):
                            dirs.remove(child)
                        elif path.is_symlink():
                            raise ValueError("Symlinked runtime directory: " + relative)
                    for child in names:
                        relative = (Path(parent) / child).relative_to(self.root).as_posix()
                        if payload_path(relative):
                            files.append(relative)
            files.extend(ROOT_FILES)
            files.extend(name for name in OPTIONAL_DOCS
                         if (self.root / name).exists() or (self.root / name).is_symlink())
            self.files = sorted(files)
            for name in self.files:
                path = self.root / name
                if path.is_symlink() or not path.is_file():
                    raise ValueError("Missing or non-regular runtime file: " + name)
        for directory in DIRECTORIES:
            if not any(name.startswith(directory + "/") for name in self.files):
                raise ValueError("Empty or missing payload directory: " + directory)

    @functools.lru_cache(maxsize=None)
    def original(self, name):
        return git(self.root, "show", self.starting_commit + ":" + name)

    @functools.lru_cache(maxsize=None)
    def read(self, name):
        if name not in self.files:
            raise ValueError("Not in runtime inventory: " + name)
        if self._archive is not None:
            return self._archive[name]
        if self.baseline:
            return self.original(name)
        path = self.root / name
        if path.is_symlink():
            raise ValueError("Symlinked runtime file: " + name)
        return path.read_bytes()

    def deltas(self):
        if self.baseline:
            return []
        # Includes staged and unstaged changes; no rename heuristics or text filters.
        raw = git(self.root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                  "--name-status", "-z", self.starting_commit, "--",
                  *DIRECTORIES, *ROOT_FILES, *OPTIONAL_DOCS).split(b"\0")
        changes = []
        for index in range(0, len(raw) - 1, 2):
            status, name = raw[index].decode(), raw[index + 1].decode("utf-8")
            if payload_path(name):
                changes.append({"status": status, "path": name})
        known = {change["path"] for change in changes}
        for name in sorted(set(self.files) ^ self.original_files):
            if name not in known:
                changes.append({"status": "A" if name in self.files else "D", "path": name})
        return sorted(changes, key=lambda change: change["path"])

    def provenance(self):
        return {
            "starting_commit": self.starting_commit, "head": self.head,
            "branch": self.branch, "source": "baseline" if self.baseline else "worktree",
            "runtime_git_diff": self.deltas(),
        }
