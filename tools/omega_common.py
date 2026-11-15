"""Local-only payload/provenance helpers; no Kodi imports or network access."""

import functools
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile

START = "203aba5"
VERSION = "2.1.0"
BASELINE_VERSION = "2.0.23"
RUNTIME_MANIFEST = "tools/runtime-files.txt"
RUNTIME_REVIEW_COMMIT = "2402785e7f5e16184955a5bc1f1e92ef666fb7da"
# The import commit remains the historical runtime anchor. Exact successor
# additions record supplemental notices; the active exclusion set is empty.
RUNTIME_REVIEW_ADDITIONS = frozenset((
    'THIRD-PARTY-NOTICES.txt',
    'fonts/Apache-2.0.txt',
    'fonts/Roboto-Regular-LineSpacingMod-NOTICE.txt',
    'resources/ICONMONSTR-LICENSE.txt',
    'resources/LEGACY-ASSET-NOTICES.txt',
))
RUNTIME_EXCLUSIONS_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
_exclusions = (Path(__file__).resolve().parent / "runtime-exclusions.txt").read_bytes()
if hashlib.sha256(_exclusions).hexdigest() != RUNTIME_EXCLUSIONS_SHA256:
    raise ValueError("Runtime exclusions differ from the reviewed alpha inventory")
RUNTIME_REVIEW_REMOVALS = frozenset(_exclusions.decode().splitlines())
# Membership approval, not content hashes: a new path review must update both
# this pin and the exact manifest. Never regenerate approval during a build.
RUNTIME_MANIFEST_SHA256 = "0df24ff354c073cdf7a286d0d67f5467c54f6938ddc237d28aa12c28c6612812"
DIRECTORIES = (
    "1080i", "colors", "extras", "fonts", "language", "media", "resources",
    "shortcuts", "themes",
)
ROOT_FILES = (
    "addon.xml", "README", "LICENSE.txt", "changelog.txt", "icon.png", "fanart.jpg",
    "THIRD-PARTY-NOTICES.txt",
)
OPTIONAL_DOCS = ()  # Compatibility only: operational documentation is never runtime.
GENERATED = "1080i/script-skinshortcuts-includes.xml"
REMOVED_RUNTIME = RUNTIME_REVIEW_REMOVALS | frozenset("1080i/" + name + ".xml" for name in (
    "DialogFavourites", "script-skin_helper_service-ColorPicker",
    "Includes_NextAired", "script-NextAired-TVGuide", "script-NextAired-TVGuide2",
    "Custom_1116_ColorBoxAdvancedSettings",
))
ADDED_RUNTIME = frozenset("1080i/" + name + ".xml" for name in (
    "DialogColorPicker", "MyFavourites", "DialogVideoManager",
    "Custom_1140_AiringCalendar", "Includes_PVR_Omega",
)) | RUNTIME_REVIEW_ADDITIONS
FOCUSED_DELTA = frozenset((
    "addon.xml", "README", "changelog.txt", "shortcuts/overrides.xml",
    *RUNTIME_REVIEW_ADDITIONS,
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

# Original Omega resources are restored. Only release documentation/notices
# differ from the pre-cleanup6882909 tree; no asset substitution is authorized.
RESTORED_OMEGA_COMMIT = "688290914a31d0f595179043062cc57eb85ab8d9"
RESTORED_DOCUMENTATION = frozenset({"README", "changelog.txt", "THIRD-PARTY-NOTICES.txt"})


def git(root, *args):
    result = subprocess.run(
        ["git", "-c", "diff.autoRefreshIndex=false", "-C", str(root), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def payload_path(name):
    """Historical inventory predicate; not permission to add worktree ZIP files.

    Keep the baseline selection stable: stricter worktree rules live separately.
    """
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


def runtime_path(name):
    """Canonical, admissible path; actual worktree membership needs the manifest."""
    if not isinstance(name, str) or not name or name != PurePosixPath(name).as_posix():
        return False
    if any(ord(char) < 32 or ord(char) == 127 or char in "\\:*?[]" for char in name):
        return False
    if not payload_path(name):
        return False
    path = PurePosixPath(name)
    if any(part.lower() in {"docs", "documentation", "internal", "generated"} for part in path.parts):
        return False
    # Exact membership is still mandatory, including for these admissible formats.
    # Bundled font licenses/readmes and the seven root distribution files remain.
    return path.suffix.lower() in {
        ".xml", ".xsp", ".po", ".png", ".jpg", ".jpeg", ".ttf", ".otf",
        ".xbt", ".txt", ".pdf",
    } or name == "README"


def parse_runtime_manifest(data):
    """Strict UTF-8/LF exact paths: no globs, normalization, duplicates or omissions."""
    text = data.decode("utf-8")
    if not text.endswith("\n") or "\r" in text:
        raise ValueError("Runtime manifest requires LF-terminated exact paths")
    files = text[:-1].split("\n")
    seen = set()
    for name in files:
        if not runtime_path(name):
            raise ValueError("Invalid runtime manifest path: " + repr(name))
        if name in seen:
            raise ValueError("Duplicate runtime manifest path: " + name)
        seen.add(name)
    if files != sorted(files):
        raise ValueError("Runtime manifest paths must be sorted")
    if not set(ROOT_FILES) <= seen:
        raise ValueError("Runtime manifest must include all required root files")
    for directory in DIRECTORIES:
        if not any(name.startswith(directory + "/") for name in files):
            raise ValueError("Runtime manifest missing directory: " + directory)
    return files


def regular_bytes(root, name):
    """Open each component without following links; reject devices/FIFOs before read."""
    parts = PurePosixPath(name).parts
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        child = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                        dir_fd=descriptor)
        if not stat.S_ISREG(os.fstat(child).st_mode):
            os.close(child)
            raise ValueError("Non-regular runtime file: " + name)
        with os.fdopen(child, "rb") as stream:
            return stream.read()
    finally:
        os.close(descriptor)


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
            manifest = regular_bytes(self.root, RUNTIME_MANIFEST)
            self.files = parse_runtime_manifest(manifest)
            digest = hashlib.sha256(manifest).hexdigest()
            if digest != RUNTIME_MANIFEST_SHA256:
                raise ValueError("Runtime manifest digest differs from reviewed approval")
            self.runtime_manifest = {
                "kind": "reviewed-exact-file-list", "path": RUNTIME_MANIFEST,
                "sha256": digest,
                "reviewed_commit": RUNTIME_REVIEW_COMMIT,
                "reviewed_additions": sorted(RUNTIME_REVIEW_ADDITIONS),
                "reviewed_removals_sha256": RUNTIME_EXCLUSIONS_SHA256,
                "file_count": len(self.files),
            }
            # Scan disk, not git's tracked/ignored view. Even admissible additions
            # must fail closed until separately reviewed and explicitly listed.
            files = set(ROOT_FILES)
            for directory in DIRECTORIES:
                base = self.root / directory
                if base.is_symlink() or not base.is_dir():
                    raise ValueError("Missing or symlinked runtime directory: " + directory)

                def walk_error(error):
                    raise error

                for parent, dirs, names in os.walk(base, followlinks=False, onerror=walk_error):
                    for child in dirs:
                        path = Path(parent) / child
                        relative = path.relative_to(self.root).as_posix()
                        if path.is_symlink():
                            raise ValueError("Symlinked runtime directory: " + relative)
                    for child in names:
                        path = Path(parent) / child
                        relative = path.relative_to(self.root).as_posix()
                        if not stat.S_ISREG(path.lstat().st_mode):
                            raise ValueError("Symlinked or non-regular runtime file: " + relative)
                        files.add(relative)
            unlisted = sorted(files - set(self.files))
            missing = sorted(set(self.files) - files)
            if unlisted or missing:
                raise ValueError("Runtime manifest inventory mismatch; unlisted=%r; missing=%r" % (unlisted, missing))
            for name in self.files:
                path = self.root / name
                if path.is_symlink() or not path.is_file():
                    raise ValueError("Missing or non-regular runtime file: " + name)
        if baseline:
            self.runtime_manifest = {
                "kind": "historical-git-tree-inventory", "commit": self.starting_commit,
                "sha256": hashlib.sha256(("\n".join(self.files) + "\n").encode()).hexdigest(),
                "format": "sorted-utf8-paths-lf", "file_count": len(self.files),
            }
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
        return regular_bytes(self.root, name)

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
            "runtime_manifest": dict(self.runtime_manifest),
        }
