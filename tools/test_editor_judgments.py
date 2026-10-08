import copy
import json
import shutil
import subprocess
import unittest
import editor_model as M
import editor_safety as S
import judgment_catalog as J
from test_editor import profile,rule
import test_editor


class JudgmentTests(unittest.TestCase):
    def test_display_names_do_not_enter_game_configuration(self):
        p=profile();before=M.compile_profile(p);p['buildLabels']={'DTDrop':'내 다크 드롭'}
        self.assertEqual(before,M.compile_profile(p))
        p['buildLabels']['missing']='없는 빌드'
        with self.assertRaises(ValueError):M.validate(p)

    def test_chained_native_commands_survive_form_edit(self):
        p=profile();p['config']['Strategy']['Strategies']['DTDrop']['OpeningBuildOrder'][1]='pylon @ natural then go scout while safe'
        self.assertEqual(M.compile_profile(p)['Strategy']['Strategies']['DTDrop']['OpeningBuildOrder'][1],'pylon @ natural then go scout while safe')

    def test_recognition_export_and_disabled_baseline(self):
        p=profile();before=S.fingerprint(p);p['recognition']={'hydraHatches':3,'workerCount':4}
        self.assertEqual(M.compile_profile(p)['NNBPolicy']['recognition'],p['recognition'])
        self.assertNotEqual(before,S.fingerprint(p))
        self.assertIn('RECOGNITION_CHANGE',{x['code'] for x in S.review(p)['issues']})
        p['enabled']=False;self.assertEqual(M.compile_profile(p),M.baseline()['config'])

    def test_recognition_invalid_thresholds_and_windows_reject(self):
        for settings in ({'hydraHatches':0},{'workerCount':2.5},{'fake':3},{'startFrame':500,'endFrame':200}):
            p=profile();p['recognition']=settings
            with self.assertRaises(ValueError):M.validate(p)

    def test_recognition_dependent_rule_checks_engine_and_switch(self):
        p=profile();r=rule();r['conditions']=[{'field':'plan_hydra','op':'==','value':1}];r['actions']={'aggression':0};p['rules']=[r]
        result=test_editor.EditorTests().engine([r],{'plan_hydra':1})
        self.assertEqual(result['actions']['aggression'],0)
        self.assertEqual(test_editor.EditorTests().engine([r],{'plan_hydra':0})['actions'],{})
        p['config']['Strategy']['UsePlanRecognizer']=False
        self.assertIn('RECOGNIZER_DISABLED',{x['code'] for x in S.review(p)['issues']})

    def test_native_catalog_generated_from_same_defaults(self):
        self.assertEqual((M.ROOT/'Steamhammer/Source/NNBPlanSettings.h').read_text(encoding='utf-8'),J.native_header())

    def test_strategy_results_are_mutually_exclusive(self):
        a=rule();a['conditions']=[{'field':'plan_hydra','op':'==','value':1}]
        b=rule();b['conditions']=[{'field':'plan_fast','op':'==','value':1}]
        self.assertFalse(S.can_overlap(a,b))
        a['conditions']+=b['conditions']
        self.assertFalse(S.feasible(a))

    def test_disabled_individual_inference_blocks_dependent_response(self):
        p=profile();r=rule();r['conditions']=[{'field':'plan_hydra','op':'==','value':1}];p['rules']=[r];p['recognition']={'hydraEnabled':0}
        self.assertIn('PLAN_DISABLED',{x['code'] for x in S.review(p)['issues']})
        r['conditions'][0]['value']=0
        self.assertNotIn('PLAN_DISABLED',{x['code'] for x in S.review(p)['issues']})
        r['conditions'][0]['value']=0.5
        self.assertIn('IMPOSSIBLE_CONDITION',{x['code'] for x in S.review(p)['issues']})

    @unittest.skipUnless(shutil.which('node'),'Node is needed for editor JavaScript checks')
    def test_all_original_openings_display_and_roundtrip(self):
        result=subprocess.run(['node','tools/test_opening_language.js'],cwd=M.ROOT,input=json.dumps({'catalog':M.catalog(),'strategies':M.baseline()['config']['Strategy']['Strategies']}),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
