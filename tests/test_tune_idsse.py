import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
from test_external_idsse import fixture
from model.tune_idsse import validate_protocol, select_best, evaluate
from model.temporal import load_config


class TuneIDSSETests(unittest.TestCase):
    def test_tune_cli_does_not_open_holdout_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata, tracking, tree = fixture(root)
            metadata.write_text(metadata.read_text().replace('MatchId="test"', 'MatchId="DFL-MAT-dev"'))
            for group in tree:
                group.set('MatchId', 'DFL-MAT-dev')
            ET.ElementTree(tree).write(tracking)
            metadata.rename(root/'dev.metadata.xml')
            tracking.rename(root/'dev.tracking.xml')
            protocol = root/'protocol.json'
            protocol.write_text(json.dumps({
                'source_revision': 'a715a38dfbaf5f58e431727c2b78d174101a703c',
                'development': ['dev'], 'holdout': ['deliberately_absent'],
                'grid': {'control_frames': [2]}}))
            output, config = root/'report.json', root/'config.json'
            result = subprocess.run([sys.executable, '-m', 'model.tune_idsse',
                '--stage', 'tune', '--data-root', str(root), '--protocol', str(protocol),
                '--config-out', str(config), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text())
            self.assertEqual([m['id'] for m in report['matches']], ['DFL-MAT-dev'])
            self.assertEqual(json.loads(config.read_text())['version'], 5)
            self.assertNotIn('evidence', report['matches'][0])

    def test_overlap_duplicates_and_empty_splits_rejected(self):
        for dev, test in [(['a'], ['a']), (['a', 'a'], ['b']), ([], ['b']), (['a'], [])]:
            with self.assertRaises(ValueError):
                validate_protocol({'development': dev, 'holdout': test})

    def test_selection_counts_abstentions_as_errors(self):
        candidates = [{'aggregate': {'accuracy': .8, 'macro_f1': .8}},
                      {'aggregate': {'accuracy': .5, 'macro_f1': .9}},
                      {'aggregate': {'accuracy': .8, 'macro_f1': .85}}]
        self.assertIs(select_best(candidates), candidates[2])
        with self.assertRaises(ValueError):
            select_best([])

    def test_evaluation_resets_state_and_counts_real_turnover(self):
        config = load_config('model/config_v4.json')
        config['control_frames'] = 2
        match = {'evidence': [dict(candidate=c, ball_seen=True, outside=False,
                                  stationary_set_piece=False,
                                  nearest_distance_m={'H': 0 if c == 'H' else 10,
                                                      'A': 0 if c == 'A' else 10})
                              for c in ['H', 'H', 'A', 'A', None]],
                 'blocks': [(1, 0, 3), (2, 4, 4)], 'reference': ['H', 'H', 'A', 'A', 'H']}
        result = evaluate(match, config)
        self.assertEqual(result['score']['correct'], 4)
        self.assertEqual(result['score']['eligible'], 5)
        self.assertEqual(result['transitions'], 1)
        self.assertEqual(result['labels'], {'H': 2, 'A': 2, 'X': 1})


if __name__ == '__main__':
    unittest.main()
