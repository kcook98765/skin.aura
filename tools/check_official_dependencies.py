#!/usr/bin/env python3
"""Offline dependency audit against an explicitly supplied Omega index.

No downloads, add-on imports, Python stubs, or installed-profile inspection.
Core provider versions/ABIs are pinned to Kodi 21.3 source manifests, not the
CPython version. This checks declarations, not installation or runtime behavior.
"""

import argparse
from functools import cmp_to_key
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

CORE_COMMIT = "a3a448d26b8d560a65655dab2cd122994dc4e146"
CORE_URL = "https://github.com/xbmc/xbmc/blob/" + CORE_COMMIT + "/addons/"
# id: (provider version, backwards-compatible ABI floor, required imports)
# PIL is a bundled Python module with no backwards-compatibility declaration;
# only the explicit API-provider ABI floors are asserted here.
CORE = {
    "xbmc.core": ("0.1.0", "0.1", ()),
    "xbmc.gui": ("5.17.0", "5.17.0", (("xbmc.core", "0.1.0"),)),
    "xbmc.python": ("3.0.1", "3.0.0", (("xbmc.core", "0.1.0"),)),
    "xbmc.json": ("13.5.0", "6.0.0", (("xbmc.core", "0.1.0"),)),
    "kodi.resource": ("1.0.0", "1.0", (("xbmc.core", "0.1.0"),)),
    "script.module.pil": ("5.1.0", None, (("xbmc.python", "3.0.0"),)),
    # Generated addon.xml.in manifests use these exact versions.h version/ABI
    # pairs at CORE_COMMIT. Reached by YouTube -> InputStream Adaptive.
    "kodi.binary.global.main": ("2.0.2", "2.0.0", (("xbmc.core", "0.1.0"),)),
    "kodi.binary.global.general": ("1.0.5", "1.0.4", (("xbmc.core", "0.1.0"),)),
    "kodi.binary.global.gui": ("5.15.0", "5.15.0", (("xbmc.core", "0.1.0"),)),
    "kodi.binary.global.filesystem": ("1.1.9", "1.1.7", (("xbmc.core", "0.1.0"),)),
    "kodi.binary.global.tools": ("1.0.4", "1.0.0", (("xbmc.core", "0.1.0"),)),
    "kodi.binary.instance.inputstream": ("3.3.0", "3.3.0", (("xbmc.core", "0.1.0"),)),
    "kodi.binary.instance.videocodec": ("2.1.0", "2.1.0", (("xbmc.core", "0.1.0"),)),
}


def compare_versions(left, right):
    """Bounded port of pinned xbmc/addons/AddonVersion.cpp CompareComponent.

    Unlike packaging.version, '+' is upstream text and '-' splits revision.
    Reject invalid syntax instead of Kodi's invalid-version fallback to 0.0.0.
    """
    def split(value):
        if not re.fullmatch(r"(?:\d+:)?[A-Za-z0-9.+_@~]+(?:-[A-Za-z0-9.+_@~]+)?", value):
            raise ValueError("Unsupported dependency version: " + repr(value))
        epoch, value = value.split(":", 1) if ":" in value else ("0", value)
        upstream, _, revision = value.lower().partition("-")
        return int(epoch), upstream, revision

    def component(a, b):
        while a and b:
            while a and b and not a[0].isdigit() and not b[0].isdigit():
                if a[0] != b[0]:
                    return -1 if a[0] == "~" else 1 if b[0] == "~" else (1 if a[0] > b[0] else -1)
                a, b = a[1:], b[1:]
            if a and b and (not a[0].isdigit() or not b[0].isdigit()):
                return -1 if a[0] == "~" else 1 if b[0] == "~" else (-1 if a[0].isdigit() else 1)
            na, nb = re.match(r"\d*", a)[0], re.match(r"\d*", b)[0]
            if int(na or 0) != int(nb or 0):
                return 1 if int(na or 0) > int(nb or 0) else -1
            a, b = a[len(na):], b[len(nb):]
        if a:
            return -1 if a[0] == "~" else 1
        if b:
            return 1 if b[0] == "~" else -1
        return 0

    a, b = split(left), split(right)
    return (1 if a[0] > b[0] else -1) if a[0] != b[0] else component(a[1], b[1]) or component(a[2], b[2])


version_key = cmp_to_key(compare_versions)


def dependency_closure(manifest, index_bytes):
    """Traverse required edges and available optional branches separately.

Choose the newest published version per ID (no fallback to older packages to
hide a broken newest graph). Platform-specific duplicates must have identical
declarations or are reported ambiguous. Missing optional providers are explicit
diagnostics; required descendants of published optional providers are audited.
"""
    index = ET.fromstring(index_bytes)
    if index.tag != "addons":
        raise ValueError("Expected an <addons> repository index")
    providers = {}
    for node in index.findall("addon"):
        addon, version = node.get("id"), node.get("version")
        if not addon or not version:
            raise ValueError("Index entry missing ID/version")
        providers.setdefault(addon, []).append(node)
    selected, visited, edges, failures, optional = {}, set(), [], [], []
    optional_required, optional_failures, optional_unavailable = [], [], []

    def visit(parent, requirement, via_optional=False):
        addon, minimum = requirement.get("addon", ""), requirement.get("version", "0.0.0")
        is_optional = requirement.get("optional", "false").lower() == "true"
        optional_branch = via_optional or is_optional
        edge = {"parent": parent, "addon": addon, "minimum": minimum}
        (optional if is_optional else optional_required if optional_branch else edges).append(edge)
        problems = optional_failures if optional_branch else failures
        requested = version_key(minimum)
        broken = []
        if addon in CORE:
            version, abi, dependencies = CORE[addon]
            node = ET.Element("addon", id=addon, version=version)
            requires = ET.SubElement(node, "requires")
            for child, floor in dependencies:
                ET.SubElement(requires, "import", addon=child, version=floor)
            edge.update(provider="Kodi 21.3 core", version=version, abi=abi)
            valid = requested <= version_key(version) and (abi is None or version_key(abi) <= requested)
        else:
            candidates = providers.get(addon, [])
            if not candidates:
                if is_optional:
                    edge["status"] = "unavailable"
                    optional_unavailable.append(dict(edge))
                else:
                    problems.append({**edge, "reason": "required provider missing"})
                return
            newest = max(version_key(n.get("version")) for n in candidates)
            candidates = [n for n in candidates if version_key(n.get("version")) == newest]
            declarations = {tuple(sorted(tuple(sorted(dep.attrib.items())) for dep in n.findall("./requires/import")))
                            for n in candidates}
            if len(declarations) != 1:
                problems.append({**edge, "reason": "ambiguous platform dependency declarations"})
                if optional_branch:
                    edge["status"] = "ambiguous"
                return
            node = candidates[0]
            version = node.get("version")
            edge.update(provider="supplied official index", version=version)
            valid = requested <= version_key(version)
            broken = [n.text for n in node.findall("./extension/broken") if n.text and n.text.strip()]
            if broken:
                problems.append({**edge, "reason": "provider marked broken: " + "; ".join(broken)})
        if not valid:
            problems.append({**edge, "reason": "required version/ABI unsatisfied"})
        if optional_branch:
            edge["status"] = "broken" if broken else "audited" if valid else "unsatisfied"
        selected[addon] = {key: value for key, value in edge.items() if key not in ("parent", "minimum")}
        marker = (addon, optional_branch)
        if marker in visited:
            return
        visited.add(marker)
        for child in node.findall("./requires/import"):
            visit(addon, child, optional_branch)

    for requirement in manifest.findall("./requires/import"):
        visit(manifest.get("id", "root"), requirement)
    return {
        "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
        "index_entries": len(index.findall("addon")), "core_commit": CORE_COMMIT,
        "core_evidence": {addon: CORE_URL + addon + "/addon.xml" + (".in" if addon == "xbmc.json" or addon.startswith("kodi.binary.") else "") for addon in CORE},
        "json_version_evidence": CORE_URL.replace("/addons/", "/xbmc/interfaces/json-rpc/schema/version.txt"),
        "binary_version_abi_evidence": CORE_URL.replace("/addons/", "/xbmc/addons/kodi-dev-kit/include/kodi/versions.h"),
        "providers": selected, "required_edges": edges, "optional_edges": optional,
        "optional_required_edges": optional_required, "optional_failures": optional_failures,
        "unavailable_optional_edges": optional_unavailable,
        "required_closure_complete": not failures,
        "published_optional_closure_complete": not optional_failures,
        "failures": failures,
        "warnings": [
            "Offline manifest closure only; supplied index provenance/freshness and Kodi runtime acceptance are separate.",
            "Optional audit: %d unavailable declared optional edges; %d failures in published optional branches. Required closure does not establish active source-provider coverage." % (len(optional_unavailable), len(optional_failures)),
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True, help="Existing decompressed official Omega addons.xml; never downloaded")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).resolve().parents[1] / "addon.xml")
    args = parser.parse_args(argv)
    try:
        report = dependency_closure(ET.parse(args.manifest).getroot(), args.index.read_bytes())
        report["index_file"] = str(args.index.resolve())
        report["manifest_file"] = str(args.manifest.resolve())
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1 if report["failures"] or report["optional_failures"] else 0
    except (OSError, ValueError, ET.ParseError) as error:
        print("ERROR: %s; exit=2" % error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
