import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from corpus import candidates, index_record, inside, state_at


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'game.rep').write_bytes(b'replay')
        self.sha = hashlib.sha256(b'replay').hexdigest()
        with gzip.open(self.root / 'state.gz', 'wt', encoding='utf-8') as f:
            json.dump({'sourceReplaySha256': self.sha, 'mismatchedTags': 0}, f)
        self.raw = dict(path='game.rep', sha256=self.sha, cache='state.gz', mapSha1='exact',
                        matchup='pvp', split='analysis', stateStatus='zero_generation_mismatch',
                        externallyCorroborated=True, sourceListedMmr=None,
                        perspectives=[{'owner': 1, 'classification': 'TwoGate3Zealot', 'protossMmrVerified': None},
                                      {'owner': 2, 'classification': 'TwoGate3Zealot', 'protossMmrVerified': None}])

    def test_unknown_ratings_keep_both_pvp_perspectives(self):
        r = index_record(self.root, self.raw)
        self.assertTrue(r['stateEligible'])
        self.assertEqual(len(list(candidates([r], 'exact', 'pvp', 'TwoGate3Zealot', 5000))), 2)

    def test_holdout_and_other_map_or_build_never_returned(self):
        r = index_record(self.root, self.raw)
        for key, value in [('split', 'holdout'), ('mapSha1', 'other'), ('matchup', 'pvz')]:
            with self.subTest(key=key):
                self.assertEqual(list(candidates([{**r, key: value}], 'exact', 'pvp', 'TwoGate3Zealot', 5000)), [])
        self.assertEqual(list(candidates([r], 'exact', 'pvp', 'Nexus23', 5000)), [])

    def test_corrupt_replay_preserved_but_not_evidence(self):
        (self.root / 'game.rep').write_bytes(b'changed')
        r = index_record(self.root, self.raw)
        self.assertIn('replay_hash_mismatch', r['technicalIssues'])
        self.assertFalse(r['stateEligible'])

    def test_wrong_state_identity_rejected(self):
        with gzip.open(self.root / 'state.gz', 'wt', encoding='utf-8') as f:
            json.dump({'sourceReplaySha256': 'wrong', 'mismatchedTags': 0}, f)
        self.assertIn('state_source_hash_mismatch', index_record(self.root, self.raw)['technicalIssues'])

    def test_evidence_window_and_provisional(self):
        r = index_record(self.root, self.raw)
        self.assertEqual(list(candidates([r], 'exact', 'pvp', 'TwoGate3Zealot', 11521)), [])
        self.assertEqual(len(list(candidates([r], 'exact', 'pvp', 'TwoGate3Zealot', 11521, True))), 2)

    def test_state_is_not_from_future_or_long_ago(self):
        snaps = [[100, 1], [148, 1], [140, 2]]
        self.assertEqual(state_at(snaps, 1, 140), [100, 1])
        self.assertIsNone(state_at(snaps, 1, 200))
        self.assertIsNone(state_at(snaps, 1, 99))

    def test_source_path_cannot_escape(self):
        with self.assertRaises(ValueError):
            inside(self.root, '../outside.rep')


if __name__ == '__main__':
    unittest.main()
