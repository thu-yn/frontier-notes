import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import summarize
from validate import validate_issue


class IssueValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / '2026-10-07.json'
        self.issue = json.loads((summarize.ROOT / 'data/daily/2026-10-07.json').read_text())

    def validate(self, issue):
        self.path.write_text(json.dumps(issue))
        with contextlib.redirect_stdout(io.StringIO()):
            return validate_issue(self.path, '2026-10-07')

    def test_complete_issue(self):
        self.assertEqual(self.validate(self.issue)['date'], '2026-10-07')

    def test_wrong_date(self):
        self.issue['date'] = '2026-10-06'
        with self.assertRaisesRegex(ValueError, 'date'):
            self.validate(self.issue)

    def test_missing_or_invalid_sections(self):
        for key, value in [('editor_note', ''), ('math_note', []), ('crossover', None),
                           ('papers', {}), ('news', ['bad']), ('research_ideas', None)]:
            with self.subTest(key=key):
                issue = copy.deepcopy(self.issue)
                issue[key] = value
                with self.assertRaises(ValueError):
                    self.validate(issue)

    def test_all_sources_empty(self):
        for key in ('papers', 'repos', 'news'):
            self.issue[key] = []
        with self.assertRaisesRegex(ValueError, '全部为空'):
            self.validate(self.issue)

    def test_invalid_json(self):
        self.path.write_text('{')
        with self.assertRaises(json.JSONDecodeError):
            validate_issue(self.path, '2026-10-07')

    def test_optional_visualization_remains_soft(self):
        self.issue['math_note']['viz'] = {'type': 'unknown'}
        self.validate(self.issue)


class CodexInvocationTests(unittest.TestCase):
    def test_model_search_effort_and_output_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / 'data/raw/2026-11-04.json'
            raw.parent.mkdir(parents=True)
            raw.write_text('{"date":"2026-11-04"}')
            with patch.object(summarize, 'ROOT', root), \
                 patch.object(sys, 'argv', ['summarize.py', '--date', '2026-11-04']), \
                 patch.object(summarize.subprocess, 'run') as run, \
                 patch.object(summarize, 'validate_issue') as validate:
                summarize.main()
            command = run.call_args.args[0]
            self.assertIn('--search', command)
            self.assertEqual(command[command.index('--model') + 1], 'gpt-6.1-sol')
            self.assertIn('model_reasoning_effort="max"', command)
            self.assertEqual(run.call_args.kwargs['stdin'], summarize.subprocess.DEVNULL)
            validate.assert_called_once_with(root / 'data/daily/2026-11-04.json', '2026-11-04')

    def test_existing_issue_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ('raw', 'daily'):
                path = root / f'data/{folder}/2026-11-04.json'
                path.parent.mkdir(parents=True)
                path.write_text('{"date":"2026-11-04"}')
            with patch.object(summarize, 'ROOT', root), \
                 patch.object(sys, 'argv', ['summarize.py', '--date', '2026-11-04']), \
                 patch.object(summarize.subprocess, 'run') as run:
                with self.assertRaisesRegex(SystemExit, '不会覆盖'):
                    summarize.main()
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
