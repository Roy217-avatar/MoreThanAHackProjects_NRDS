import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from model.external_wcsf import load_match
from model.temporal import load_config


FIELDS = ['', 'x', 'y', 'speed', 'acceleration', 'group_id', 'timestamp_ms',
          'AliveFlag', 'PossessionFlag', 'x_ball', 'y_ball',
          'team_game_phase', 'player_id']


def row(index, group, timestamp, alive, possession, player_x, ball_x='0'):
    return [index, player_x, '0', '0', '0', group, timestamp, alive, possession,
            ball_x, '0', '2', 1000 + index]


def archive(path, member, rows):
    text = io.StringIO()
    writer = csv.writer(text, lineterminator='\n')
    writer.writerow(FIELDS)
    writer.writerows(rows)
    with zipfile.ZipFile(path, 'w') as handle:
        handle.writestr(member, text.getvalue())


class ExternalWCSFTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.first = root / 'first.zip'
        self.second = root / 'second.zip'
        archive(self.first, 'positions_FIRST_HALF.csv', [
            row(0, 1, 0, 1, 1, '1'), row(1, 2, 0, 1, 1, '8'),
            row(2, 1, 100, 0, 1, '5'), row(3, 2, 100, 0, 1, '6'),
        ])
        archive(self.second, 'positions_SECOND_HALF.csv', [
            row(4, 1, 5000, 1, 2, '8'), row(5, 2, 5000, 1, 2, '1'),
        ])
        self.config = load_config('model/config_v7_stoppage.json')

    def test_maps_rows_to_ten_hz_evidence_references_and_half_blocks(self):
        match = load_match([self.first, self.second], self.config)
        self.assertEqual(match['blocks'], [(1, 0, 1), (2, 2, 2)])
        self.assertEqual(match['reference'], ['H', 'D', 'A'])
        self.assertEqual([item['candidate'] for item in match['evidence']], ['H', None, 'A'])
        self.assertEqual(match['evidence'][0]['nearest_distance_m'], {'H': 1.0, 'A': 8.0})
        self.assertEqual(match['evidence'][0]['ball_xy'], (0.5, 0.5))
        self.assertEqual(match['audit']['timestamps_ms'], [[0, 100], [5000, 5000]])

    def test_missing_ball_stays_missing_and_does_not_imply_dead(self):
        archive(self.first, 'positions_FIRST_HALF.csv', [
            row(0, 1, 0, 1, 1, '1', ''), row(1, 2, 0, 1, 1, '8', ''),
        ])
        match = load_match([self.first, self.second], self.config)
        item = match['evidence'][0]
        self.assertFalse(item['ball_seen'])
        self.assertFalse(item['outside'])
        self.assertIsNone(item['candidate'])

    def test_rejects_inconsistent_references_within_timestamp(self):
        archive(self.first, 'positions_FIRST_HALF.csv', [
            row(0, 1, 0, 1, 1, '1'), row(1, 2, 0, 0, 1, '8'),
        ])
        with self.assertRaisesRegex(ValueError, 'inconsistent reference'):
            load_match([self.first, self.second], self.config)

    def test_uses_unique_row_majority_and_audits_reference_conflict(self):
        archive(self.first, 'positions_FIRST_HALF.csv', [
            row(0, 1, 0, 1, 1, '1'), row(1, 2, 0, 1, 1, '8'),
            row(2, 1, 0, 1, 2, '2'),
        ])
        match = load_match([self.first, self.second], self.config)
        self.assertEqual(match['reference'][0], 'H')
        self.assertEqual(match['audit']['reference_conflict_timestamps'], 1)

    def test_rejects_timestamps_that_are_not_ten_hz(self):
        archive(self.first, 'positions_FIRST_HALF.csv', [
            row(0, 1, 0, 1, 1, '1'), row(1, 2, 0, 1, 1, '8'),
            row(2, 1, 120, 1, 1, '1'), row(3, 2, 120, 1, 1, '8'),
        ])
        with self.assertRaisesRegex(ValueError, '10 Hz'):
            load_match([self.first, self.second], self.config)


if __name__ == '__main__':
    unittest.main()
