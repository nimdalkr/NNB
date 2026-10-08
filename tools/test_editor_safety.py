import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import editor_model as M
import editor_safety as S
from test_editor import profile,rule


def build(p,steps):
    p['config']['Strategy']['Strategies']['Candidate']={'Race':'Protoss','OpeningGroup':'dragoons','OpeningBuildOrder':steps}
    p['matchups']['PvP']={'fixed':True,'opening':'Candidate'}
    return p


class SafetyTests(unittest.TestCase):
    def codes(self,p):return {x['code'] for x in S.review(p)['issues']}

    def test_native_data_and_missing_chain_repair(self):
        names,ids=S.catalog()
        self.assertEqual(names['dragoon']['gas'],50)
        p=build(profile(),['Dragoon'])
        before=copy.deepcopy(p);report=S.review(p)
        self.assertTrue(report['blocked'])
        self.assertIn('NO_GAS_SOURCE',self.codes(p))
        item=next(x for x in report['issues'] if x.get('fix'))
        result=S.propose(p,item['id'])
        self.assertEqual(p,before,'Preview must not mutate the saved/draft source')
        self.assertEqual(result['profile']['config']['Strategy']['Strategies']['Candidate']['OpeningBuildOrder'],['Pylon','Gateway','Cybernetics Core','Assimilator','Dragoon'])
        self.assertFalse(result['report']['blocked'])
        self.assertFalse(result['report']['gameplayValidated'])

    def test_existing_dependencies_move_without_duplication(self):
        p=build(profile(),['Dragoon','Pylon @ main','Gateway','Cybernetics Core','Assimilator'])
        changes=S.repair_dependencies(p,'Candidate')
        steps=p['config']['Strategy']['Strategies']['Candidate']['OpeningBuildOrder']
        self.assertEqual(steps,['Pylon @ main','Gateway','Cybernetics Core','Assimilator','Dragoon'])
        self.assertEqual(len(changes),4)

    def test_upgrade_dependencies_are_checked(self):
        p=build(profile(),['Pylon','Assimilator','Singularity Charge'])
        self.assertIn('MISSING_REQUIRED',self.codes(p))

    def test_supply_auto_replan_is_review_not_impossible_production(self):
        p=build(profile(),['6 x Probe'])
        report=S.review(p)
        self.assertIn('SUPPLY_REPLAN',self.codes(p))
        self.assertFalse(report['blocked'])

    def test_parser_ignored_then_and_count_rejected(self):
        p=build(profile(),['go defensive then go scout'])
        self.assertIn('PARSER_MISMATCH',self.codes(p))
        p=build(profile(),['2 x go gas until 100'])
        self.assertIn('PARSER_MISMATCH',self.codes(p))

    def test_gas_budget_uncertainty_is_not_fake_resource_simulation(self):
        p=build(profile(),['Pylon','Gateway','Assimilator','Cybernetics Core','go stop gas','Dragoon'])
        self.assertIn('GAS_STOP',self.codes(p))
        self.assertFalse(S.review(p)['blocked'])

    def test_zero_gas_without_recovery_blocks(self):
        p=profile();p['config']['Macro']['WorkersPerRefinery']=0
        self.assertTrue(S.review(p)['blocked'])
        self.assertIn('ZERO_GAS',self.codes(p))

    def test_permanent_gas_shutdown_blocks(self):
        p=profile();r=rule();r['mode']='once';r['actions']={'gasWorkers':0};p['rules']=[r]
        self.assertTrue(S.review(p)['blocked'])

    def test_gas_recovery_must_cover_all_stopped_maps(self):
        p=profile();resume=rule();resume['actions']={'gasWorkers':3};resume['map']=M.catalog()['maps'][0]['hash']
        stop=rule();stop.update(id='gas-stop',mode='once',actions={'gasWorkers':0})
        stop['conditions']=[{'field':'seconds','op':'>=','value':30}]
        p['rules']=[resume,stop]
        finding=next(x for x in S.review(p)['issues'] if x['code']=='RULE_GAS_STOP')
        self.assertEqual(finding['severity'],'error')
        p['config']['Macro']['WorkersPerRefinery']=0
        finding=next(x for x in S.review(p)['issues'] if x['code']=='ZERO_GAS' and x['where']=='PvP')
        self.assertEqual(finding['severity'],'error')
        resume['map']='';p['rules']=[resume]
        finding=next(x for x in S.review(p)['issues'] if x['code']=='ZERO_GAS' and x['where']=='PvP')
        self.assertEqual(finding['severity'],'review')

    def test_race_config_uses_our_protoss_race_in_every_matchup(self):
        p=profile();p['config']['Macro']['WorkersPerRefinery']={'Protoss':0,'Zerg':3,'Terran':3}
        findings=[x for x in S.review(p)['issues'] if x['code']=='ZERO_GAS']
        self.assertEqual({x['where'] for x in findings},{'PvP','PvZ','PvT'})
        p['config']['Macro']['WorkersPerRefinery']={'Protoss':3,'Zerg':0,'Terran':0}
        self.assertNotIn('ZERO_GAS',self.codes(p))

    def test_original_transition_can_override_selected_carriers(self):
        p=profile();p['matchups']['PvP']={'fixed':True,'opening':'PlasmaCarriers'}
        self.assertIn('GROUP_RESET',self.codes(p))
        self.assertTrue(S.review(p)['blocked'])

    def test_attack_impacts_production_as_well_as_combat(self):
        p=profile();p['rules']=[rule()];r=S.review(p)
        self.assertIn('production',r['impacts'][0]['areas'])

    def test_whitespace_is_normalized_before_native_export(self):
        p=build(profile(),[' Probe ']);c=M.compile_profile(p)
        self.assertEqual(c['Strategy']['Strategies']['Candidate']['OpeningBuildOrder'],['Probe'])

    def test_browser_whole_numbers_export_as_native_required_numeric_types(self):
        p=profile();p['config']['Macro']['WorkersPerPatch']={'Protoss':2}
        p['config']['Strategy']['RandomGasStealRate']=1
        p['config']['Macro']['ProductionJamFrameLimit']=600.0
        exported=json.loads(json.dumps(M.compile_profile(p)))
        self.assertIs(type(exported['Macro']['WorkersPerPatch']['Protoss']),float)
        self.assertIs(type(exported['Strategy']['RandomGasStealRate']),float)
        self.assertIs(type(exported['Macro']['ProductionJamFrameLimit']),int)

    def test_contradictory_predicates_never_pass(self):
        p=profile();r=rule();r['conditions'].append({'field':'own_65','op':'<','value':3});p['rules']=[r]
        self.assertIn('IMPOSSIBLE_CONDITION',self.codes(p))
        r['conditions']=[{'field':'workers','op':'>','value':2},{'field':'workers','op':'<','value':3}]
        self.assertIn('IMPOSSIBLE_CONDITION',self.codes(p))

    def test_overlapping_actions_need_explicit_priority(self):
        p=profile();a=rule();b=rule();b.update(id='rule-b',actions={'aggression':0});p['rules']=[a,b]
        report=S.review(p);self.assertTrue(report['blocked'])
        issue=next(x for x in report['issues'] if x['code']=='RULE_CONFLICT')
        fixed=S.propose(p,issue['id'])['profile']
        self.assertFalse(S.review(fixed)['blocked'])
        self.assertEqual(fixed['rules'][0]['overrides'],['rule-b'])

    def test_disjoint_maps_do_not_conflict(self):
        p=profile();a=rule();b=rule();b.update(id='rule-b',actions={'aggression':0})
        maps=M.catalog()['maps'];a['map']=maps[0]['hash'];b['map']=maps[1]['hash'];p['rules']=[a,b]
        self.assertNotIn('RULE_CONFLICT',self.codes(p))

    def test_first_three_then_reinforce_does_not_need_simultaneous_override(self):
        p=profile();a=rule();a['mode']='once';b=rule();b.update(id='rule-b',actions={'aggression':0});b['conditions'][0]['op']='<'
        p['rules']=[a,b];r=S.review(p)
        self.assertFalse(r['blocked']);self.assertIn('LATCH_PRIORITY',self.codes(p))

    def test_runtime_creation_rechecks_even_without_ui(self):
        p=build(profile(),['Dragoon'])
        with self.assertRaisesRegex(ValueError,'연결 검사'):M.stage(p)

    def test_disabled_profile_uses_baseline_and_keeps_draft_findings(self):
        p=build(profile(),['Dragoon']);p['enabled']=False;r=S.review(p)
        self.assertFalse(r['blocked']);self.assertGreater(r['errors'],0)
        self.assertEqual(M.compile_profile(p),M.baseline()['config'])

    def test_fingerprint_changes_when_conditions_change(self):
        p=profile();p['rules']=[rule()];old=S.review(p)['profileFingerprint']
        p['rules'][0]['conditions'][0]['value']=5
        self.assertNotEqual(S.review(p)['profileFingerprint'],old)

    def test_revision_restore_preserves_current_and_rejects_stale(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(M,'PROFILES',Path(tmp)/'profiles'),patch.object(M,'HISTORY',Path(tmp)/'history'):
            p=profile();M.save(p,create=True);p['config']['Macro']['AbsoluteMaxWorkers']=60;M.save(p)
            self.assertEqual(M.history(p['id'])[0]['revision'],1)
            with self.assertRaises(ValueError):M.restore(p['id'],1,1)
            restored=M.restore(p['id'],1,2)
            self.assertEqual(restored['revision'],3)
            self.assertEqual(restored['config']['Macro']['AbsoluteMaxWorkers'],75)
            self.assertEqual(M.read_json(M.HISTORY/p['id']/'2.json')['config']['Macro']['AbsoluteMaxWorkers'],60)


if __name__=='__main__':unittest.main()
