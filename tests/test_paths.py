import json
import tempfile
import unittest
from pathlib import Path

from jobtracker.paths import StatePaths, initialize_state, resolve_state_paths


class StatePathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def make_source(self) -> Path:
        source = self.root / "source"
        paths = StatePaths(source)
        for path in paths.required_files():
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".json":
                path.write_text(json.dumps({"schema_version": 1, "jobs": []}))
            else:
                path.write_text("# Fictional resume\n")
        return source

    def test_explicit_path_precedes_environment_and_config(self):
        (self.repository / ".jobtracker.json").write_text(
            json.dumps({"state_dir": str(self.root / "configured")})
        )
        paths = resolve_state_paths(
            self.root / "explicit",
            environ={"JOBTRACKER_STATE_DIR": str(self.root / "environment")},
            repository_root=self.repository,
        )
        self.assertEqual(paths.root, (self.root / "explicit").resolve())

    def test_environment_precedes_local_config(self):
        (self.repository / ".jobtracker.json").write_text(
            json.dumps({"state_dir": str(self.root / "configured")})
        )
        paths = resolve_state_paths(
            environ={"JOBTRACKER_STATE_DIR": str(self.root / "environment")},
            repository_root=self.repository,
        )
        self.assertEqual(paths.root, (self.root / "environment").resolve())

    def test_local_config_supports_relative_path(self):
        (self.repository / ".jobtracker.json").write_text(
            json.dumps({"state_dir": "../private-state"})
        )
        paths = resolve_state_paths(environ={}, repository_root=self.repository)
        self.assertEqual(paths.root, (self.root / "private-state").resolve())

    def test_initialize_copies_complete_state_and_refuses_overwrite(self):
        source = self.make_source()
        target = StatePaths(self.root / "private-state")
        initialize_state(target, source_root=source, repository_root=self.repository)
        for path in target.required_files():
            self.assertTrue(path.is_file())
        with self.assertRaises(ValueError):
            initialize_state(target, source_root=source, repository_root=self.repository)

    def test_state_directory_cannot_be_inside_repository(self):
        source = self.make_source()
        with self.assertRaises(ValueError):
            initialize_state(
                StatePaths(self.repository / "private"),
                source_root=source,
                repository_root=self.repository,
            )


if __name__ == "__main__":
    unittest.main()
