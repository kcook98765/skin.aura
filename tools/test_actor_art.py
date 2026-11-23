"""Focused XML binding regression; synthetic artwork labels, not Kodi rendering.

Run: python -B -m unittest discover -s tools -p 'test_actor_art.py' -v
Only resolves the two cast-layout include layers and Image_Poster's small
expression subset. No Kodi imports, network, image-cache or provider execution.
"""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
FILES = ("DialogVideoInfo.xml", "script-script.extendedinfo-DialogVideoInfo.xml",
         "script-script.extendedinfo-DialogInfo.xml")
CAST_CALLERS = {("DialogVideoInfo.xml", "9550"),
                ("script-script.extendedinfo-DialogVideoInfo.xml", "1000")}


def parameters(node, attribute):
    # Kodi21.3 GUIIncludes.cpp:538-574: first duplicate wins, no overwrites.
    result = {}
    for child in node.findall("param"):
        result.setdefault(child.get("name"), child.get(attribute, ""))
    return result


def substitute(text, values):
    return re.sub(r"\$PARAM\[([^]]+)\]", lambda m: values[m[1]], text)


class CastBindings:
    def __init__(self):
        self.roots = {name: ET.parse(ROOT / "1080i" / name).getroot() for name in FILES}
        self.layout = ET.parse(ROOT / "1080i/Includes_View.xml").find("include[@name='View_Actor_Layout']")
        self.wrapper = ET.parse(ROOT / "1080i/Includes_Object.xml").find("include[@name='Object_VideoInfo_CastList']")
        self.poster = ET.parse(ROOT / "1080i/Includes_Images.xml").find("variable[@name='Image_Poster']")

    def wrapped_calls(self):
        for name, root in self.roots.items():
            for call in root.findall(".//include[@content='Object_VideoInfo_CastList']"):
                yield (name, parameters(call, "value")["id"]), call

    def native_call(self):
        return self.roots[FILES[0]].find(".//control[@id='50']/include[@content='View_Actor_Layout']")

    def texture(self, call, focused):
        values = parameters(call, "value")
        if call.get("content") == "Object_VideoInfo_CastList":
            values = {**parameters(self.wrapper, "default"), **values}
            nested = self.wrapper.find(".//include[@content='View_Actor_Layout']")
            values = {key: substitute(value, values) for key, value in parameters(nested, "value").items()}
        values = {**parameters(self.layout, "default"), **values}
        kind = "focusedlayout" if focused else "itemlayout"
        episode = values["episodelayout"] == "true"
        controls = self.layout.findall("definition/%s/control/control" % kind)
        control = next(n for n in controls if n.findtext("visible") ==
                       ("$PARAM[episodelayout]" if episode and not focused else
                        "!$PARAM[textonly]" if episode else "!$PARAM[episodelayout]")
                       and n.find("texture") is not None
                       and (not episode or n.findtext("texture") == "$INFO[ListItem.Art(thumb)]"))
        texture = control.find("texture")
        return substitute(texture.text, values), substitute(texture.get("fallback"), values)

    def image(self, call, focused, labels, content="episodes"):
        labels = {key.lower(): value for key, value in labels.items()}

        def info(name):
            return labels.get(name.lower(), "")

        def condition(text):
            if " | " in text:
                return any(condition(part) for part in text.split(" | "))
            if " + " in text:
                return all(condition(part) for part in text.split(" + "))
            if text.startswith("!"):
                return not condition(text[1:])
            if text.startswith("Skin.HasSetting("):
                return False  # animated posters off in these explicit fixtures
            if text == "Window.IsActive(movieinformation)":
                return True
            match = re.fullmatch(r"Container.Content\(([^)]+)\)", text)
            if match:
                return content == match[1]
            match = re.fullmatch(r"String.IsEmpty\((.+)\)", text)
            if match:
                return not info(match[1])
            match = re.fullmatch(r"String.(IsEqual|EndsWith)\((.+),([^,]+)\)", text)
            if match:
                left, right = info(match[2]).lower(), match[3].lower()
                return left == right if match[1] == "IsEqual" else left.endswith(right)
            raise AssertionError("Unsupported fixture condition: " + text)

        def evaluate(text):
            if text == "$VAR[Image_Poster]":
                node = next(n for n in self.poster if n.get("condition") is None or condition(n.get("condition")))
                return evaluate(node.text)
            match = re.fullmatch(r"\$INFO\[(.+)\]", text)
            if match:
                return info(match[1])
            raise AssertionError("Unsupported fixture texture: " + text)

        texture, fallback = self.texture(call, focused)
        return evaluate(texture) or fallback


class ActorArtTests(unittest.TestCase):
    def setUp(self):
        self.bindings = CastBindings()

    def actor_calls(self):
        return [((FILES[0], "50"), self.bindings.native_call()),
                *[(key, call) for key, call in self.bindings.wrapped_calls() if key in CAST_CALLERS]]

    def test_cast_portraits_ignore_episode_season_and_show_container_art(self):
        self.assertEqual(len(self.actor_calls()), 3)
        for key, call in self.actor_calls():
            for focused in (False, True):
                for content in ("episodes", "seasons", "videos"):
                    for art in ("poster", "season.poster", "tvshow.poster"):
                        for portrait in ("actor-one.jpg", "actor-two.jpg"):
                            labels = {"ListItem.Icon": portrait, "Container.Art(%s)" % art: "season.jpg"}
                            self.assertEqual(self.bindings.image(call, focused, labels, content), portrait,
                                             (key, focused, content, art, portrait))

    def test_missing_headshot_keeps_actor_placeholder_not_season_art(self):
        for key, call in self.actor_calls():
            for focused in (False, True):
                # Native/SIS contract emits DefaultActor.png when headshot absent.
                labels = {"ListItem.Icon": "DefaultActor.png", "Container.Art(poster)": "season.jpg"}
                self.assertEqual(self.bindings.image(call, focused, labels), "DefaultActor.png", key)
                if key in CAST_CALLERS:
                    labels["ListItem.Icon"] = ""
                    self.assertEqual(self.bindings.image(call, focused, labels), "DefaultActor.png", key)

    def test_actual_generic_wrapper_callers_keep_poster_and_episode_bindings(self):
        generic = [(key, call) for key, call in self.bindings.wrapped_calls() if key not in CAST_CALLERS]
        self.assertGreaterEqual(len(generic), 10)  # includes Similar, NextUp, extras and legacy media/crew
        for key, call in generic:
            episode = parameters(call, "value").get("episodelayout") == "true"
            for focused in (False, True):
                with self.subTest(caller=key, focused=focused):
                    labels = {"ListItem.Icon": "icon.jpg", "ListItem.Art(poster)": "media.jpg",
                              "ListItem.Art(thumb)": "episode.jpg", "Container.Art(poster)": "season.jpg"}
                    self.assertEqual(self.bindings.image(call, focused, labels), "episode.jpg" if episode else "media.jpg")
                    del labels["ListItem.Art(poster)"]
                    self.assertEqual(self.bindings.image(call, focused, labels), "episode.jpg" if episode else "season.jpg")

    def test_generic_extras_keep_their_configured_missing_image_fallback(self):
        for key, call in self.bindings.wrapped_calls():
            if key == (FILES[0], "9505"):
                for focused in (False, True):
                    self.assertEqual(self.bindings.image(call, focused, {}, "videos"), "common/playring.png")

    def test_negative_control_reintroduced_general_poster_selects_season(self):
        for kind in ("itemlayout", "focusedlayout"):
            texture = self.bindings.layout.find("definition/%s/control/control/texture" % kind)
            texture.text = "$VAR[Image_Poster]"
        labels = {"ListItem.Icon": "actor.jpg", "Container.Art(poster)": "season.jpg"}
        for focused in (False, True):
            self.assertEqual(self.bindings.image(self.bindings.native_call(), focused, labels), "season.jpg")


if __name__ == "__main__":
    unittest.main()
