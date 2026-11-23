"""Repair A source semantics, not native Kodi rendering.

Run: python3 -B -m unittest discover -s tools -p test_pvr_player_metadata.py -v
Only the two known row predicates and the three OSD branches are modelled;
unexpected expressions fail closed. No Kodi modules or expression engine.
"""

from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
# One level of bracketed formatting/localization inside an INFO prefix/suffix.
INFO = re.compile(r"\$INFO\[([\w.]+)(?:,((?:\[[^\[\]]*\]|[^\[\]])*?),"
                  r"((?:\[[^\[\]]*\]|[^\[\]])*?))?\]")


def text(template, metadata):
    def expand(match):
        value = metadata.get(match[1], "")
        return (match[2] or "") + value + (match[3] or "") if value else ""
    result = INFO.sub(expand, template)
    assert "$INFO[" not in result, "Unmodelled INFO syntax: " + result
    return result


def summary_rows(node, metadata):
    rows = []
    for row in node.findall("./control[@type='label']")[:2]:
        predicate = row.findtext("visible")
        match = re.fullmatch(
            r"\[!String.IsEmpty\(ListItem.Title\) \| !String.IsEmpty\((ListItem.\w+)\)\]"
            r" \+ (!?)String.IsEmpty\(ListItem.Season\)", predicate)
        assert match, "Unmodelled summary predicate: " + predicate
        has_heading = bool(metadata.get("ListItem.Title") or metadata.get(match[1]))
        season_matches = bool(metadata.get("ListItem.Season")) == bool(match[2])
        if has_heading and season_matches:
            rows.append(text(row.findtext("label"), metadata))
    return rows


def osd_line(values, metadata, livetv):
    assert len(values) == 3
    match = re.fullmatch(
        r"\[!String.IsEmpty\(([\w.]+)\) \| !String.IsEmpty\(VideoPlayer.EpisodeName\)\]"
        r" \+ VideoPlayer.Content\(livetv\)", values[0].get("condition"))
    assert match, "Unmodelled live-TV predicate"
    assert values[1].get("condition") == (
        "!String.IsEmpty(VideoPlayer.Season) + !String.IsEmpty(VideoPlayer.Episode)")
    assert values[2].get("condition") is None
    if livetv and (metadata.get(match[1]) or metadata.get("VideoPlayer.EpisodeName")):
        branch = 0
    elif metadata.get("VideoPlayer.Season") and metadata.get("VideoPlayer.Episode"):
        branch = 1
    else:
        branch = 2
    return branch, text(values[branch].text, metadata)


class PVRPlayerMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = ET.parse(ROOT / "1080i/Includes_Object.xml").find(
            "./include[@name='Object_PVR_Info_Content']")
        cls.osd = ET.parse(ROOT / "1080i/Includes_Labels.xml").findall(
            "./variable[@name='Label_OSD_InfoLine']/value")
        cls.guide = ET.parse(ROOT / "1080i/Includes_PVR_Omega.xml").findall(
            "./variable[@name='PVR_Omega_SummaryTitle']/value")

    def test_summary_bindings_and_formatting(self):
        rows = self.summary.findall("./control[@type='label']")[:2]
        serialized = "".join(ET.tostring(row, encoding="unicode") for row in rows)
        self.assertEqual(serialized.count("ListItem.ChannelNumberLabel"), 4)
        self.assertNotRegex(serialized, r"ListItem\.ChannelNumber\b")
        for season in ("", "2"):
            with self.subTest(season=season):
                metadata = {"ListItem.Title": "Programme", "ListItem.Year": "2026",
                            "ListItem.ChannelNumberLabel": "7.2", "ListItem.ChannelName": "Station",
                            "ListItem.Season": season, "ListItem.Episode": "3"}
                prefix = "S2E3" if season else "2026"
                self.assertEqual(summary_rows(self.summary, metadata), [prefix +
                    "  |  [COLOR=main_fg_100]7.2. [/COLOR][COLOR=main_fg_100]Station[/COLOR]"])

    def test_channel_present_title_absent_both_season_rows(self):
        for season in ("", "2"):
            with self.subTest(season=season):
                metadata = {"ListItem.ChannelNumberLabel": "7.2", "ListItem.Season": season,
                            "ListItem.Episode": "3"}
                prefix = "S2E3" if season else ""
                self.assertEqual(summary_rows(self.summary, metadata), [prefix +
                    "  |  [COLOR=main_fg_100]7.2. [/COLOR]"])

    def test_empty_number_and_empty_metadata(self):
        self.assertEqual(summary_rows(self.summary, {}), [])
        self.assertEqual(summary_rows(self.summary, {"ListItem.Season": "2"}), [])
        for season in ("", "2"):
            with self.subTest(season=season):
                metadata = {"ListItem.Title": "Programme", "ListItem.Year": "2026",
                            "ListItem.Season": season, "ListItem.Episode": "3"}
                self.assertEqual(summary_rows(self.summary, metadata), ["S2E3" if season else "2026"])

    def test_summary_selected_title_and_label_fallback_unchanged(self):
        titles = self.summary.findall("./control[@type='group'][1]/control[@type='label']")
        self.assertEqual([n.findtext("visible") for n in titles], [
            "!String.IsEmpty(ListItem.EpgEventTitle)", "String.IsEmpty(ListItem.EpgEventTitle)"])
        self.assertEqual(text(titles[0].findtext("label"), {
            "ListItem.EpgEventTitle": "Future", "ListItem.EpisodeName": "Episode"}), "Future - Episode")
        self.assertEqual(text(titles[1].findtext("label"), {"ListItem.Label": "Recording"}), "Recording")
        self.assertEqual(text(titles[1].findtext("label"), {}), "")

    def test_current_epg_title_and_episode_availability(self):
        for title, episode in (("Now", ""), ("Now", "Episode"), ("", "Episode"), ("", "")):
            with self.subTest(title=title, episode=episode):
                metadata = {"Player.Title": title, "VideoPlayer.EpisodeName": episode}
                expected = "".join("  |  [COLOR=main_fg_100]" + value + "[/COLOR]"
                                   for value in (episode, title) if value)
                self.assertEqual(osd_line(self.osd, metadata, True),
                                 (0 if title or episode else 2, expected))

    def test_no_epg_and_non_livetv_fallbacks(self):
        metadata = {"Player.Title": "Movie", "VideoPlayer.TvShowTitle": "Show",
                    "VideoPlayer.Season": "2", "VideoPlayer.Episode": "3"}
        episode = "  |  [COLOR=main_fg_100]Show[/COLOR]  |  [COLOR=main_fg_100]S2[/COLOR][COLOR=main_fg_100]E3[/COLOR]"
        self.assertEqual(osd_line(self.osd, metadata, False), (1, episode))
        del metadata["Player.Title"]
        self.assertEqual(osd_line(self.osd, metadata, True), (1, episode))
        del metadata["VideoPlayer.Episode"]
        metadata.update({"VideoPlayer.Year": "2026", "VideoPlayer.MPAA": "PG", "VideoPlayer.Genre": "Drama"})
        self.assertEqual(osd_line(self.osd, metadata, True), (2,
            "  |  [COLOR=main_fg_100]Show[/COLOR]  |  [COLOR=main_fg_100]2026[/COLOR]"
            "  |  [COLOR=main_fg_100]PG[/COLOR]  |  [COLOR=main_fg_100]Drama[/COLOR]"))
        self.assertEqual(osd_line(self.osd, {}, True), (2, ""))

    def test_future_selection_is_not_playing_programme_negative_control(self):
        metadata = {"ListItem.EpgEventTitle": "Future selection", "Player.Title": "Playing now"}
        selected = self.guide[0]
        self.assertEqual(selected.get("condition"), "!String.IsEmpty(ListItem.EpgEventTitle)")
        self.assertEqual(selected.text, "$INFO[ListItem.EpgEventTitle]")
        self.assertEqual(text(selected.text, metadata), "Future selection")
        self.assertEqual(osd_line(self.osd, metadata, True),
                         (0, "  |  [COLOR=main_fg_100]Playing now[/COLOR]"))
        # Deliberately substitute the wrong context in memory; the oracle must reject it.
        wrong = text(selected.text.replace("ListItem.EpgEventTitle", "Player.Title"), metadata)
        with self.assertRaises(AssertionError):
            self.assertEqual(wrong, "Future selection")
        self.assertEqual(wrong, "Playing now")


if __name__ == "__main__":
    unittest.main()
