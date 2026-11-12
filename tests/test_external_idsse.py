"""Independent synthetic checks for the external Sportec adapter and scoring."""
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from model.external_idsse import load_match, score_labels, merge_scores
from model.temporal import load_config
from model.inference import infer


def fixture(folder):
    metadata = folder / 'metadata.xml'
    metadata.write_text('''<Root><General MatchId="test" HomeTeamId="home"
        GuestTeamId="away" HomeTeamName="Home" GuestTeamName="Away"
        KickoffTime="2023-01-01T12:00:00+00:00"/>
        <Environment PitchX="100" PitchY="60"/>
        <Teams><Team TeamId="home"><Player PersonId="h"/></Team>
        <Team TeamId="away"><Player PersonId="a"/></Team></Teams></Root>''')
    root = ET.Element('Positions')
    for period, start, minute in [('firstHalf', 100, '00'), ('secondHalf', 1000, '10')]:
        for team, player, x in [('away', 'a', '10'), ('home', 'h', '1'), ('BALL', 'ball', '0')]:
            group = ET.SubElement(root, 'FrameSet', GameSection=period,
                                  MatchId='test', TeamId=team, PersonId=player)
            for delta in range(3):
                ET.SubElement(group, 'Frame', N=str(start + delta), X=x, Y='0',
                              T='2023-01-01T12:{}:00.{:03d}+00:00'.format(minute, delta * 40),
                              **({'BallStatus': '1', 'BallPossession': '2'} if team == 'BALL' else {}))
    tracking = folder / 'tracking.xml'
    ET.ElementTree(root).write(tracking)
    return metadata, tracking, root


class IDSSETests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.metadata, self.tracking, self.root = fixture(Path(self.temp.name))
        self.config = load_config('model/config_v4.json')

    def save(self):
        ET.ElementTree(self.root).write(self.tracking)

    def test_raw_offsets_team_mapping_and_metres(self):
        match = load_match(self.metadata, self.tracking, self.config)
        self.assertEqual(match['blocks'], [(1, 0, 2), (2, 3, 5)])
        self.assertEqual(match['reference'], ['A'] * 6)
        self.assertEqual(match['evidence'][0]['nearest_distance_m'], {'H': 1.0, 'A': 10.0})
        self.assertEqual(match['evidence'][0]['candidate'], 'H')

    def test_reference_changes_cannot_change_inference(self):
        first = load_match(self.metadata, self.tracking, self.config)
        for row in self.root.findall(".//Frame[@BallStatus]"):
            row.set('BallStatus', '0'); row.set('BallPossession', '1')
        self.save()
        second = load_match(self.metadata, self.tracking, self.config)
        self.assertEqual(second['reference'], ['D'] * 6)
        self.assertEqual(first['evidence'], second['evidence'])
        self.assertEqual(infer(first['evidence'], first['blocks'], self.config),
                         infer(second['evidence'], second['blocks'], self.config))

    def test_missing_ball_and_all_missing_frame_do_not_collapse_time(self):
        for group in self.root.findall('FrameSet'):
            if group.get('GameSection') == 'firstHalf':
                group.remove(list(group)[1])
        self.save()
        match = load_match(self.metadata, self.tracking, self.config)
        self.assertEqual(len(match['evidence']), 6)
        self.assertIsNone(match['reference'][1])
        row = match['evidence'][1]
        self.assertFalse(row['ball_seen']); self.assertFalse(row['outside'])
        self.assertEqual(row['players_seen'], 0); self.assertIsNone(row['candidate'])

    def test_missing_players_cannot_establish_control(self):
        for group in list(self.root):
            if group.get('TeamId') != 'BALL':
                self.root.remove(group)
        self.save()
        match = load_match(self.metadata, self.tracking, self.config)
        labels, _ = infer(match['evidence'], match['blocks'], self.config)
        self.assertEqual(labels, ['X'] * 6)

    def test_duplicate_frame_rejected(self):
        self.root.find('FrameSet')[1].set('N', '100')
        self.save()
        with self.assertRaises(ValueError):
            load_match(self.metadata, self.tracking, self.config)

    def test_timestamp_misalignment_rejected(self):
        self.root.find('FrameSet')[1].set('T', '2023-01-01T12:00:00.080+00:00')
        self.save()
        with self.assertRaises(ValueError):
            load_match(self.metadata, self.tracking, self.config)

    def test_unknown_team_and_match_rejected(self):
        for field, value in [('TeamId', 'unknown'), ('MatchId', 'other')]:
            with self.subTest(field=field):
                self.metadata, self.tracking, self.root = fixture(Path(self.temp.name))
                self.root.find('FrameSet').set(field, value)
                self.save()
                with self.assertRaises(ValueError):
                    load_match(self.metadata, self.tracking, self.config)

    def test_no_team_for_live_unknown_reference(self):
        row = self.root.find(".//Frame[@BallStatus]")
        row.set('BallPossession', '0')
        self.save()
        self.assertIsNone(load_match(self.metadata, self.tracking, self.config)['reference'][0])

    def test_scores_include_abstention_and_dead_ball_errors(self):
        score = score_labels(['H', 'A', 'X', 'D', 'A'], ['H', 'H', 'A', 'D', None])
        self.assertEqual((score['correct'], score['eligible'], score['unknown']), (2, 4, 1))
        self.assertEqual(score['accuracy'], 0.5)
        self.assertAlmostEqual(score['macro_f1'], 5/9)
        self.assertAlmostEqual(score['live_accuracy'], 1/3)
        self.assertEqual(score['prediction_coverage'], 0.75)
        merged = merge_scores([score, score_labels(['H'], ['H'])])
        self.assertEqual(merged['accuracy'], 3/5)

    def test_score_rejects_invalid_dimensions_and_labels(self):
        for prediction, reference in [(['H'], []), (['Q'], ['H']), (['H'], ['X']),
                                      ([''], ['H']), (['HA'], ['H']), ([None], ['H'])]:
            with self.assertRaises(ValueError):
                score_labels(prediction, reference)


if __name__ == '__main__':
    unittest.main()
