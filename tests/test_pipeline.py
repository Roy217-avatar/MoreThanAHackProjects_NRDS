"""End-to-end synthetic tactical ATD to official CSV contract."""

import csv
import tempfile
import unittest
from pathlib import Path

from model.temporal import run


ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def test_runner_rejects_colliding_output_paths_before_loading_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prediction.csv"
            with self.assertRaisesRegex(ValueError, "different paths"):
                run(ROOT / "model" / "config.json", path, path, data_dir=directory)
            self.assertFalse(path.exists())

    def test_runner_accepts_authorized_bundle_location_and_resets_at_halftime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tactical = root / "tactical"
            tactical.mkdir()
            (tactical / "BAR-ATH_tactical_atd.xml").write_text(
                '<Root><Team id="10"><Name>Home</Name></Team>'
                '<Team id="20"><Name>Away</Name></Team>'
                '<Player teamId="10"/><Player teamId="20"/></Root>')
            (tactical / "BAR-ATH_tactical_smart_tagging.xml").write_text("<Root/>")
            with (tactical / "BAR-ATH_tactical_atd.txt").open("w") as handle:
                for frame_id in range(1, 199320):
                    handle.write("{}:0.5,0.5,0;0.8,0.8,0:0.5,0.5,0\n".format(frame_id))

            output = root / "prediction.csv"
            diagnostics = root / "diagnostics.csv"
            try:
                run(ROOT / "model" / "config.json", output, diagnostics, data_dir=root)
            except TypeError as error:
                self.fail("runner cannot use a supplied tactical bundle: {}".format(error))

            with output.open(newline="") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0], ["frame", "label"])
            self.assertEqual(len(rows), 199320)
            self.assertEqual(rows[1], ["0", "X"])
            self.assertEqual(rows[11185], ["11184", "X"])
            self.assertEqual(rows[11197], ["11196", "H"])
            self.assertEqual(rows[90653], ["90652", "X"])
            self.assertEqual(rows[110809], ["110808", "X"])
            self.assertEqual(rows[110821], ["110820", "H"])
            self.assertEqual(rows[-1], ["199318", "X"])
            with diagnostics.open(newline="") as handle:
                self.assertEqual(sum(1 for _ in csv.reader(handle)), 199320)


if __name__ == "__main__":
    unittest.main()
