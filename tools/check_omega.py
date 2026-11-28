#!/usr/bin/env python3
"""Focused Omega source regressions, entirely static. Exit 0 pass, 1 fail, 2 error."""

import argparse
import ast
import copy
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qsl
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
from omega_common import ADDED_RUNTIME, BASELINE_VERSION, FOCUSED_DELTA, REMOVED_RUNTIME, RUNTIME_REVIEW_ADDITIONS, VERSION, Source
from check_official_dependencies import CORE, dependency_closure, version_key

ROOT = Path(__file__).resolve().parents[1]
SEEK_COUNTS = {
    "1080i/DialogSeekBar.xml": 2,
    "1080i/Includes_OSD.xml": 4,
    "1080i/Includes_Labels.xml": 1,
}
STYLE_INCLUDES = {
    "Defs_Settings_Button": "1080i/Includes_Defs.xml",
    "Dialog_Standard_ListButton": "1080i/Includes_Dialog.xml",
    "Dialog_Standard_Right_Buttons": "1080i/Includes_Dialog.xml",
    "Dialog_Standard_Header": "1080i/Includes_Dialog.xml",
}
DEFAULT_TYPES = ("button", "sliderex", "label", "list", "panel")
WARNINGS = [
    "Static source checks only: no Kodi modules imported; embedded expressions are AST-parsed, never evaluated.",
    "Dependency availability, native dialog behavior, focus and rendering require separate runtime acceptance.",
    "Style coverage is a scoped static guard for four known style includes and relevant Defaults.xml entries; no full Kodi include expansion or inherited-condition resolution.",
    "Migration guards are named XML/source-regex assertions with scoped PVR include substitution, not a full Kodi condition evaluator or renderer; no Python-stub compatibility claim.",
]
LEGACY_DEPENDENCIES = (
    "script.module.musicbrainz", "script.module.thetvdb", "script.module.metadatautils",
    "script.skin.helper.service", "script.skin.helper.widgets", "script.skin.helper.skinbackup",
    "script.skin.helper.backgrounds", "script.tv.show.next.aired", "script.skin.helper.colorpicker",
)
OFFICIAL_MINIMUMS = {
    "xbmc.gui": "5.17.0", "script.skinshortcuts": "2.0.3", "script.globalsearch": "9.0.5",
    "script.image.resource.select": "0.0.5", "resource.images.weathericons.white": "0.0.6",
    "resource.images.moviegenreicons.transparent": "0.0.6", "resource.images.studios.white": "0.0.25",
    "script.embuary.info": "2.0.8", "script.embuary.helper": "2.0.8",
    "plugin.video.themoviedb.helper": "5.4.16", "script.skin.info.service": "2.0.0",
    "script.xbmcbackup": "1.7.3",
}
# Unchanged APIs keep the original floor; publication maxima belong to closure.
COMPAT_LOCALIZATION_PREFIXES = (
    "1080i/script-script.extendedinfo-", "1080i/script-nextup-notification-",
)
ENGLISH_LOCALES = tuple("language/resource.language.%s/strings.po" % name for name in ("en_gb", "en_us"))
INFO_BLUR_WINDOWS = (("DialogAddonInfo", "addoninformation"), ("DialogMusicInfo", "musicinformation"),
                     ("DialogVideoInfo", "movieinformation"))
ENABLED_HELPERS = ("script.skin.info.service", "script.embuary.helper", "script.embuary.info",
                   "plugin.video.themoviedb.helper")


def po_messages(data):
    """Read singular UTF-8 PO entries with stdlib string-literal decoding only.

    Supports multiline strings/comments; rejects unsupported syntax rather than
    silently discarding an entry. This is not a general gettext/plural validator.
    """
    messages, duplicates, fields = {}, [], {}
    field = None

    def finish():
        context = fields.get("msgctxt", "")
        if context:
            if not re.fullmatch(r"#\d+", context) or not {"msgid", "msgstr"} <= fields.keys():
                raise ValueError("Expected numeric Kodi context and singular msgid/msgstr: " + context)
            number = int(context[1:])
            if number in messages:
                duplicates.append(number)
            messages[number] = fields["msgstr"]
        fields.clear()

    for number, raw in enumerate(data.decode("utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line:
            finish()
            field = None
            continue
        if line.startswith("#"):
            continue
        match = re.fullmatch(r'(msgctxt|msgid|msgstr)\s+(".*")', line)
        if match:
            if match[1] == "msgctxt" and "msgctxt" in fields:
                finish()
            field, literal = match.groups()
            if field in fields:
                raise ValueError("Duplicate PO field at line %d" % number)
            fields[field] = ""
        elif line.startswith('"') and field is not None:
            literal = line
        else:
            raise ValueError("Unsupported PO syntax at line %d" % number)
        try:
            value = ast.literal_eval(literal)
        except (ValueError, SyntaxError) as error:
            raise ValueError("Invalid PO string at line %d" % number) from error
        if not isinstance(value, str):
            raise ValueError("Non-string PO value at line %d" % number)
        fields[field] += value
    finish()
    return messages, sorted(set(duplicates))


def localization_checks(checks, source, roots):
    referenced = set()
    for root in roots.values():
        for node in root.iter():
            for value in (node.text or "", *node.attrib.values()):
                referenced.update(map(int, re.findall(r"\$LOCALIZE\[(319\d{2})\]", value)))
            if node.tag in ("label", "label2") and re.fullmatch(r"319\d{2}", node.text or ""):
                referenced.add(int(node.text))
    result = {"referenced_migration_ids": sorted(referenced), "english": {}}
    for name in ENGLISH_LOCALES:
        messages, duplicates, error = {}, [], ""
        try:
            if name not in source.files:
                raise ValueError("Required English catalog missing")
            messages, duplicates = po_messages(source.read(name))
        except (UnicodeError, ValueError) as exception:
            error = str(exception)
        missing = sorted(number for number in referenced if not messages.get(number, "").strip())
        checks.require("locale:parse:" + name, not error, error)
        checks.require("locale:unique-ids:" + name, not duplicates, str(duplicates))
        checks.require("locale:migration-references:" + name, not missing, "Missing/empty English IDs: " + str(missing))
        result["english"][name] = {"entries": len(messages), "duplicates": duplicates, "missing_or_empty": missing, "error": error}
    return result


def source_providers(roots):
    """Authored provider consumers, not plugin-path styling comparisons.

    No dynamic label/include evaluation. Dependency functions and $ADDON reads
    count separately from literal URLs in actions/content/artwork. Retained
    compatibility-window localizations are reported, not treated as invocations.
    """
    active, compatibility = [], []
    addon_id = r"((?:script|plugin|service|resource)\.[\w.-]+)"
    action_tags = {"onclick", "onfocus", "onunfocus", "onload", "onunload", "action",
                   "onleft", "onright", "onup", "ondown", "onback", "oninfo"}
    data_tags = {"content", "shortcut", "value", "texture", "imagepath", "thumb", "icon"}
    for name, root in roots.items():
        for node in root.iter():
            fields = [node.text or "", *node.attrib.values()]
            for value in fields:
                for addon in re.findall(r"(?:System\.(?:HasAddon|AddonIsEnabled|AddonVersion)|Addon\.HasSettings)\(\s*" + addon_id, value, re.I):
                    active.append({"path": name, "addon": addon, "kind": "dependency-function"})
                for addon in re.findall(r"\$ADDON\[\s*" + addon_id, value, re.I):
                    record = {"path": name, "addon": addon, "kind": "addon-localization"}
                    (compatibility if name.startswith(COMPAT_LOCALIZATION_PREFIXES) else active).append(record)
            authored = node.tag in action_tags | data_tags
            value = node.text or ""
            if node.tag == "param" and node.get("name", "").lower() in action_tags | {"content", "content2", "content3", "path", "texture", "imagepath"}:
                authored, value = True, node.get("value", "")
            if not authored:
                continue
            for addon in re.findall(r"(?:RunScript|RunAddon|InstallAddon|Addon.OpenSettings)\(\s*" + addon_id, value, re.I):
                active.append({"path": name, "addon": addon, "kind": "builtin"})
            # URLs in a builtin action are arguments. Plain data URLs must start
            # the authored value; String.StartsWith(...,plugin://...) is styling.
            urls = value if node.tag in action_tags or re.match(r"\s*(?:ActivateWindow|RunPlugin|RunScript|PlayMedia|RunAddon)\(", value, re.I) else value.lstrip() if value.lstrip().startswith(("plugin://", "resource://", "special://home/addons/")) else ""
            for addon in re.findall(r"(?:plugin://|resource://|special://home/addons/)" + addon_id, urls, re.I):
                active.append({"path": name, "addon": addon, "kind": "provider-path"})
    def unique(records):
        return [dict(zip(("path", "addon", "kind"), key)) for key in sorted({(n["path"], n["addon"], n["kind"]) for n in records})]
    return unique(active), unique(compatibility)


def online_toggle_errors(row):
    """Closed two-state fixture for this one settings row; not a Kodi evaluator.

    CGUIAction snapshots all conditions before running any onclick. Verify both
    old opt-in states and require its unconditional toggle to run last.
    """
    if row is None:
        return ["missing opt-in settings row"]
    clicks = row.findall("onclick")
    toggle = "Skin.ToggleSetting(Aura.OnlineEnrichment)"
    if len(clicks) != 5 or clicks[-1].text != toggle or clicks[-1].attrib or any(n.text == toggle for n in clicks[:-1]):
        return ["expected four provider actions followed by one unconditional opt-in toggle"]
    flag = "Skin.HasSetting(Aura.OnlineEnrichment)"
    errors = []
    for old in (False, True):
        flags = {"SkinInfo.Service.Online": old, "TMDbHelper.Service": old}
        # Conditions use the snapshot, not the value after a preceding action.
        eligible = []
        for node in clicks[:-1]:
            condition = (node.get("condition") or "").strip()
            if condition not in (flag, "!" + flag):
                errors.append("unrecognized provider transition condition: " + condition)
            eligible.append(old if condition == flag else not old if condition == "!" + flag else False)
        for node, enabled in zip(clicks[:-1], eligible):
            match = re.fullmatch(r"Skin\.(SetBool|Reset)\((SkinInfo\.Service\.Online|TMDbHelper\.Service)\)", node.text or "")
            if match is None:
                errors.append("unrecognized provider transition action: " + (node.text or ""))
            elif enabled:
                flags[match[2]] = match[1] == "SetBool"
        if any(value != (not old) for value in flags.values()):
            errors.append("old opt-in=%s does not transition both provider flags to %s" % (old, not old))
    return sorted(set(errors))


def python_expressions(text):
    """Extract balanced $PYTHON[...] bodies, respecting Python strings/brackets."""
    offset = 0
    while True:
        start = text.find("$PYTHON[", offset)
        if start < 0:
            return
        body = start + len("$PYTHON[")
        index, depth, quote = body, 1, None
        while index < len(text):
            char = text[index]
            if quote:
                if char == "\\":
                    index += 2
                    continue
                if text.startswith(quote, index):
                    index += len(quote)
                    quote = None
                    continue
            elif char in "\"'":
                quote = char * 3 if text.startswith(char * 3, index) else char
                index += len(quote)
                continue
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    yield text[body:index]
                    offset = index + 1
                    break
            index += 1
        else:
            raise ValueError("Unterminated $PYTHON expression")


def signature(element):
    """All attributes/text/children are significant; indentation is not appearance."""
    def content(text):
        return text if text and text.strip() else ""

    return (element.tag, sorted(element.attrib.items()), content(element.text),
            tuple((signature(child), content(child.tail)) for child in element))


def control(root, number, kind):
    matches = root.findall(".//control[@id='" + str(number) + "']")
    return matches[0] if len(matches) == 1 and matches[0].get("type") == kind else None


def direct_native(element):
    """Check direct XML only; known include/default guards run separately."""
    return element is not None and not any(element.findall(".//" + tag) for tag in (
        "onclick", "onfocus", "onunfocus", "visible", "enable",
    ))


def has_style(element, name):
    includes = element.findall("include") if element is not None else []
    return len(includes) == 1 and includes[0].text == name and not includes[0].attrib and not len(includes[0])


class Checks:
    def __init__(self):
        self.results = []

    def require(self, name, condition, detail=""):
        self.results.append({"check": name, "passed": bool(condition), "detail": detail})


def check_source(source, index_bytes=None):
    checks = Checks()
    roots, raw = {}, {}
    counts = {"xml": 0, "xsp": 0, "python_expressions": 0, "seek_expressions": 0}
    seek_by_file, invalid_seek = {}, []
    for name in source.files:
        suffix = Path(name).suffix.lower()
        if suffix not in (".xml", ".xsp"):
            continue
        counts[suffix[1:]] += 1
        data = source.read(name)
        raw[name] = data
        try:
            root = ET.fromstring(data)
            roots[name] = root
            checks.require("parse:" + name, True)
        except ET.ParseError as error:
            checks.require("parse:" + name, False, str(error))
            continue
        # XML decoding resolves entities before Python syntax is examined.
        values = []
        for element in root.iter():
            values.extend(element.attrib.values())
            values.extend(value for value in (element.text, element.tail) if value)
        for value in values:
            for match in re.finditer(r"(?<![\w.])Player\.HasPerformedSeek\b(?:\s*\([^)]*\))?", value, re.I):
                if match[0] == "Player.HasPerformedSeek(3)":
                    seek_by_file[name] = seek_by_file.get(name, 0) + 1
                else:
                    invalid_seek.append({"path": name, "expression": match[0]})
        try:
            for value in values:
                for expression in python_expressions(value):
                    counts["python_expressions"] += 1
                    label = "python:%s:%d" % (name, counts["python_expressions"])
                    try:
                        ast.parse(expression, filename=name, mode="eval")
                        checks.require(label, True)
                    except SyntaxError as error:
                        checks.require(label, False, str(error))
        except ValueError as error:
            checks.require("python:" + name, False, str(error))
    required = (set(source.original_files) - REMOVED_RUNTIME) | ADDED_RUNTIME
    # Preserve every existing XML/XSP guard and explicitly require the one new
    # distribution notice for candidates. Historical baseline bytes omit it.
    required = {name for name in required if Path(name).suffix.lower() in (".xml", ".xsp")}
    if not source.baseline:
        required |= RUNTIME_REVIEW_ADDITIONS
    missing = sorted(required - set(source.files))
    checks.require("inventory:required-runtime", not missing, ", ".join(missing))
    checks.require("inventory:removed-runtime", not REMOVED_RUNTIME.intersection(source.files),
                   ", ".join(sorted(REMOVED_RUNTIME.intersection(source.files))))
    removed = [name for name, data in raw.items() if re.search(b"DisplayAfterSeek", data, re.I)]
    checks.require("removed:DisplayAfterSeek", not removed, ", ".join(removed))
    counts["seek_expressions"] = sum(seek_by_file.values())
    checks.require("seek:total7", counts["seek_expressions"] == 7,
                   "actual=%d; expected=7 exact Player.HasPerformedSeek(3)" % counts["seek_expressions"])
    for name, expected in SEEK_COUNTS.items():
        checks.require("seek:count:" + name, seek_by_file.get(name, 0) == expected,
                       "actual=%d; expected=%d" % (seek_by_file.get(name, 0), expected))
    checks.require("seek:no-invalid-interval", not invalid_seek, json.dumps(invalid_seek, sort_keys=True))

    def xml(name):
        return roots.get(name, ET.Element("missing"))

    # Compare only these known style definitions, not Kodi's general include graph.
    original_roots = {}

    def original_xml(name):
        if name not in original_roots:
            original_roots[name] = ET.fromstring(source.original(name))
        return original_roots[name]

    for style, path in STYLE_INCLUDES.items():
        xpath = "./include[@name='%s']" % style
        actual, original = xml(path).findall(xpath), original_xml(path).findall(xpath)
        checks.require("style-include:baseline:" + style,
                       len(actual) == len(original) == 1 and signature(actual[0]) == signature(original[0]),
                       "Scoped definition comparison to git show 203aba5:" + path)
    for kind in DEFAULT_TYPES:
        xpath = "./default[@type='%s']" % kind
        checks.require("default-style:baseline:" + kind,
                       [signature(node) for node in xml("1080i/Defaults.xml").findall(xpath)] ==
                       [signature(node) for node in original_xml("1080i/Defaults.xml").findall(xpath)],
                       "Includes absence of defaults for types with no baseline entry")

    addon = xml("addon.xml")
    identity = {"id": "skin.aura", "name": "Aura", "provider-name": "kcook98765",
                "version": BASELINE_VERSION if source.baseline else VERSION}
    checks.require("manifest:identity", all(addon.get(key) == value for key, value in identity.items()), str(addon.attrib))
    for dependency, expected in OFFICIAL_MINIMUMS.items():
        imports = addon.findall("./requires/import[@addon='%s']" % dependency)
        version = imports[0].get("version", "") if len(imports) == 1 else ""
        try:
            valid = version_key(version) >= version_key(expected)
        except ValueError:
            valid = False
        valid = valid and bool(imports) and imports[0].get("optional", "false").lower() != "true"
        checks.require("dependency:" + dependency, valid, "actual=%r; required=%s%s" % (
            version, expected, "+"))
    for dependency in LEGACY_DEPENDENCIES:
        checks.require("dependency:removed:" + dependency,
                       not addon.findall("./requires/import[@addon='%s']" % dependency))
    imports = addon.findall("./requires/import")
    checks.require("dependency:unique-imports", len({node.get("addon") for node in imports}) == len(imports))
    checks.require("dependency:no-cherrypy", not addon.findall("./requires/import[@addon='script.module.cherrypy']"))
    for name in ("SettingsCategory", "DialogSettings", "DialogAddonSettings"):
        template = control(xml("1080i/" + name + ".xml"), 15, "colorbutton")
        checks.require("settings:colorbutton15:" + name, direct_native(template))
        style = "Defs_Settings_Button" if name == "SettingsCategory" else "Dialog_Standard_ListButton"
        checks.require("settings:style15:" + name, has_style(template, style), "Required direct style include: " + style)
    slider = control(xml("1080i/SettingsCategory.xml"), 13, "sliderex")
    checks.require("settings:general-slider13", direct_native(slider))
    checks.require("settings:general-slider13-style", has_style(slider, "Defs_Settings_Button"))
    defaults = xml("1080i/Defaults.xml").findall("./default[@type='colorbutton']")
    expected_default = copy.deepcopy(original_xml("1080i/Defaults.xml").find("./default[@type='button']"))
    expected_default.set("type", "colorbutton")
    expected_default.extend(ET.fromstring("""<swatch>
        <colorwidth>32</colorwidth><colorheight>32</colorheight>
        <colorposx>0</colorposx><colorposy>0</colorposy>
        <texturecolormask>common/white.png</texturecolormask>
        <texturecolordisabledmask colordiffuse="dialog_fg_30">common/white.png</texturecolordisabledmask>
    </swatch>"""))
    checks.require("settings:colorbutton-default", len(defaults) == 1 and
                   signature(defaults[0]) == signature(expected_default),
                   "Expected native default: baseline button styling plus fixed 32px color swatch")

    picker = xml("1080i/DialogColorPicker.xml")
    checks.require("picker:header1", control(picker, 1, "label") is not None)
    panel = control(picker, 6, "panel")
    checks.require("picker:panel6", panel is not None)
    checks.require("picker:defaultfocus6", picker.findtext("defaultcontrol") == "6")
    cancel = control(picker, 7, "button")
    checks.require("picker:cancel7", direct_native(cancel) and cancel.findtext("label") in ("222", "$LOCALIZE[222]"))
    checks.require("picker:cancel7-style", has_style(cancel, "Dialog_Standard_Right_Buttons"))
    for layout in ("itemlayout", "focusedlayout"):
        values = panel.findall("./" + layout + "//colordiffuse") if panel is not None else []
        checks.require("picker:palette:" + layout, any(value.text == "$INFO[ListItem.Label2]" for value in values))
    checks.require("picker:no-runscript", "1080i/DialogColorPicker.xml" in raw and
                   b"runscript" not in raw["1080i/DialogColorPicker.xml"].lower())

    favourites = xml("1080i/MyFavourites.xml")
    checks.require("favourites:media-window", favourites.tag == "window" and
                   not favourites.get("type") and not favourites.get("id"))
    checks.require("favourites:views450", favourites.findtext("views") == "450")
    checks.require("favourites:defaultfocus450", favourites.findtext("defaultcontrol") == "450")
    checks.require("favourites:heading1", control(favourites, 1, "label") is not None)
    panel = control(favourites, 450, "panel")
    checks.require("favourites:panel450", panel is not None)
    original = control(ET.fromstring(source.original("1080i/DialogFavourites.xml")), 450, "panel")
    appearance = copy.deepcopy(panel)
    if appearance is not None:
        for viewtype in appearance.findall("viewtype"):
            appearance.remove(viewtype)
    checks.require("favourites:original-panel-appearance", appearance is not None and
                   original is not None and signature(appearance) == signature(original),
                   "Complete panel compared to git show 203aba5:1080i/DialogFavourites.xml; only viewtype metadata excluded")
    checks.require("favourites:no-legacy-dialog", "1080i/DialogFavourites.xml" not in source.files)
    overrides = xml("shortcuts/overrides.xml")
    for function in ("ActivateWindow", "activatewindow"):
        for window in ("Favourites", "favourites"):
            action = "%s(%s)" % (function, window)
            matches = overrides.findall("./override[@action='%s']" % action)
            checks.require("favourites:override:" + action, len(matches) == 1 and
                           matches[0].get("version") == "21" and
                           [child.text for child in matches[0].findall("action")] == ["ActivateWindow(FavouritesBrowser)"])

    manager = xml("1080i/DialogVideoManager.xml")
    checks.require("video-manager:list50", control(manager, 50, "list") is not None)
    checks.require("video-manager:header2", control(manager, 2, "label") is not None)
    checks.require("video-manager:defaultfocus50", manager.findtext("defaultcontrol") == "50")
    visibility = {22: "managevideoversions", 24: "managevideoversions", 25: "managevideoversions",
                  23: "managevideoextras", 28: "managevideoextras"}
    parents = {child: parent for parent in manager.iter() for child in parent}
    for number in range(21, 29):
        button = control(manager, number, "button")
        checks.require("video-manager:button%d" % number, button is not None)
        checks.require("video-manager:button%d-style" % number, has_style(button, "Dialog_Standard_Right_Buttons"))
        expected = ["Window.IsVisible(%s)" % visibility[number]] if number in visibility else []
        actual = [node.text for node in button.findall("visible")] if button is not None else None
        ancestor, inherited = parents.get(button), []
        while ancestor is not None:
            inherited.extend(ancestor.findall("visible"))
            ancestor = parents.get(ancestor)
        checks.require("video-manager:visibility%d" % number, actual == expected and not inherited,
                       "actual=%r; expected=%r; inherited=%d" % (actual, expected, len(inherited)))
    standard = xml("1080i/Includes_Dialog.xml").find("./include[@name='Dialog_Select_Standard']")
    secondary = control(standard, 8, "button") if standard is not None else None
    checks.require("select:secondary8-in-include", direct_native(secondary))
    checks.require("select:secondary8-style", has_style(secondary, "Dialog_Standard_Right_Buttons"))
    checks.require("select:include-connected", any(
        node.text == "Dialog_Select_Standard" for node in xml("1080i/DialogSelect.xml").findall(".//include")))
    migration_checks(checks, source, roots, original_xml)
    localization = localization_checks(checks, source, roots)
    warnings = list(WARNINGS)
    closure = None
    active_closure = None
    active, compatibility = source_providers(roots)
    if index_bytes is not None:
        closure = dependency_closure(addon, index_bytes)
        checks.require("dependency:official-recursive-closure", not closure["failures"],
                       json.dumps(closure["failures"], sort_keys=True))
        checks.require("dependency:official-published-optional-closure", not closure["optional_failures"],
                       json.dumps(closure["optional_failures"], sort_keys=True))
        warnings.extend(closure["warnings"])
        # Active optional integrations need their own required graph even when
        # Aura's manifest does not import them. Localization-only compatibility
        # windows do not launch a provider and remain separate diagnostics.
        active_manifest = ET.Element("addon", id="skin.aura:authored-providers")
        active_requires = ET.SubElement(active_manifest, "requires")
        minima = {node.get("addon"): node.get("version", "0.0.0") for node in addon.findall("./requires/import")}
        for dependency in sorted({record["addon"] for record in active}):
            ET.SubElement(active_requires, "import", addon=dependency, version=minima.get(dependency, "0.0.0"))
        active_closure = dependency_closure(active_manifest, index_bytes)
        checks.require("dependency:active-providers-official", not active_closure["failures"],
                       json.dumps(active_closure["failures"], sort_keys=True))
        checks.require("dependency:active-published-optional-closure", not active_closure["optional_failures"],
                       json.dumps(active_closure["optional_failures"], sort_keys=True))
        warnings.append("Active provider audit: %d IDs; %d unavailable optional edges; %d published-optional failures." % (
            len(active_requires), len(active_closure["unavailable_optional_edges"]), len(active_closure["optional_failures"])))
        published = {node.get("id") for node in ET.fromstring(index_bytes).findall("addon")} | set(CORE)
        for record in compatibility:
            record["published"] = record["addon"] in published
        if compatibility:
            warnings.append("Compatibility-window localization-only diagnostics: " + json.dumps(compatibility, sort_keys=True))
    else:
        warnings.append("Official recursive closure NOT CHECKED: supply --index /path/to/official/omega/addons.xml; no automatic download.")
    changes = source.deltas()
    unexpected = [change for change in changes if change["path"] not in FOCUSED_DELTA]
    checks.require("preservation:baseline-runtime", not unexpected, json.dumps(unexpected, sort_keys=True))
    return {
        **source.provenance(), "counts": counts, "checks": checks.results,
        "seek_by_file": seek_by_file, "invalid_seek": invalid_seek,
        "official_closure": closure,
        "active_provider_closure": active_closure, "active_provider_references": active,
        "compatibility_localizations": compatibility,
        "localization": localization,
        "warnings": warnings, "failures": sum(not item["passed"] for item in checks.results),
    }


def confirmation_checks(checks, roots, original_xml):
    """Closed confirmation/Home guards; comments are ignored by the XML parser."""
    dialog = roots.get("1080i/DialogConfirm.xml", ET.Element("missing"))
    home = roots.get("1080i/Home.xml", ET.Element("missing"))
    original_dialog = copy.deepcopy(original_xml("1080i/DialogConfirm.xml"))
    old_action = "RunScript(script.skinshortcuts,type=manage&group=mainmenu)"
    flag = "!Skin.HasSetting(WidgetsInit)"
    hooks = [node for node in original_dialog.findall("onunload")
             if node.attrib == {"condition": flag} and node.text == old_action and not len(node)]
    for node in hooks:
        original_dialog.remove(node)
    checks.require("confirmation:no-editor-onunload", not any(
        re.search(r"script\.skinshortcuts.*type=manage", node.text or "", re.I)
        for node in dialog.findall("onunload")))
    checks.require("confirmation:original-minus-exact-hook", len(hooks) == 1 and
                   signature(dialog) == signature(original_dialog),
                   "Complete git show 203aba5 dialog signature; remove only the exact old WidgetsInit manage hook")
    checks.require("confirmation:native-buttons-and-focus", all(
        direct_native(control(dialog, number, "button")) and
        control(dialog, number, "button").findtext("description") == description and
        control(dialog, number, "button").findtext("label") == label
        for number, description, label in ((10, "No", "106"), (11, "Yes", "107"))) and
        [signature(n) for n in dialog.findall("defaultcontrol")] ==
        [signature(n) for n in original_dialog.findall("defaultcontrol")])

    original_home = original_xml("1080i/Home.xml")
    build = [n for n in home.findall("onload") if (n.text or "").startswith("RunScript(script.skinshortcuts,")]
    original_build = [n for n in original_home.findall("onload") if (n.text or "").startswith("RunScript(script.skinshortcuts,")]
    expected_args = {"type": "buildxml", "mainmenuID": "300", "mode": "single", "group": "mainmenu|powermenu"}
    arguments = parse_qsl((build[0].text or "")[len("RunScript(script.skinshortcuts,"):-1]) if len(build) == 1 else []
    checks.require("home:unchanged-buildxml-arguments", len(build) == len(original_build) == 1 and
                   signature(build[0]) == signature(original_build[0]) and
                   len(arguments) == len(expected_args) and dict(arguments) == expected_args)
    init = [n for n in home.findall("onload") if n.text == "Skin.SetBool(WidgetsInit)"]
    checks.require("home:widgets-init-before-buildxml", len(init) == len(build) == 1 and
                   init[0].attrib == {"condition": flag} and not len(init[0]) and
                   list(home).index(init[0]) < list(home).index(build[0]))
    checks.require("home:original-controls-and-focus4000", len(home.findall("controls")) == 1 and
                   signature(home.find("controls")) == signature(original_home.find("controls")) and
                   home.findtext("defaultcontrol") == "4000" and
                   [signature(n) for n in home.findall("defaultcontrol")] ==
                   [signature(n) for n in original_home.findall("defaultcontrol")])
    services = roots.get("1080i/Includes.xml", ET.Element("missing")).find("include[@name='Aura_Services_OnLoad']")
    startup_nodes = [dialog, home] + ([services] if services is not None else [])
    checks.require("confirmation:no-forced-editor-dialog-or-menu-reset", not any(
        re.search(r"script\.skinshortcuts.*type=(?:manage|reset\w*)|(?:Activate|Replace)Window\s*\(|"
                  r"Dialog\s*\.|Skin\.(?:ResetAll\s*\(|(?:Reset|ToggleSetting)\s*\(WidgetsInit\s*\))",
                  node.text or "", re.I)
        for root in startup_nodes for node in root.iter()))
    editor = roots.get("1080i/script-skinshortcuts.xml", ET.Element("missing"))
    warmup = [n for n in editor if n.tag in ("onload", "onunload") and n.get("condition") == flag]
    expected_warmup = [n for n in original_xml("1080i/script-skinshortcuts.xml")
                       if n.tag in ("onload", "onunload") and n.get("condition") == flag]
    checks.require("editor:original-widgets-init-warmup-guard", len(warmup) == 2 and
                   [signature(n) for n in warmup] == [signature(n) for n in expected_warmup] and
                   [n.text for n in warmup] == ["AlarmClock(Clickit,Action(Close),00:01,silent)", "Skin.ToggleSetting(WidgetsInit)"])


def migration_checks(checks, source, roots, original_xml):
    """Named source guards. No Kodi expressions or add-on code are executed."""
    def xml(name):
        return roots.get(name, ET.Element("missing"))

    def text(node):
        return ET.tostring(node, encoding="unicode")

    def actions(root, tag="onclick"):
        return [(node.text or "").strip() for node in root.iter(tag)]

    confirmation_checks(checks, roots, original_xml)
    legacy = []
    for name, root in roots.items():
        active = text(root)
        # These saved skin keys still drive native artwork preferences.
        active = re.sub(r"(Skin\.(?:HasSetting|ToggleSetting|SetBool|Reset|String|SetString)\(\s*)SkinHelper\.(?:EnableAnimatedPosters|EnableExtraFanart)(?=\s*[,\)])", r"\1SavedNativeArtworkKey", active, flags=re.I)
        if re.search(r"SkinHelper\.|script\.skin\.helper|script\.tv\.show\.next\.aired|script-NextAired|Includes_NextAired|script-skin_helper_service-ColorPicker|script\.module\.(?:metadatautils|musicbrainz|thetvdb)|smartshortcuts|widgetreload", active, re.I):
            legacy.append(name)
    checks.require("migration:no-active-legacy-helper", not legacy, ", ".join(legacy))
    settings = xml("1080i/SkinSettings.xml")
    ratings_path = "1080i/Custom_1118_EnableRatings.xml"
    expected_ratings = copy.deepcopy(original_xml(ratings_path))
    for number, label in ((9003, "31905"), (9005, "31906")):
        expected_ratings.find(".//control[@id='%d']/label" % number).text = "$LOCALIZE[%s]" % label
    checks.require("preservation:ratings-dialog-two-labels-only", signature(xml(ratings_path)) == signature(expected_ratings),
                   "Complete original dialog signature with only labels 9003/9005 localized to 31905/31906")
    animated = control(settings, 9501, "radiobutton")
    original_animated = control(original_xml("1080i/SkinSettings.xml"), 9501, "radiobutton")
    checks.require("preservation:animated-posters-toggle9501", animated is not None and original_animated is not None and
                   signature(animated) == signature(original_animated),
                   "Native artwork preference: preserve original control/key/label/style; it does not invoke the old service")
    baseline_colors = original_xml("colors/defaults.xml")
    for number, key, default_name in ((9401, "focuscolor.name", "Highlight"), (9402, "gradientcolor.name", "GradientHighlight"), (9403, "overlaycolor.name", "Overlay")):
        rows = settings.findall(".//control[@id='%d']" % number)
        default = baseline_colors.findtext("color[@name='%s']" % default_name, "")
        # Kodi 21.3 SkinBuiltins.cpp:323-327 uses params[2] only when the saved
        # setting is empty. An exact baseline ARGB default preserves saved values.
        selected = r"(?:" + re.escape(default) + r"|\$INFO\[Skin\.String\(" + re.escape(key) + r"\)\])"
        expected = re.compile(r"Skin\.SetColor\(" + re.escape(key) + r",\d+," + selected + r",special://skin/extras/colors/colors\.xml\)", re.I)
        clicks = rows[0].findall("onclick") if len(rows) == 1 else []
        color_clicks = [node for node in clicks if expected.fullmatch(node.text or "") and not node.attrib]
        ancillary = [node for node in clicks if node not in color_clicks]
        valid = len(color_clicks) == 1 and (not ancillary or (key == "overlaycolor.name" and len(ancillary) == 1 and
            ((ancillary[0].text == "Skin.Reset(DisableOverlayColor)" and not ancillary[0].attrib) or
             (ancillary[0].text == "Skin.ToggleSetting(DisableOverlayColor)" and ancillary[0].get("condition") == "Skin.HasSetting(DisableOverlayColor)"))))
        checks.require("colors:native-palette-only:" + key, valid,
                       "One unconditional Skin.SetColor(key,localized-header,baseline-ARGB-or-current-key,Aura-palette) onclick required; baseline=" + default)
    palette = "extras/colors/colors.xml"
    checks.require("colors:original-palette", palette in roots and signature(xml(palette)) == signature(original_xml(palette)))
    checks.require("colors:no-custom-picker", not any(
        re.search(r"(?:skin_helper_service|skin\.info\.service|skin\.helper).*colorpicker", name, re.I) for name in source.files))
    checks.require("osd:no-helper-auto-close", not any(re.search(r"AutoClose(?:Video|Music)OSD", text(root), re.I) for root in roots.values()))
    startup = xml("1080i/Startup.xml")
    checks.require("startup:no-reset-all", not re.search(r"Skin\.ResetAll\s*\(", text(startup), re.I))
    all_actions = [value for root in roots.values() for tag in ("onload", "onfocus", "onclick") for value in actions(root, tag)]
    checks.require("enrichment:library-flag", "Skin.SetBool(SkinInfo.Service.Library)" in all_actions)
    checks.require("enrichment:no-broad-service", not any(re.search(r"Skin\.(?:SetBool|ToggleSetting)\(SkinInfo\.Service(?:,\s*true)?\)", value, re.I) for value in all_actions))
    checks.require("enrichment:startup-online-opt-in", not any(
        re.search(r"Skin\.(?:SetBool|ToggleSetting)\(Aura\.OnlineEnrichment(?:,\s*true)?\)", value, re.I) for value in actions(startup, "onload")))
    expressions = {node.get("name"): node.text or "" for root in roots.values() for node in root.findall("expression")}
    for name in ("Aura.ItemOnline", "Aura.PlayerOnline"):
        checks.require("enrichment:opt-in-expression:" + name,
                       "Skin.HasSetting(Aura.OnlineEnrichment)" in expressions.get(name, ""))
    # Resolve only named expression references for gate presence; no condition evaluation.
    def expanded(value, stack=()):
        def replace(match):
            name = match[1]
            return "" if name in stack else expanded(expressions.get(name, ""), stack + (name,))
        return re.sub(r"\$EXP\[([^]]+)\]", replace, value)

    def opt_in(value):
        return bool(re.search(r"(?<!!)Skin\.HasSetting\(Aura\.OnlineEnrichment\)", expanded(value), re.I))

    # One known parameterized include: verify its actual wrapper binding before
    # treating the caller's visible parameter as a gate. No generic expansion.
    info_section = xml("1080i/Includes_Object.xml").find("include[@name='Object_VideoInfo_InfoSection']")
    info_visible = info_section.findall("./definition/control[@type='group']/visible") if info_section is not None else []
    info_visible_wired = any(n.text == "$PARAM[visible]" for n in info_visible)
    checks.require("enrichment:info-section-visible-param", info_visible_wired)
    ungated = []
    for name, root in roots.items():
        parents = {child: parent for parent in root.iter() for child in parent}
        for node in root.iter():
            value = " ".join([node.text or "", *node.attrib.values()])
            if not (re.search(r"SkinInfo\.(?:Player\.)?Online\.", value) or
                    re.search(r"(?:RunScript\(|plugin://)plugin\.video\.themoviedb\.helper", value, re.I) or
                    ("plugin://script.skin.info.service" in value and ("online=true" in value or "tmdb_id=" in value))):
                continue
            context, ancestor = node.get("condition", ""), node
            while ancestor is not None:
                context += " " + " ".join(n.text or "" for n in ancestor.findall("visible"))
                if ancestor.tag == "include" and ancestor.get("content") == "Object_VideoInfo_InfoSection" and info_visible_wired:
                    context += " " + " ".join(n.get("value", "") for n in ancestor.findall("param[@name='visible']"))
                ancestor = parents.get(ancestor)
            if not opt_in(context + (value if node.tag == "expression" else "")):
                ungated.append(name + ":" + node.tag + ":" + value[:100])
    checks.require("enrichment:online-consumers-gated", not ungated, "; ".join(ungated))
    online_row = control(settings, 9513, "radiobutton")
    transition_errors = online_toggle_errors(online_row)
    checks.require("enrichment:online-toggle-transition", not transition_errors, "; ".join(transition_errors))
    transition_nodes = set(online_row.findall("onclick")) if online_row is not None and not transition_errors else set()
    online_flags = []
    for name, root in roots.items():
        for node in root.iter():
            if re.search(r"Skin\.(?:SetBool|ToggleSetting)\((?:SkinInfo\.Service\.Online|TMDbHelper\.Service)(?:,\s*true)?\)", node.text or "", re.I) and node not in transition_nodes and not opt_in(node.get("condition", "")):
                online_flags.append(name + ":" + node.tag)
    checks.require("enrichment:online-flags-opt-in", not online_flags, ", ".join(online_flags))
    services = xml("1080i/Includes.xml").find("include[@name='Aura_Services_OnLoad']")
    checks.require("enrichment:service-onload-connected", services is not None and all(
        sum(node.text == "Aura_Services_OnLoad" for node in xml("1080i/" + name + ".xml").findall("include")) == 1
        for name in ("Startup", "Home", "SkinSettings")))
    checks.require("startup:included-services-no-reset-all", services is not None and not re.search(r"Skin\.ResetAll\s*\(", text(services), re.I))
    global_root = xml("1080i/Includes_Global.xml")
    object_root = xml("1080i/Includes_Object.xml")
    identity_include = object_root.find("include[@name='Object_Aura_BlurSource']")
    probe = control(identity_include, 7978, "label") if identity_include is not None else None
    checks.require("blur:native-source7978", probe is not None and probe.findtext("label") == "$VAR[Aura_BlurImage]" and
                   probe.findtext("left") == "-2160" and probe.findtext("width") == probe.findtext("height") == "1" and
                   sum(len(root.findall(".//control[@id='7978']")) for root in roots.values()) == 1)
    checks.require("blur:base-shared-identity", len(global_root.findall("include[@name='Global_Background']/include[.='Object_Aura_BlurSource']")) == 1)
    image_probe = control(global_root, 7975, "multiimage")
    probe_gate = "Skin.HasSetting(EnableBlur) + Skin.HasSetting(SkinInfo.Blur) + Skin.HasSetting(SkinInfo.Service.Library) + System.AddonIsEnabled(script.skin.info.service)"
    checks.require("blur:unblurred-frame-probe7975", image_probe is not None and
                   image_probe.findtext("imagepath") == "$VAR[Global_Background_Image_Var]" and
                   image_probe.findtext("visible") == probe_gate and image_probe.findtext("left") == "-2160" and
                   image_probe.findtext("width") == image_probe.findtext("height") == "1")
    image_values = global_root.findall("variable[@name='Aura_BlurImage']/value")
    checks.require("blur:current-frame-only", len(image_values) == 4 and
                   image_values[-1].text == "$INFO[Control.GetLabel(7975)]" and image_values[-1].attrib == {
                       "condition": "Control.IsVisible(7975) + !String.IsEmpty(Control.GetLabel(7975))"})
    checks.require("blur:qualified-dialog-priority", len(image_values) == 4 and all(
        node.text == "$INFO[Window(%s).Property(Aura.Blur.InfoImage)]" % window and
        node.attrib == {"condition": "Window.IsVisible(%s.xml)" % name}
        for node, (name, window) in zip(image_values[:3], INFO_BLUR_WINDOWS)),
        "Visible native dialogs return their entry snapshot, including empty snapshots, before the base-frame fallback")
    native_sources = global_root.findall("variable[@name='Aura_InfoBlurNative']/value")
    native_art = ("tvshow.fanart", "artist.fanart", "fanart", "thumb")
    checks.require("blur:dialog-native-single-image", len(native_sources) == len(native_art) and all(
        node.text == "$INFO[ListItem.Art(%s)]" % art and node.attrib == {"condition": "!String.IsEmpty(ListItem.Art(%s))" % art}
        for node, art in zip(native_sources, native_art)), "Only native image artwork; no directory or blurred-image fallback")
    capture = object_root.find("include[@name='Object_Aura_InfoBlur_OnLoad']")
    capture_body = capture.find("definition") if capture is not None else None
    expected_capture = ET.fromstring('''<definition>
        <onload>SetProperty(Aura.Blur.InfoImage,$ESCVAR[Aura_InfoBlurNative],$PARAM[window])</onload>
        <onunload>ClearProperty(Aura.Blur.InfoImage,$PARAM[window])</onunload>
    </definition>''')
    checks.require("blur:dialog-capture-template", capture_body is not None and signature(capture_body) == signature(expected_capture))
    for name, window in INFO_BLUR_WINDOWS:
        dialog = xml("1080i/" + name + ".xml")
        callers = dialog.findall("include[@content='Object_Aura_InfoBlur_OnLoad']")
        expected = ET.fromstring('<include content="Object_Aura_InfoBlur_OnLoad"><param name="window" value="%s" /></include>' % window)
        checks.require("blur:dialog-capture:" + name, len(callers) == 1 and signature(callers[0]) == signature(expected) and
                       dialog.find("controls") is not None and list(dialog).index(callers[0]) < list(dialog).index(dialog.find("controls")))
        shared = dialog.findall("controls/include[.='Object_Aura_BlurSource']")
        checks.require("blur:dialog-shared-identity:" + name, len(shared) == 1 and not shared[0].attrib and not len(shared[0]))
    # This dialog was otherwise untouched: remove exactly the two authorized
    # additions for a complete baseline comparison, preserving all other flags,
    # labels, layout, and native actions. Their contents are checked above.
    addon_dialog = copy.deepcopy(xml("1080i/DialogAddonInfo.xml"))
    for node in addon_dialog.findall("include[@content='Object_Aura_InfoBlur_OnLoad']"):
        addon_dialog.remove(node)
    addon_controls = addon_dialog.find("controls")
    if addon_controls is not None:
        for node in addon_controls.findall("include[.='Object_Aura_BlurSource']"):
            addon_controls.remove(node)
    checks.require("preservation:addon-info-blur-additions-only", signature(addon_dialog) == signature(original_xml("1080i/DialogAddonInfo.xml")))
    source_var = global_root.find("variable[@name='Global_Background_Image_Var']")
    checks.require("blur:unblurred-source", source_var is not None and not re.search(
        r"BlurredImage|\$VAR\[(?:Aura_BlurImage|Global_Background_Image)\]|Control.GetLabel\(797[58]\)", text(source_var)))
    service_actions = actions(services, "onload") if services is not None else []
    checks.require("blur:official-source-contract", all(
        [value for value in service_actions if value.startswith("SetProperty(SkinInfo." + key + ",")] == [expected]
        for key, expected in (("BlurSourceVar", "SetProperty(SkinInfo.BlurSourceVar,Aura_BlurImage,Home)"),
                              ("BlurPrefix", "SetProperty(SkinInfo.BlurPrefix,Aura,Home)"))))
    blurred = global_root.findall("variable[@name='Global_Background_Image']/value")
    checks.require("blur:result-identity-guard", any(n.text == "$INFO[Window(Home).Property(SkinInfo.Aura.BlurredImage)]" and all(
         token in n.get("condition", "") for token in ("Skin.HasSetting(EnableBlur)", "Skin.HasSetting(SkinInfo.Blur)",
        "Skin.HasSetting(SkinInfo.Service.Library)", "System.AddonIsEnabled(script.skin.info.service)", "!String.IsEmpty(Control.GetLabel(7978))",
        "String.IsEqual(Window(Home).Property(SkinInfo.Aura.BlurredImage.Original),Control.GetLabel(7978))")) for n in blurred))
    eligibility = global_root.findtext("expression[@name='Aura.ExtraFanartEligible']", "")
    expected_eligibility = "Skin.HasSetting(SkinHelper.EnableExtraFanart) + !ListItem.IsParentFolder + [String.IsEqual(ListItem.DBType,movie) | String.IsEqual(ListItem.DBType,tvshow)] + !String.IsEmpty(ListItem.Path) + !String.StartsWith(ListItem.Path,plugin://) + !String.StartsWith(ListItem.Path,videodb://)"
    folder = global_root.findall("variable[@name='Aura_ExtraFanartFolder']/value")
    consumers = source_var.findall("value[.='$VAR[Aura_ExtraFanartFolder]']") if source_var is not None else []
    checks.require("background:extra-fanart-current-eligibility", eligibility == expected_eligibility and len(folder) == 1 and
                   folder[0].text == "$INFO[ListItem.Path,,extrafanart/]" and folder[0].attrib == {"condition": "$EXP[Aura.ExtraFanartEligible]"} and
                   len(consumers) == 1 and all(token in consumers[0].get("condition", "") for token in (
                       "$EXP[Aura.ExtraFanartEligible]", "Integer.IsGreater(Container(7979).NumItems,0)", "!Container(7979).IsUpdating")))
    background = global_root.find("variable[@name='Global_Background_Image_NoFanart']")
    checks.require("preservation:background-folder-playlist", background is not None and signature(background) ==
                   signature(original_xml("1080i/Includes_Global.xml").find("variable[@name='Global_Background_Image_NoFanart']")))
    provider_boundary_checks(checks, roots)
    label_routes = xml("1080i/Includes_Labels.xml").findall("variable/value")
    ungated_routes = [node.text for node in label_routes if (node.text or "").startswith("plugin://script.skin.info.service/") and
                     "System.AddonIsEnabled(script.skin.info.service)" not in node.get("condition", "")]
    checks.require("providers:library-routes-enabled", not ungated_routes, str(ungated_routes))
    for mode in ("backup", "restore"):
        checks.require("backup:mode:" + mode, "RunScript(script.xbmcbackup,mode=%s)" % mode in actions(settings))
    checks.require("backup:settings", "Addon.OpenSettings(script.xbmcbackup)" in actions(settings))
    checks.require("backup:no-action-parameter", not re.search(r"RunScript\(script\.xbmcbackup,action=", text(settings), re.I))
    template = "shortcuts/template.xml"
    checks.require("preservation:widget-template", template in source.files and source.read(template) == source.original(template))
    for tag in ("widgetdefaultnode", "widgetdefault", "propertydefault", "background", "backgroundBrowse", "widgetPlaylists"):
        checks.require("preservation:native-defaults:" + tag,
                       [signature(n) for n in xml("shortcuts/overrides.xml").findall(tag)] ==
                       [signature(n) for n in original_xml("shortcuts/overrides.xml").findall(tag)])
    # Provider/editor API shapes verified from published 2.0.0 / 2.0.8 source.
    editor = xml("1080i/script-skinshortcuts.xml")
    for number, commit, alias in ((9402, 9410, "widgetName"), (9404, 9411, "WidgetSort")):
        row, handoff = control(editor, number, "button"), control(editor, commit, "button")
        start = row.findall("onclick") if row is not None else []
        finish = handoff.findall("onfocus") if handoff is not None else []
        checks.require("editor:native-input:%d" % number,
                       [n.text for n in start] == ["Skin.Reset(Aura.Shortcuts.Input)", "Skin.SetString(Aura.Shortcuts.Input)", "SetFocus(%d)" % commit] and
                       not any(n.attrib for n in start))
        checks.require("editor:deferred-escaped-commit:%d" % commit,
                       [n.text for n in finish[:3]] == ["SetProperty(customProperty,$INFO[Window.Property(%s)])" % alias,
                       "SetProperty(customValue,$ESCINFO[Skin.String(Aura.Shortcuts.Input)])", "SendClick(404)"] and
                       all(n.get("condition") == "!String.IsEmpty(Skin.String(Aura.Shortcuts.Input))" for n in finish[:3]) and
                       bool(finish) and finish[-1].text == "SetFocus(%d)" % number)
    overrides = xml("shortcuts/overrides.xml")
    widgets = [n.text for n in overrides.iter("shortcut") if (n.text or "").startswith("plugin://script.skin.info.service/")]
    for action, dbtype, seed in (("similar", "movie", "9986"), ("similar", "tvshow", "9987"),
                                 ("recommended", "movie", None), ("recommended", "tvshow", None), ("next_up", "episodes", None)):
        matches = [url for url in widgets if "action=" + action in url and (action == "next_up" or "dbtype=" + dbtype in url)]
        valid = len(matches) == 1 and "reload=$INFO[Window(Home).Property(SkinInfo.Library.Refreshed)]" in matches[0]
        if seed:
            content = xml("1080i/Includes_Widgets.xml").find(".//control[@id='%s']/content" % seed)
            valid = valid and "dbid=$INFO[Container(%s).ListItem.DBID]" % seed in matches[0] and content is not None and content.get("limit") == "1" and content.get("sortby") == "dateadded"
        checks.require("widgets:official-%s-%s" % (action, dbtype), valid)
    labels_root = xml("1080i/Includes_Labels.xml")
    similar = labels_root.find("variable[@name='Aura_InfoSimilarTV']")
    checks.require("api:similar-parent-show", similar is not None and any(
        "dbtype=tvshow&dbid=$INFO[Window.Property(Aura.Info.TVShowDBID)]" in (n.text or "") and
        all(kind in n.get("condition", "") for kind in ("episode", "season")) for n in similar.findall("value")))
    cast = labels_root.find("variable[@name='Aura_InfoCast']")
    checks.require("api:cast-online-explicit", cast is not None and any("&online=true&" in (n.text or "") for n in cast.findall("value")))
    checks.require("api:cast-parent-external-id", cast is not None and any(
        "tmdb_id=$INFO[Window.Property(Aura.Info.ShowTMDB)]" in (n.text or "") and
        "imdb_id=$INFO[Window.Property(Aura.Info.ShowIMDB)]" in (n.text or "") and
        "season=$INFO[Window.Property(Aura.Info.Season)]" in (n.text or "") and
        "episode=$INFO[Window.Property(Aura.Info.Episode)]" in (n.text or "") for n in cast.findall("value")))
    alphabet = xml("1080i/Includes_Object.xml").find(".//control[@id='8001']/content")
    checks.require("api:embuary-alphabet", alphabet is not None and
                   "plugin://script.embuary.helper/" in (alphabet.text or "") and "info=jumptoletter&showall=true" in alphabet.text)
    actor_checks(checks, roots, original_xml)
    missing_refs = []
    variable_names = {n.get("name") for root in roots.values() for n in root.findall("variable")}
    for name, root in roots.items():
        for ref in re.findall(r"\$EXP\[(Aura\.[^]]+)\]", text(root)):
            if ref not in expressions:
                missing_refs.append(name + ":" + ref)
        for ref in re.findall(r"\$VAR\[(Aura_[^],]+)", text(root)):
            if ref not in variable_names:
                missing_refs.append(name + ":" + ref)
    checks.require("api:named-references-resolve", not missing_refs, ", ".join(missing_refs))

    calendar = xml("1080i/Custom_1140_AiringCalendar.xml")
    checks.require("calendar:window1140", calendar.tag == "window" and calendar.get("id") == "1140" and
                   sum(root.tag == "window" and root.get("id") == "1140" for root in roots.values()) == 1)
    checks.require("calendar:default9000", calendar.findtext("defaultcontrol") == "9000" and control(calendar, 9000, "list") is not None)
    days = calendar.findall(".//control[@id='9000']/content/item")
    checks.require("calendar:week-and-weekday-routes", [n.findtext("property[@name='day']") for n in days] == ["week", *map(str, range(7))] and
                   all(n.findtext("onclick") == "SetProperty(Aura.Calendar.Day,%s)" % n.findtext("property[@name='day']") for n in days))
    checks.require("calendar:localized-weekdays", [n.findtext("label") for n in days[1:]] == ["$LOCALIZE[%d]" % n for n in range(11, 18)])
    content = calendar.find(".//control[@id='50']/content")
    route = "plugin://script.embuary.info/nextaired/$INFO[Window.Property(Aura.Calendar.Day)]"
    enabled = "System.AddonIsEnabled(script.embuary.info)"
    definitions = xml("1080i/Includes_Topbar.xml").findall("variable[@name='AiringCalendar_Content']")
    values = definitions[0].findall("value") if len(definitions) == 1 else []
    gate_valid = (sum(len(root.findall("variable[@name='AiringCalendar_Content']")) for root in roots.values()) == 1 and
                  len(values) == 2 and values[0].text == route and values[0].attrib == {"condition": enabled} and
                  not (values[1].text or "").strip() and not values[1].attrib and
                  len(xml("1080i/Includes.xml").findall("include[@file='Includes_Topbar.xml']")) == 1)
    checks.require("calendar:content-enabled-gate", gate_valid,
                   "Known AiringCalendar_Content variable: enabled official route, unconditional empty fallback, registered include")
    checks.require("calendar:provider-route", control(calendar, 50, "list") is not None and content is not None and content.get("browse") == "never" and
                   content.text == "$VAR[AiringCalendar_Content]" and gate_valid)
    clicks = calendar.findall(".//control[@id='50']/onclick")
    checks.require("calendar:non-playable-info", len(clicks) == 2 and
                   clicks[0].text == "RunPlugin($ESCINFO[Container(50).ListItem.FileNameAndPath])" and
                   clicks[0].get("condition") == enabled + " + String.StartsWith(Container(50).ListItem.FileNameAndPath,plugin://script.embuary.info/)" and
                   clicks[1].text == "noop" and not clicks[1].attrib and "PlayMedia(" not in text(calendar))
    labels = [(node.findtext("label", ""), node.findtext("visible", "")) for node in calendar.iter("control")]
    def terms(condition):
        return {part.strip() for part in condition.split("+")}
    checks.require("calendar:empty-state", any("$LOCALIZE[" in label and terms(condition) == {
        enabled, "!Container(50).IsUpdating", "!Integer.IsGreater(Container(50).NumItems,0)"} for label, condition in labels))
    checks.require("calendar:loading-state", any("$LOCALIZE[" in label and terms(condition) == {enabled, "Container(50).IsUpdating"} for label, condition in labels))
    checks.require("calendar:disabled-state", any("$LOCALIZE[" in label and condition == "!" + enabled for label, condition in labels))
    checks.require("calendar:selection-lifecycle", "SetProperty(Aura.Calendar.Day,week)" in actions(calendar, "onload") and
                   "ClearProperty(Aura.Calendar.Day)" in actions(calendar, "onunload"))
    checks.require("calendar:locale-dates", "ListItem.Premiered" in text(calendar) and "ListItem.Property(AirDay)" in text(calendar) and "ListItem.Property(AirTime)" in text(calendar))
    known_ids = {node.get("id") for node in calendar.iter("control") if node.get("id")}
    if any(node.text == "Topbar" for node in calendar.iter("include")):
        known_ids.add("300")  # Existing shared topbar menu; not a global include expansion.
    targets = []
    for node in calendar.iter():
        value = node.text or ""
        if node.tag in ("onleft", "onright", "onup", "ondown", "onback", "defaultcontrol", "menucontrol", "pagecontrol") and value.isdigit():
            targets.append(value)
        targets.extend(re.findall(r"(?:SetFocus|SendClick|Control\.Move)\((\d+)", value))
    checks.require("calendar:focus-targets", not set(targets) - known_ids, ", ".join(sorted(set(targets) - known_ids)))
    pvr_checks(checks, roots)


def provider_boundary_checks(checks, roots):
    """Scan all runtime XML, allowing presence checks only for installation.

    Named expression substitution and direct ancestor gates are source checks,
    not a generic include/condition evaluator. Paths and actions must be enabled;
    !HasAddon remains correct for a matching InstallAddon action.
    """
    expressions = {n.get("name"): n.text or "" for root in roots.values() for n in root.findall("expression")}
    def expand(value, stack=()):
        return re.sub(r"\$EXP\[([^]]+)\]", lambda m: "" if m[1] in stack else
                      expand(expressions.get(m[1], ""), stack + (m[1],)), value)
    presence, invocations = [], []
    for name, root in roots.items():
        parents = {child: parent for parent in root.iter() for child in parent}
        for node in root.iter():
            fields = [node.text or "", *node.attrib.values()]
            for addon in ENABLED_HELPERS:
                has_addon = "System.HasAddon(%s)" % addon
                if any(has_addon.lower() in value.lower() for value in fields):
                    installer = ((node.text or "").lower() == "installaddon(%s)" % addon and
                                 node.attrib == {"condition": "!" + has_addon})
                    if not installer:
                        presence.append(name + ":" + node.tag + ":" + addon)
                value = node.get("value", "") if node.tag == "param" else node.text or ""
                invokes = re.search(r"(?:RunScript|RunAddon|Addon.OpenSettings)\(\s*" + re.escape(addon) + r"(?:[,\)])", value, re.I)
                invokes = invokes or value.startswith("plugin://" + addon + "/") or (
                    node.tag in {"onclick", "onload", "onfocus", "onunload", "action"} and
                    "plugin://" + addon + "/" in value)
                if not invokes:
                    continue
                context, ancestor = "", node
                while ancestor is not None:
                    context += " " + ancestor.get("condition", "")
                    context += " " + " ".join(n.text or "" for tag in ("visible", "enable") for n in ancestor.findall(tag))
                    if ancestor.tag == "include" and ancestor.get("name") == "Object_AlphabetStrip":
                        # This known include is instantiated conditionally. Check
                        # every authored call site before borrowing its gate;
                        # no general include expansion or condition evaluation.
                        callers = [n for other in roots.values() for n in other.iter("include") if
                                   (n.text or "").strip() == "Object_AlphabetStrip" or n.get("content") == "Object_AlphabetStrip"]
                        gate = "System.AddonIsEnabled(%s)" % addon
                        if callers and all(re.search(r"(?<!!)" + re.escape(gate), expand(n.get("condition", ""))) for n in callers):
                            context += " " + gate
                    ancestor = parents.get(ancestor)
                if not re.search(r"(?<!!)System.AddonIsEnabled\(" + re.escape(addon) + r"\)", expand(context), re.I):
                    invocations.append(name + ":" + node.tag + ":" + addon)
    checks.require("providers:reviewed-enabled-boundaries", not presence, "; ".join(sorted(set(presence))))
    checks.require("providers:all-authored-invocations-enabled", not invocations, "; ".join(sorted(set(invocations))))


def actor_checks(checks, roots, original_xml):
    """Literal native actor browsers are manual selection, not filmography lookup.

    Exact tagged-core URL shapes and reviewed Stage 7A SIS contracts only; no
    asynchronous helper execution or arbitrary builtin/condition evaluation.
    """
    root = roots.get("1080i/Includes_Object.xml", ET.Element("missing"))
    dialog = roots.get("1080i/DialogVideoInfo.xml", ET.Element("missing"))
    expressions = {node.get("name"): node.text for node in root.findall("expression")}
    launch = root.find("include[@name='Object_Aura_Actor_OnClick']")
    actions = launch.findall("onclick") if launch is not None else []
    online = "Skin.HasSetting(Aura.OnlineEnrichment) + $EXP[Aura.PersonAction]"
    checks.require("actor:online-sis-dispatch", expressions.get("Aura.ActorOnline") == online and len(actions) == 4 and
                   actions[0].text == "SendClick(9551)" and actions[0].get("condition") == "$EXP[Aura.ActorOnline]")
    identity_gates = {
        "Aura.PersonDiscovery": "String.IsEqual(Window.Property(Aura.Info.Category),Aura Online Discovery) | String.IsEqual(Window.Property(Aura.Info.Category),Aura Online Discovery TV)",
        "Aura.PersonTitleType": "String.IsEqual(Window.Property(Aura.Info.DBType),movie) | String.IsEqual(Window.Property(Aura.Info.DBType),tvshow)",
        "Aura.PersonLibraryType": "$EXP[Aura.PersonTitleType] | String.IsEqual(Window.Property(Aura.Info.DBType),episode)",
        "Aura.PersonTitleID": "Integer.IsGreater(Window.Property(Aura.Info.TMDB),0) | String.StartsWith(Window.Property(Aura.Info.IMDB),tt)",
        "Aura.PersonExact": "Control.IsVisible(9550) + Integer.IsGreater(Container(9550).NumItems,0) + !Container(9550).IsUpdating + Integer.IsGreater(Container(9550).ListItem.Property(person_id),0)",
        "Aura.PersonContext": "Integer.IsGreater(Window.Property(Aura.Info.DBID),0) + $EXP[Aura.PersonLibraryType] + [String.IsEqual(Window.Property(Aura.Info.DBType),episode) | $EXP[Aura.PersonTitleID]]",
        "Aura.PersonNativeCard": "Control.IsVisible(50) + Integer.IsGreater(Container(50).NumItems,0) + !Container(50).IsUpdating + !String.IsEmpty(Container(50).ListItem.Label)",
        "Aura.PersonFallbackCard": "Control.IsVisible(9550) + Integer.IsGreater(Container(9550).NumItems,0) + !Container(9550).IsUpdating + !String.IsEmpty(Container(9550).ListItem.Label)",
        "Aura.PersonAction": "System.AddonIsEnabled(script.skin.info.service) + !Skin.HasSetting(VideoInfo.CastList) + [[$EXP[Aura.PersonDiscovery] + $EXP[Aura.PersonTitleType] + Integer.IsGreater(Window.Property(Aura.Info.TMDB),0)] | [!$EXP[Aura.PersonDiscovery] + $EXP[Aura.PersonLibraryType] + [$EXP[Aura.PersonExact] | [$EXP[Aura.PersonContext] + [$EXP[Aura.PersonNativeCard] | $EXP[Aura.PersonFallbackCard]]]]]]",
    }
    checks.require("actor:sis-identity-gates", all(expressions.get(k) == v for k, v in identity_gates.items()),
                   "Positive typed subject IDs; settled selected cast; exact fallback person before credit matching; no global guesses")
    secondary = control(dialog, 9551, "button")
    routes = secondary.findall("onclick") if secondary is not None else []
    prefix = "$EXP[Aura.PersonAction] + !$EXP[Aura.PersonDiscovery] + "
    expected_routes = [
        ("$EXP[Aura.PersonAction] + $EXP[Aura.PersonDiscovery]",
         "RunScript(script.skin.info.service,action=dialog_video_info,dbtype=$INFO[Window.Property(Aura.Info.DBType)],tmdb_id=$INFO[Window.Property(Aura.Info.TMDB)],focus=9551)"),
        (prefix + "$EXP[Aura.PersonExact]",
         "RunScript(script.skin.info.service,action=dialog_actor_info,person_id=$INFO[Container(9550).ListItem.Property(person_id)],name=$ESCINFO[Container(9550).ListItem.Label],auto_search=false,separator=,focus=9550)"),
        (prefix + "!$EXP[Aura.PersonExact] + $EXP[Aura.PersonContext] + $EXP[Aura.PersonNativeCard]",
         "RunScript(script.skin.info.service,action=dialog_actor_info,dbid=$INFO[Window.Property(Aura.Info.DBID)],dbtype=$INFO[Window.Property(Aura.Info.DBType)],name=$ESCINFO[Container(50).ListItem.Label],role=$ESCINFO[Container(50).ListItem.Label2],auto_search=false,separator=,focus=50)"),
        (prefix + "!$EXP[Aura.PersonExact] + $EXP[Aura.PersonContext] + !$EXP[Aura.PersonNativeCard] + $EXP[Aura.PersonFallbackCard]",
         "RunScript(script.skin.info.service,action=dialog_actor_info,dbid=$INFO[Window.Property(Aura.Info.DBID)],dbtype=$INFO[Window.Property(Aura.Info.DBType)],name=$ESCINFO[Container(9550).ListItem.Label],role=$ESCINFO[Container(9550).ListItem.Label2],auto_search=false,separator=,focus=9550)"),
    ]
    checks.require("actor:sis-typed-dialog-routes", [(n.get("condition"), n.text) for n in routes] == expected_routes and
                   secondary.findtext("visible") == "$EXP[Aura.PersonAction]",
                   "Captured typed title/episode identity, ESCINFO name/role, auto_search=false, single-name separator and originating focus")
    tv = "[String.IsEqual(Window.Property(Aura.Info.DBType),tvshow) | String.IsEqual(Window.Property(Aura.Info.DBType),season) | String.IsEqual(Window.Property(Aura.Info.DBType),episode)]"
    expected = [("Dialog.Close(movieinformation)", "!$EXP[Aura.ActorOnline]"),
                ("ActivateWindow(Videos,videodb://tvshows/actors/,return)", "!$EXP[Aura.ActorOnline] + " + tv),
                ("ActivateWindow(Videos,videodb://movies/actors/,return)", "!$EXP[Aura.ActorOnline] + !" + tv)]
    checks.require("actor:offline-literal-native-browsers", len(actions) == 4 and
                   [(n.text, n.get("condition")) for n in actions[1:]] == expected,
                   "Conditions use the pre-close subject type; actor names are never interpolated into either literal URL")
    stale = [name for name, other in roots.items() if re.search(
        r"Aura\.Actor\.(?:Encoding|Encoded|Choose|Name|CanEncode|EncodedReady)|Object_Aura_Actor_Workflow", ET.tostring(other, encoding="unicode")) or
        any(n.get("id") in {"7981", "7982", "7983"} for n in other.iter("control"))]
    checks.require("actor:no-async-lock-or-confirmation-panel", not stale, ", ".join(stale))
    cast = dialog.findall(".//include[@content='Object_VideoInfo_CastList']/param[@name='id'][@value='9550']")
    wired = root.find("include[@name='Object_VideoInfo_CastList']//include[.='Object_Aura_Actor_OnClick']")
    parents = {child: parent for parent in dialog.iter() for child in parent}
    call = parents.get(cast[0]) if len(cast) == 1 else None
    checks.require("actor:fallback9550-wired", wired is not None and wired.get("condition") == "$PARAM[actoronclick]" and
                   call is not None and call.find("param[@name='actoronclick'][@value='true']") is not None and
                   call.find("param[@name='content'][@value='$VAR[Aura_InfoCast]']") is not None)
    native = copy.deepcopy(control(dialog, 50, "list"))
    original = copy.deepcopy(control(original_xml("1080i/DialogVideoInfo.xml"), 50, "list"))
    for item in (native, original):
        if item is not None:
            for visible in item.findall("visible"):
                item.remove(visible)
    # Permit only the approved secondary-action Down link, not arbitrary edits
    # to native cards, includes, orientation or core Select semantics.
    native_down = native.find("ondown") if native is not None else None
    approved_down = native_down is not None and native_down.text == "SetFocus($VAR[Aura_PersonDown])"
    if approved_down:
        native_down.text = "9501"
    checks.require("actor:native-cast50-core-selection", native is not None and original is not None and
                   approved_down and signature(native) == signature(original),
                   "Only visibility and the exact Stage 7A Down link excluded from the native cast-list baseline comparison")
    down = root.find("variable[@name='Aura_PersonDown']")
    checks.require("actor:cast-return-focus", down is not None and
                   [(n.get("condition"), n.text) for n in down.findall("value")] ==
                   [("Control.IsVisible(9551)", "9551"), (None, "9501")] and secondary is not None and
                   all([(n.get("condition"), n.text) for n in secondary.findall(event)] == [
                       ("Control.IsVisible(50)", "50"),
                       ("!Control.IsVisible(50) + Control.IsVisible(9550)", "9550"),
                       ("!Control.IsVisible(50) + !Control.IsVisible(9550)", "9570")]
                       for event in ("onup", "onback")))
    button = control(dialog, 9958, "button")
    direct = button.findall("onclick") if button is not None else []
    direct_gate = "$EXP[Aura.ActorOnline]"
    checks.require("actor:container50-online-sis-dispatch", len(direct) == 1 and direct[0].text == "SendClick(9551)" and
                   direct[0].get("condition") == direct_gate and
                   button.findtext("visible") == direct_gate)
    hints = [n for n in dialog.iter("control") if n.findtext("label") == "$LOCALIZE[31907]"]
    checks.require("actor:manual-browser-help", len(hints) == 1 and all(token in hints[0].findtext("visible", "") for token in (
        "Control.IsVisible(9550)", "Integer.IsEqual(Container(50).NumItems,0)", "!Container(50).IsUpdating", "!$EXP[Aura.ActorOnline]")))


def pvr_checks(checks, roots):
    """Substitute only the PVR file's local includes/params; conditions stay opaque."""
    pvr = roots.get("1080i/Includes_PVR_Omega.xml", ET.Element("missing"))
    definitions = {node.get("name"): node for node in pvr.findall("include") if node.get("name")}

    def expand(node, params=None, stack=()):
        node = copy.deepcopy(node)
        for child in node.iter():
            for key, value in (params or {}).items():
                if child.text:
                    child.text = child.text.replace("$PARAM[" + key + "]", value)
                child.attrib = {k: v.replace("$PARAM[" + key + "]", value) for k, v in child.attrib.items()}
        children = []
        for child in node:
            key = child.get("content") or (child.text or "").strip()
            if child.tag == "include" and key in definitions:
                if key in stack:
                    raise ValueError("Recursive PVR include: " + key)
                definition = definitions[key]
                values = {n.get("name"): n.get("default", "") for n in definition.findall("param")}
                values.update({n.get("name"): n.get("value", "") for n in child.findall("param")})
                body = definition.find("definition")
                body = definition if body is None else body
                children.extend(expand(body, values, stack + (key,)))
            else:
                children.append(expand(child, params, stack))
        node[:] = children
        return node

    includes = roots.get("1080i/Includes.xml", ET.Element("missing"))
    checks.require("pvr:include-registered", len(includes.findall("include[@file='Includes_PVR_Omega.xml']")) == 1)
    for name, kind in (("MyPVRGuide", "epggrid"), ("MyPVRChannels", "list")):
        root = expand(roots.get("1080i/" + name + ".xml", ET.Element("missing")))
        checks.require("pvr:view50:" + name, root.findtext("views") == root.findtext("defaultcontrol") == "50" and control(root, 50, kind) is not None)
        group = control(root, 28, "button")
        checks.require("pvr:core-group28:" + name, group is not None and not group.findall("onclick"))
        checks.require("pvr:scrollbar60:" + name, control(root, 60, "scrollbar") is not None)
        if kind == "epggrid":
            grid = control(root, 50, kind)
            checks.require("pvr:grid800", grid is not None and grid.findtext("height") == "800" and not grid.findall("onclick"))
        for number, action in ((9311, "Info"), (9312, "ContextMenu")):
            button = control(root, number, "button")
            checks.require("pvr:native-%s:%s" % (action, name), button is not None and
                           [n.text for n in button.findall("onclick")] == ["SetFocus(50)", "Action(%s)" % action])
    summary = pvr.find("include[@name='PVR_Omega_Summary']")
    summary_text = ET.tostring(summary, encoding="unicode") if summary is not None else ""
    variables = " ".join(ET.tostring(n, encoding="unicode") for n in pvr.findall("variable"))
    checks.require("pvr:summary-native-event", "ListItem.Plot" in summary_text and "ListItem.EpgEventTitle" in variables and
                   "ListItem.EpgEventIcon" in variables and "Container(50).ListItem" not in summary_text + variables)
    checks.require("pvr:native-art-fallback", "ListItem.Icon" in variables and "fallback=" in summary_text)
    dialog = roots.get("1080i/DialogPVRInfo.xml", ET.Element("missing"))
    checks.require("pvr:dialog-native-buttons", all(control(dialog, n, "button") is not None and
                   not control(dialog, n, "button").findall("onclick") for n in range(4, 12)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true", help="Read starting-commit bytes with git show; failures remain failures")
    parser.add_argument("--report", type=Path, help="New JSON report outside the source/package; parent must exist")
    parser.add_argument("--index", type=Path, help="Existing decompressed official Omega addons.xml for recursive closure; no download")
    args = parser.parse_args(argv)
    try:
        report_path = None
        if args.report is not None:
            report_path = args.report.absolute()
            if report_path.is_symlink() or report_path.exists():
                raise ValueError("Report must be a new file")
            if report_path.resolve().is_relative_to(ROOT) or not report_path.parent.is_dir():
                raise ValueError("Report must be outside the package with an existing parent")
        report = check_source(Source(ROOT, baseline=args.baseline), args.index.read_bytes() if args.index else None)
        report["official_index_file"] = str(args.index.resolve()) if args.index else None
        report["exit_code"] = 1 if report["failures"] else 0
        passed = len(report["checks"]) - report["failures"]
        print("Omega static %s: %s" % (report["source"], "FAIL" if report["failures"] else "PASS"))
        print("Parsed inventory: {xml} XML, {xsp} XSP; {python_expressions} Python expressions (AST only)".format(**report["counts"]))
        print("Seek conditions: %d exact Player.HasPerformedSeek(3); expected=7 with per-file counts 2/4/1" % report["counts"]["seek_expressions"])
        print("Checks: %d passed, %d failed, %d warnings; exit=%d" % (
            passed, report["failures"], len(report["warnings"]), report["exit_code"]))
        for result in report["checks"]:
            if not result["passed"]:
                print("FAIL %s%s" % (result["check"], ": " + result["detail"] if result["detail"] else ""))
        for warning in report["warnings"]:
            print("WARNING: " + warning)
        if report_path:
            with report_path.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, sort_keys=True)
                stream.write("\n")
            print("Report: " + str(report_path))
        return report["exit_code"]
    except (OSError, ValueError, ET.ParseError) as error:
        print("ERROR: %s; exit=2" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
