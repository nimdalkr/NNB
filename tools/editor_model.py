"""NNB editor profile validation and immutable runtime staging. No game control."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import threading
import uuid
from corpus import ROOT, read_json, digest
import build_provenance
import judgment_catalog

UPSTREAM = '4e96da0b7e31831ee97aaef153b2bef977a235e1'
PROFILES = ROOT / 'data/editor/profiles'
HISTORY = ROOT / 'data/editor/history'
PROFILE_LOCK = threading.Lock()
FIELDS = [
    ('Micro','KiteWithRangedUnits','원거리 유닛 치고 빠지기','bool',0,1,'원거리 마이크로'),
    ('Micro','WorkersDefendRush','일꾼으로 초반 공격 방어','bool',0,1,'일꾼 방어'),
    ('Micro','RetreatMeleeUnitShields','근접 유닛 후퇴 보호막','int',0,100,'질럿 등 근접 유닛 생존'),
    ('Micro','RetreatMeleeUnitHP','근접 유닛 후퇴 체력','int',0,100,'보호막과 체력을 함께 고려'),
    ('Micro','CombatSimRadius','교전 계산 범위 (픽셀)','int',128,1600,'전투 예상에 포함하는 주변 범위'),
    ('Micro','UnitNearEnemyRadius','적 접근 판단 거리 (픽셀)','int',64,1600,'근처 적 판단'),
    ('Micro','ScoutDefenseRadius','정찰 일꾼 방어 범위 (픽셀)','int',64,1600,'정찰 대응'),
    ('Macro','ProductionJamFrameLimit','생산 정체 대기 (프레임)','int',24,2400,'멈춘 생산 계획 처리'),
    ('Macro','WorkersPerRefinery','가스당 일꾼 수','int',0,3,'가스 수급'),
    ('Macro','WorkersPerPatch','미네랄당 일꾼 목표','float',1,3,'경제와 확장 판단'),
    ('Macro','AbsoluteMaxWorkers','전체 일꾼 상한','int',4,100,'NNB 프로필에서만 읽는 상한'),
    ('Macro','BuildingSpacing','건물 간격 (타일)','int',0,6,'건설 배치'),
    ('Macro','PylonSpacing','파일런 간격 (타일)','int',0,8,'파일런 배치'),
    ('Strategy','ScoutHarassEnemy','정찰 일꾼으로 견제','bool',0,1,'정찰 생존과 견제'),
    ('Strategy','AutoGasSteal','가스 러시 허용','bool',0,1,'상대 가스 방해'),
    ('Strategy','RandomGasStealRate','무작위 가스 러시 비율','float',0,1,'0이면 무작위 요청 안 함'),
    ('Strategy','UsePlanRecognizer','상대 전략 추정 사용','bool',0,1,'정찰 정보로 전략 추정'),
    ('Strategy','SurrenderWhenHopeIsLost','순정 기권 판단 사용','bool',0,1,'보정된 승률 수치가 아닌 순정 휴리스틱'),
]
FIELD_KEYS = {(s,k) for s,k,*_ in FIELDS}
ACTIONS = {
    'aggression': ('공격 허용',0,1,1,'1: 공격, 0: 방어. 개별 교전 후퇴 판단은 유지'),
    'retreatScore': ('전투 계산 후퇴 기준',-100000,100000,1,'전투 계산 점수가 이 값보다 낮으면 후퇴. 승률이 아님'),
    'retreatHoldFrames': ('후퇴 후 재공격 대기 (프레임)',0,1440,1,'24프레임은 게임 시간 1초'),
    'expandWorkersPerBase': ('기지당 일꾼 확장 기준',8,50,1,'기지 수 × 기준보다 일꾼이 많을 때 확장 후보'),
    'expandIdleWorkers': ('쉬는 일꾼 확장 기준',0,50,1,'이 수보다 많을 때 확장 후보. 안전·자원·생산 판단도 적용'),
    'maxWorkers': ('일꾼 상한',4,100,1,'전체 경제 목표 상한'),
    'gasWorkers': ('가스당 일꾼 수',0,3,1,'가스 수급 조절'),
    'meleeHP': ('근접 유닛 후퇴 체력',0,100,1,'개별 마이크로 기준'),
    'meleeShields': ('근접 유닛 후퇴 보호막',0,100,1,'개별 마이크로 기준'),
}
FACTS = {'seconds':'게임 시간 (초)','minerals':'보유 미네랄','gas':'보유 가스','supply':'현재 인구','workers':'완성된 일꾼 수','bases':'완성된 기지 수','army':'우리 병력 자원 가치','enemyVisibleArmy':'지금 보이는 적 병력 가치','enemyNearBase':'기지 768픽셀 안 보이는 적 병력 가치','enemyMainKnown':'상대 본진을 찾음 (1/0)','enemyCloakKnown':'상대 은폐 기술을 확인함 (1/0)'}
FACTS.update(judgment_catalog.PLAN_FACTS)
UNITS = {64:('Probe','프로브'),65:('Zealot','질럿'),66:('Dragoon','드라군'),67:('High Templar','하이 템플러'),68:('Archon','아칸'),60:('Corsair','커세어'),61:('Dark Templar','다크 템플러'),69:('Shuttle','셔틀'),70:('Scout','스카웃'),71:('Arbiter','아비터'),72:('Carrier','캐리어'),83:('Reaver','리버'),84:('Observer','옵저버'),154:('Nexus','넥서스'),155:('Robotics Facility','로보틱스'),156:('Pylon','파일런'),157:('Assimilator','어시밀레이터'),159:('Observatory','옵저버토리'),160:('Gateway','게이트웨이'),162:('Photon Cannon','포톤 캐논'),163:('Citadel of Adun','아둔'),164:('Cybernetics Core','사이버네틱스 코어'),165:('Templar Archives','템플러 아카이브'),166:('Forge','포지'),167:('Stargate','스타게이트'),169:('Fleet Beacon','플릿 비콘'),170:('Arbiter Tribunal','아비터 트리뷰널'),171:('Robotics Support Bay','로보틱스 서포트 베이'),172:('Shield Battery','쉴드 배터리'),37:('Zergling','적 저글링'),38:('Hydralisk','적 히드라'),43:('Mutalisk','적 뮤탈'),103:('Lurker','적 럴커'),0:('Marine','적 마린'),2:('Vulture','적 벌처'),5:('Siege Tank Tank Mode','적 탱크'),8:('Wraith','적 레이스')}


def baseline():
    config=json.loads(subprocess.check_output(['git','show',UPSTREAM+':Locutus.json'],cwd=ROOT))
    return dict(id='baseline', name='순정 Locutus · 읽기 전용', revision=0, enabled=False, config=config,
                matchups={m:{'fixed':False,'opening': next(x['Strategy'] for x in config['Strategy'][m]['Protoss'])} for m in ('PvP','PvT','PvZ')},rules=[])


def valid_id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z0-9-]{1,64}',value):raise ValueError('잘못된 프로필 ID')
    return value


def load_profile(id):
    return baseline() if id=='baseline' else read_json(PROFILES/(valid_id(id)+'.json'))


def list_profiles():
    PROFILES.mkdir(parents=True,exist_ok=True)
    return [baseline()]+[read_json(p) for p in sorted(PROFILES.glob('*.json'))]


def clone(id):
    p=copy.deepcopy(load_profile(id));p.update(id='nnb-'+uuid.uuid4().hex[:12],name='나의 NNB',revision=0,enabled=True)
    save(p,create=True)
    return p


def number(v,low,high,integer=False):
    if type(v) not in (int,float) or not low<=v<=high or (integer and int(v)!=v):raise ValueError(f'값은 {low}~{high} 범위여야 합니다')


def allowed_build_items():
    result={x[0].lower() for id,x in UNITS.items() if id>=60 and id not in (103,) and id not in (68,)}
    # Existing upstream commands/upgrades remain available, including argument-bearing forms.
    for b in baseline()['config']['Strategy']['Strategies'].values():
        for item in b.get('OpeningBuildOrder',[]):
            result.add(item.lower())
            # Form editing must accept the same atomic actions used in chained steps.
            for atom in re.sub(r'^\d+\s+x\s+','',item.lower()).split(' then '):
                result.add(atom.split(' @ ',1)[0])
    result.update(['go aggressive','go defensive','go scout','go start gas','go stop gas','go scout once around','go queue barrier'])
    return result


def valid_step(item,allowed):
    if not isinstance(item,str) or len(item)>180:return False
    s=item.strip().lower()
    if s in allowed:return True
    if ' then ' in s:return all(valid_step(x,allowed) for x in s.split(' then '))
    match=re.fullmatch(r'(\d+) x (.+)',s)
    if match:return 1<=int(match[1])<=100 and valid_step(match[2],allowed)
    if ' @ ' in s:
        act,place=s.split(' @ ',1)
        return place in ['main','natural','expo','hidden','wall','choke','proxy','center','hidden tech','macro','min only'] and act in allowed
    if re.fullmatch(r'go (gas until|aggressive at|pull workers|pull workers leaving) \d+',s):return True
    return False


def validate(p):
    valid_id(p['id'])
    if p['id']=='baseline':raise ValueError('순정 기준본은 변경할 수 없습니다. 복사본을 만드세요.')
    if not isinstance(p.get('name'),str) or not 1<=len(p['name'])<=80:raise ValueError('이름을 입력하세요')
    if type(p.get('enabled')) is not bool:raise ValueError('프로필 사용 여부가 잘못되었습니다')
    judgment_catalog.validate(p.get('recognition',{}))
    config=p['config']; original=baseline()['config']
    # User input cannot alter IO paths, hidden-information flags or unsupported parser sections.
    sanitized=copy.deepcopy(original)
    for s,k,label,kind,low,high,hint in FIELDS:
        value=config[s][k]
        if k in ('AbsoluteMaxWorkers','PylonSpacing') and isinstance(value,dict):raise ValueError(label+'은 공통 숫자 설정입니다')
        for v in (value.values() if isinstance(value,dict) else [value]):
            if kind=='bool':
                if type(v) is not bool:raise ValueError(label+'은 켜기/끄기 값입니다')
            else:number(v,low,high,kind=='int')
        if isinstance(value,dict) and (not value or set(value)-{'Zerg','Terran','Protoss','Unknown'}):raise ValueError('종족별 설정이 잘못되었습니다')
        # RapidJSON's IsDouble/IsInt are distinct in the native Get*ByRace parser.
        # Browser JSON serializes 2.0 as 2; restore the declared type before export.
        if kind in ('float','int'):
            cast=float if kind=='float' else int
            value={race:cast(v) for race,v in value.items()} if isinstance(value,dict) else cast(value)
        sanitized[s][k]=value
    strategies=config['Strategy']['Strategies']
    if not isinstance(strategies,dict) or len(strategies)>200:raise ValueError('빌드 목록이 잘못되었습니다')
    allowed=allowed_build_items()
    for name,b in strategies.items():
        if name in original['Strategy']['Strategies'] and b==original['Strategy']['Strategies'][name]:continue
        if not re.fullmatch(r'[A-Za-z0-9 _-]{1,80}',name) or b.get('Race')!='Protoss':raise ValueError('새 빌드는 프로토스만 지원합니다')
        if b.get('OpeningGroup') not in ['zealots','dragoons','dark templar','carriers','drop']:raise ValueError('후속 운영 계열이 잘못되었습니다')
        steps=b.get('OpeningBuildOrder')
        if not isinstance(steps,list) or not 1<=len(steps)<=300 or any(not valid_step(x,allowed) for x in steps):raise ValueError('지원하지 않는 빌드 항목이 있습니다')
        b['OpeningBuildOrder']=[x.strip() for x in steps]
    if not set(original['Strategy']['Strategies']).issubset(strategies):raise ValueError('순정 빌드는 목록에서 삭제하지 말고 복사해 수정하세요')
    labels=p.get('buildLabels',{})
    if not isinstance(labels,dict) or any(k not in strategies or not isinstance(v,str) or not 1<=len(v)<=80 for k,v in labels.items()):raise ValueError('빌드 표시 이름은 1~80자로 입력하세요')
    sanitized['Strategy']['Strategies']=copy.deepcopy(strategies)
    for m in ['PvP','PvT','PvZ']:
        v=p['matchups'][m]
        if type(v['fixed']) is not bool or v['opening'] not in strategies or strategies[v['opening']]['Race']!='Protoss':raise ValueError('종족전 빌드 선택이 잘못되었습니다')
    if not isinstance(p['rules'],list) or len(p['rules'])>100:raise ValueError('규칙은 100개까지 지원합니다')
    ids=set()
    maps={h for m in read_json(ROOT/'data/maps.json') for h in m['bwapiMapHashes']}
    for r in p['rules']:
        valid_id(r['id'])
        if r['id'] in ids:raise ValueError('규칙 ID가 중복됩니다')
        ids.add(r['id'])
        if type(r['enabled']) is not bool or r['mode'] not in ['while','once']:raise ValueError('규칙 방식이 잘못되었습니다')
        if r['matchup'] not in ['','PvP','PvT','PvZ'] or (r['map'] and r['map'] not in maps) or (r['opening'] and r['opening'] not in strategies):raise ValueError('규칙 범위가 잘못되었습니다')
        if not 1<=len(r['conditions'])<=20 or not 1<=len(r['actions'])<=9:raise ValueError('조건과 행동을 입력하세요')
        for c in r['conditions']:
            f=c['field']
            if f not in FACTS and not re.fullmatch(r'(own|visible)_(\d{1,3})',f):raise ValueError('지원하지 않는 판단 정보입니다')
            if f.startswith(('own_','visible_')) and int(f.split('_')[1])>=228:raise ValueError('유닛 번호가 잘못되었습니다')
            if c['op'] not in ['>=','<=','==','>','<']:raise ValueError('비교가 잘못되었습니다')
            number(c['value'],0,10000000)
        for key,v in r['actions'].items():
            if key not in ACTIONS:raise ValueError('지원하지 않는 행동입니다')
            _,low,high,step,_=ACTIONS[key];number(v,low,high,True)
    positions={r['id']:i for i,r in enumerate(p['rules'])}
    for r in p['rules']:
        overrides=r.get('overrides',[])
        if not isinstance(overrides,list) or any(not isinstance(x,str) or x not in positions or positions[x]<=positions[r['id']] for x in overrides):
            raise ValueError('명시한 우선 관계가 현재 규칙 순서와 맞지 않습니다. 연결 검사에서 다시 지정하세요.')
    p['config']=sanitized
    return p


def save(p,create=False):
    with PROFILE_LOCK:
        return _save(p,create)


def _save(p,create=False):
    validate(p); PROFILES.mkdir(parents=True,exist_ok=True)
    path=PROFILES/(p['id']+'.json')
    if path.exists() and read_json(path)['revision']!=p['revision']:raise ValueError('다른 창에서 수정되었습니다. 다시 불러오세요.')
    if not path.exists() and not create:raise ValueError('프로필이 없습니다')
    if path.exists():
        old=read_json(path);history=HISTORY/p['id'];history.mkdir(parents=True,exist_ok=True)
        archive=history/(str(old['revision'])+'.json')
        if not archive.exists():
            with archive.open('x',encoding='utf-8') as f:json.dump(old,f,ensure_ascii=False,indent=2)
    p['revision']+=1
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
    return p


def history(id):
    valid_id(id);folder=HISTORY/id
    return [dict(revision=p['revision'],name=p['name'],enabled=p['enabled']) for p in
            sorted((read_json(f) for f in folder.glob('*.json')),key=lambda p:p['revision'],reverse=True)]


def restore(id,revision,expected_revision):
    if id=='baseline':raise ValueError('순정 기준본은 변경할 수 없습니다')
    valid_id(id)
    if type(revision) is not int or revision<1:raise ValueError('잘못된 저장 번호')
    with PROFILE_LOCK:
        current=load_profile(id)
        if current['revision']!=expected_revision:raise ValueError('다른 창에서 수정되었습니다. 다시 불러오세요.')
        previous=read_json(HISTORY/id/(str(revision)+'.json'))
        previous['revision']=current['revision']
        return _save(previous)


def compile_profile(p):
    if p['id']!='baseline':p=validate(copy.deepcopy(p))
    config=copy.deepcopy(p['config'])
    if p['id']=='baseline' or not p['enabled']:return baseline()['config']
    config['NNBPolicy']={'enabled':True,'rules':p['rules'],'recognition':p.get('recognition',{}),
                         'openings':{m:v['opening'] for m,v in p['matchups'].items() if v['fixed']}}
    return config


def verified_caches():
    result=[]
    for m in read_json(ROOT/'data/maps.json'):
        h=m['bwapiMapHashes'][0];terrain=ROOT/'data/terrain'/h
        cache=terrain/'bwapi-data/BWTA2'/(h+'.bwta')
        try:
            geometry=read_json(terrain/'geometry.json');manifest=read_json(terrain/'manifest.json')
            if not geometry.get('cacheLoadVerified') or manifest['cacheSha256']!=digest(cache) or manifest['chkSha256']!=m['chkSha256']:
                raise ValueError('맵 지형 검증 결과가 달라졌습니다: '+m['name'])
        except (OSError,KeyError) as e:
            raise ValueError('검증된 맵 캐시가 필요합니다: '+m['name']) from e
        result.append(cache)
    return result


def stage(p):
    import editor_safety
    safety=editor_safety.review(p)
    if safety['blocked']:
        raise ValueError(f"연결 검사에서 {safety['errors']}개 문제를 찾았습니다. 초안은 저장할 수 있지만 문제를 수정하기 전 시험본을 만들 수 없습니다.")
    config=compile_profile(p)
    baseline_mode=p['id']=='baseline' or not p['enabled']
    dll=ROOT/'artifacts/upstream/NNB.dll' if baseline_mode else ROOT/'Release/Locutus.dll'
    if not dll.is_file():raise ValueError('먼저 NNB DLL을 빌드해야 합니다')
    if baseline_mode:
        record=read_json(ROOT/'artifacts/upstream/provenance.json')
        if record.get('upstreamCommit',record.get('commit'))!=UPSTREAM or record.get('strategyCodeChanged') is not False or digest(dll)!=record['sha256']:
            raise ValueError('순정 DLL 출처 또는 해시가 달라졌습니다')
    if not baseline_mode:build_provenance.check(dll)
    verified=verified_caches()
    folder=ROOT/'artifacts'/('editor-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
    ai=folder/'bwapi-data/AI';ai.mkdir(parents=True)
    (folder/'bwapi-data/write').mkdir();(folder/'bwapi-data/read').mkdir();(folder/'bwapi-data/logs').mkdir()
    (ai/'Locutus.json').write_text(json.dumps(config,ensure_ascii=True,indent=2),encoding='utf-8')
    shutil.copy2(dll,folder/'NNB.dll')
    caches=folder/'bwapi-data/BWTA2';caches.mkdir()
    copied=[]
    for cache in verified:
        shutil.copy2(cache,caches/cache.name);copied.append(cache.stem)
    report=dict(profileId=p['id'],revision=p['revision'],baseline=baseline_mode,dllSha256=digest(folder/'NNB.dll'),configSha256=digest(ai/'Locutus.json'),mapCaches=len(copied),nativeGameTested=False,directory=str(folder),gameLaunched=False,
                intendedUse='baseline-comparison' if baseline_mode else 'offline-candidate',productionEligible=False,
                profileFingerprint=safety['profileFingerprint'],staticErrors=safety['errors'],reviewItems=safety['reviews'])
    (folder/'compatibility.json').write_text(json.dumps(safety,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'profile.json').write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (ROOT/'data/editor/last-stage.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def catalog():
    return dict(fields=[dict(section=s,key=k,label=l,type=t,min=a,max=b,hint=h) for s,k,l,t,a,b,h in FIELDS],
                actions={k:dict(label=v[0],min=v[1],max=v[2],step=v[3],hint=v[4]) for k,v in ACTIONS.items()},facts=FACTS,
                units={str(k):dict(name=v[0],label=v[1]) for k,v in UNITS.items()},
                judgments=judgment_catalog.catalog(),buildItems=sorted(allowed_build_items()),maps=[{'name':m['name'],'hash':m['bwapiMapHashes'][0]} for m in read_json(ROOT/'data/maps.json')])
