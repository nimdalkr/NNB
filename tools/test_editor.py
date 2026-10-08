import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import editor_model as M


def profile():
    p=M.baseline();p.update(id='test-profile',name='Test',enabled=True);return p


def rule(**values):
    return dict(id='rule-a',enabled=True,matchup='PvP',map='',opening='',mode='while',
                conditions=[{'field':'own_65','op':'>=','value':3}],actions={'aggression':1},**values)


class EditorTests(unittest.TestCase):
    def test_baseline_is_read_only(self):
        with self.assertRaises(ValueError):M.save(M.baseline())
        self.assertNotIn('NNBPolicy',M.compile_profile(M.baseline()))

    def test_disabled_profile_produces_original_config(self):
        p=profile();p['config']['Micro']['CombatSimRadius']=900;p['enabled']=False
        self.assertEqual(M.compile_profile(p),M.baseline()['config'])

    def test_fixed_choice_preserves_other_matchups_and_learning(self):
        p=profile();p['matchups']['PvP']['fixed']=True
        c=M.compile_profile(p)
        self.assertEqual(c['NNBPolicy']['openings'],{'PvP':p['matchups']['PvP']['opening']})
        self.assertEqual(c['IO'],p['config']['IO'])
        self.assertEqual(c['Strategy'],p['config']['Strategy'])

    def test_unknown_action_and_malformed_build_rejected(self):
        p=profile();r=rule();r['actions']={'teleport':1};p['rules']=[r]
        with self.assertRaises(ValueError):M.validate(p)
        p=profile();p['config']['Strategy']['Strategies']['bad']={'Race':'Protoss','OpeningGroup':'dragoons','OpeningBuildOrder':['unicorn']}
        with self.assertRaises(ValueError):M.validate(p)

    def test_save_conflict_preserves_latest(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(M,'PROFILES',Path(tmp)/'profiles'),patch.object(M,'HISTORY',Path(tmp)/'history'):
            p=profile();M.save(p,create=True);stale=copy.deepcopy(p)
            p['name']='new';M.save(p)
            with self.assertRaises(ValueError):M.save(stale)
            self.assertEqual(M.load_profile('test-profile')['name'],'new')

    def test_unexposed_config_does_not_enter_runtime(self):
        p=profile();p['config']['IO']['ReadDir']='elsewhere/'
        self.assertEqual(M.compile_profile(p)['IO'],M.baseline()['config']['IO'])

    def test_staging_rejects_changed_terrain_cache(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(M,'ROOT',Path(tmp)):
            root=Path(tmp);terrain=root/'data/terrain/test';cache=terrain/'bwapi-data/BWTA2/test.bwta'
            cache.parent.mkdir(parents=True);cache.write_text('verified cache')
            (root/'data/maps.json').write_text(json.dumps([{'name':'test','bwapiMapHashes':['test'],'chkSha256':'exact-map'}]))
            (terrain/'geometry.json').write_text(json.dumps({'cacheLoadVerified':True}))
            (terrain/'manifest.json').write_text(json.dumps({'cacheSha256':M.digest(cache),'chkSha256':'exact-map'}))
            self.assertEqual(M.verified_caches(),[cache])
            cache.write_text('different map')
            with self.assertRaises(ValueError):M.verified_caches()

    def engine(self,rules,facts,next_facts=None,matchup='PvP',enabled=True):
        exe=M.ROOT/'build/native-check/Release/nnb-policy-check.exe'
        if not exe.exists():self.skipTest('Build native-check first')
        data={'policy':{'enabled':enabled,'rules':rules},'facts':facts,'matchup':matchup,'map':'','opening':''}
        if next_facts is not None:data['nextFacts']=next_facts
        r=subprocess.run([str(exe)],input=json.dumps(data),capture_output=True,text=True,timeout=10)
        self.assertEqual(r.returncode,0,r.stderr)
        return json.loads(r.stdout)

    def test_real_cpp_threshold_and_scope(self):
        self.assertEqual(self.engine([rule()],{'own_65':2})['actions'],{})
        self.assertEqual(self.engine([rule()],{'own_65':3})['actions'],{'aggression':1})
        self.assertEqual(self.engine([rule()],{'own_65':3},matchup='PvZ')['actions'],{})

    def test_real_cpp_once_does_not_wait_for_reinforcements(self):
        r=rule();r['mode']='once'
        self.assertEqual(self.engine([r],{'own_65':3},{'own_65':1})['actions'],{'aggression':1})
        self.assertEqual(self.engine([rule()],{'own_65':3},{'own_65':1})['actions'],{})

    def test_real_cpp_rule_priority_and_disabled(self):
        a=rule();b=rule();b['id']='rule-b';b['actions']={'aggression':0,'gasWorkers':2}
        self.assertEqual(self.engine([a,b],{'own_65':3})['actions'],{'aggression':1,'gasWorkers':2})
        self.assertEqual(self.engine([a,b],{'own_65':3},enabled=False)['actions'],{})

    def test_future_or_unknown_facts_do_not_satisfy_conditions(self):
        self.assertEqual(self.engine([rule()],{})['matched'],[])


if __name__=='__main__':unittest.main()
