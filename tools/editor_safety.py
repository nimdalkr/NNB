"""Conservative cross-system checks for editor candidates, not a game simulator."""
import copy
from functools import lru_cache
import hashlib
import json
import math
import re
import subprocess
from corpus import ROOT, digest

VERSION = 1
GROUPS = {
    'economy': ('자원과 일꾼', '가스 수급, 미네랄 수급, 일꾼 생산', '가스 부족·일꾼 공백·자원 잔고'),
    'production': ('생산과 보급', '선행 건물, 생산 대기열, 보급, 연구', '누락된 생산·생산 정체·보급 막힘'),
    'scouting': ('정찰과 대응', '상대 위치·기술 확인, 가스 러시, 긴급 대응', '정찰 생존·은폐 대응·정보 없이 내린 판단'),
    'combat': ('공격과 방어', '공격 출발, 합류, 교전 후퇴, 본진 방어', '출발·증원 타이밍·병력 분산·본진 피해'),
    'placement': ('건설과 이동', '전력 공급, 건물 간격, 확장과 길목', '건설 실패·길막·파일런 파괴 후 생산'),
}
LINKS = {
    'gasWorkers': ['economy','production'], 'maxWorkers': ['economy','production'],
    'expandWorkersPerBase': ['economy','production','placement','combat'],
    'expandIdleWorkers': ['economy','production','placement','combat'],
    'aggression': ['combat','production','economy','scouting'], 'retreatScore': ['combat','scouting'],
    'retreatHoldFrames': ['combat'], 'meleeHP': ['combat'], 'meleeShields': ['combat'],
}


def canonical(s):
    return s.replace('_',' ').lower().strip()


@lru_cache(maxsize=2)
def _catalog(stamp):
    exe=ROOT/'build/native-check/Release/nnb-build-catalog.exe'
    r=subprocess.run([str(exe)],capture_output=True,text=True,check=True,timeout=15)
    items=json.loads(r.stdout);names={};ids={}
    for item in items:
        key=canonical(item['name']);names[key]=item
        if key.startswith('protoss '):names[key[8:]]=item
        if item['kind']=='unit':ids[item['id']]=item
    return names,ids


def catalog():
    exe=ROOT/'build/native-check/Release/nnb-build-catalog.exe'
    if not exe.exists():raise ValueError('연결 검사기가 없습니다. scripts/build-editor.ps1을 실행하세요.')
    return _catalog((exe.stat().st_mtime_ns,exe.stat().st_size))


def fingerprint(p):
    payload={k:p[k] for k in ('enabled','config','matchups','rules')}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode()).hexdigest()


def race_value(config,section,key):
    v=config[section][key]
    # ParseUtils::Get*ByRace reads self()->getRace(), not the opponent.
    return v.get('Protoss',0) if isinstance(v,dict) else v


def parse_step(text):
    """Mirror count recognition before MacroAct's then/location parsing."""
    count=1
    m=re.fullmatch(r'([0-9]+)\s+x\s+([a-zA-Z_ ]+(\s+@\s+[a-zA-Z_ ]+)?)',text)
    if m:count=int(m[1]);text=m[2]
    elif re.match(r'^\d+\s+x\s+',text):raise ValueError('이 수량·명령 조합은 순정 파서가 읽지 못합니다')
    parts=canonical(text).split(' then ')
    if any(x.startswith('go ') for x in parts[:-1]):raise ValueError('go 명령 뒤의 then은 순정 파서가 무시합니다')
    result=[]
    for part in parts:
        name,sep,location=part.partition(' @ ')
        result.append((name,location))
    return count,result


def prerequisites(item,level=1):
    actual=item['levels'][min(level,len(item['levels']))-1] if item['kind']=='upgrade' else item
    req={}
    for r in actual['requires']:req[r['id']]=max(req.get(r['id'],0),r['count'])
    if item.get('building') and item['id'] not in (154,156,157):req[156]=max(1,req.get(156,0))
    return req,actual


def scoped_overlap(a,b):
    return all(not a.get(k) or not b.get(k) or a[k]==b[k] for k in ('matchup','map','opening'))


def covers_scope(a,b):
    return all(not a.get(k) or a[k]==b.get(k) for k in ('matchup','map','opening'))


def feasible(rule):
    return all(lo<=hi for lo,hi in bounds(rule).values())


def bounds(rule):
    values={}
    for c in rule['conditions']:
        f,op,v=c['field'],c['op'],c['value']
        lo,hi=values.get(f,(0,float('inf')))
        if op in ('>=','=='):lo=max(lo,v)
        if op in ('<=','=='):hi=min(hi,v)
        if op=='>':lo=max(lo,math.nextafter(float(v),math.inf))
        if op=='<':hi=min(hi,math.nextafter(float(v),-math.inf))
        if f.startswith(('own_','visible_')) or f in ('workers','bases','enemyMainKnown','enemyCloakKnown'):
            lo=math.ceil(lo);hi=math.floor(hi) if math.isfinite(hi) else hi
        if f in ('enemyMainKnown','enemyCloakKnown'):hi=min(hi,1)
        if f=='supply':hi=min(hi,200)
        values[f]=(lo,hi)
    return values


def can_overlap(a,b):
    x,y=bounds(a),bounds(b)
    return all(max(x.get(f,(0,math.inf))[0],y.get(f,(0,math.inf))[0])<=min(x.get(f,(0,math.inf))[1],y.get(f,(0,math.inf))[1]) for f in x.keys()|y.keys())


def review(profile):
    import editor_model as M
    p=copy.deepcopy(profile)
    if p['id']!='baseline':M.validate(p)
    original=M.baseline()['config'];issues=[];impacts=[]
    def issue(code,severity,title,detail,where,fix=None):
        value=dict(code=code,severity=severity,title=title,detail=detail,where=where)
        if fix:value['fix']=fix
        value['id']=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True).encode()).hexdigest()[:16]
        issues.append(value)
    def impact(change,groups):
        impacts.append({'change':change,'areas':list(dict.fromkeys(groups))})
    try:names,ids=catalog()
    except (ValueError,OSError,subprocess.SubprocessError,json.JSONDecodeError) as e:
        issue('CHECKER_MISSING','error','연결 검사를 실행할 수 없습니다',str(e),'검사기')
        names,ids={},{}

    changed={name:b for name,b in p['config']['Strategy']['Strategies'].items() if b!=original['Strategy']['Strategies'].get(name)}
    transitions=[]
    used_names=set(changed)|{v['opening'] for v in p['matchups'].values() if v['fixed']}
    for name in sorted(used_names):
        group=p['config']['Strategy']['Strategies'][name]['OpeningGroup']
        text={
            'zealots':'PvP/PvT에서 러시·전진 러시가 끝났다고 판단하면 드라군 계열로 바뀝니다. PvZ도 이후 드라군·아칸을 섞는 순정 대응이 있습니다.',
            'dragoons':'드라군과 사거리 업그레이드가 기본입니다. 적 은폐 확인 시 옵저버, PvZ 적 공중 전투 유닛 확인 시 커세어를 생산하는 순정 대응도 남습니다.',
            'drop':'후속 생산은 드라군 계열과 공유합니다. 드롭 계열 선택만으로 수송·호위·방어 전체가 고정되는 것은 아닙니다.',
            'dark templar':'후속 생산은 드라군·사거리와 다크 템플러 견제를 함께 고려합니다.',
            'carriers':'Plasma 외 맵에서 캐리어 계열은 순정 update에서 드라군으로 바뀝니다. 맵 전체를 정찰했는데 적 정보가 없는 별도 예외가 있습니다.',
        }[group]
        transitions.append(dict(build=name,group=group,behavior=text))
        if group=='carriers':
            issue('GROUP_RESET','error','선택한 후속 계열을 순정이 바꿉니다',text+' 현재 시즌 맵에서 고정 캐리어 운영을 지원하려면 이 전환 코드까지 별도 검증해야 합니다.',name)
    for name,b in changed.items():
        impact('빌드 '+name,list(GROUPS))
        if not names:continue
        counts={64:4,154:1};upgrades={};supply=8;capacity=18;gas_possible=False;gas_cost=0;stopped=False;limited=False
        for index,text in enumerate(b['OpeningBuildOrder']):
            where=f'{name} · {index+1}번째'
            try:count,parts=parse_step(text)
            except ValueError as e:
                issue('PARSER_MISMATCH','error','실제로 읽히지 않는 명령',str(e),where);continue
            for unused in range(count):
                for key,location in parts:
                    if key.startswith('go '):
                        argument=re.search(r' (\d+)$',key)
                        if argument and int(argument[1])>2147483647:
                            issue('COMMAND_OVERFLOW','error','명령 숫자가 실행 범위를 넘었습니다','명령 인자는 32비트 정수 범위여야 합니다.',where)
                        if key=='go stop gas':stopped=True
                        elif key=='go start gas':stopped=False;limited=False
                        elif key.startswith('go gas until '):limited=True;stopped=False
                        continue
                    item=names.get(key)
                    if not item:
                        issue('UNKNOWN_ITEM','error','생산 항목을 읽을 수 없습니다',text,where);continue
                    if location and not item.get('building'):
                        issue('IGNORED_LOCATION','error','적용되지 않는 위치 지정','위치 지정은 건물에만 적용됩니다.',where)
                    level=upgrades.get(key,0)+1
                    if item['kind']=='upgrade' and level>len(item['levels']):
                        issue('UPGRADE_EXHAUSTED','error','완료 가능한 업그레이드 횟수를 넘었습니다',text,where)
                    req,cost=prerequisites(item,level)
                    missing=[ids[r]['name'].replace('Protoss_','').replace('_',' ') for r,n in req.items() if counts.get(r,0)<n and r in ids]
                    if missing:
                        issue('MISSING_REQUIRED','error','선행 생산 순서가 빠졌습니다',f'{text} 전에 필요한 항목: '+', '.join(missing)+'. 순정이 대기열을 바꾸거나 항목을 버릴 수 있습니다.',where,{'type':'dependencies','build':name,'label':'연결된 선행 순서 함께 맞추기'})
                    gas_cost+=cost['gas']
                    if cost['gas'] and not gas_possible:
                        issue('NO_GAS_SOURCE','error','가스 생산 경로가 없습니다',text+' 전에 어시밀레이터가 필요합니다.',where,{'type':'dependencies','build':name,'label':'가스 건물과 선행 순서 함께 맞추기'})
                    if cost['gas'] and stopped:
                        issue('GAS_STOP','review','가스 중단 이후 가스가 필요한 생산','이전에 모은 가스가 충분한지, 다시 채취할 조건이 있는지 확인해야 합니다.',where)
                        stopped=False  # Report this segment once; it is a timing uncertainty, not a proof of failure.
                    if item['kind']=='unit':
                        if supply+item['supply']>capacity:
                            issue('SUPPLY_REPLAN','review','계획된 보급보다 생산 인구가 많습니다','순정의 자동 파일런 보충에 따라 빌드 타이밍이 달라질 수 있습니다.',where)
                            capacity=min(400,capacity+16)
                        supply+=item['supply'];capacity=min(400,capacity+item['capacity'])
                        counts[item['id']]=counts.get(item['id'],0)+1
                        gas_possible|=item['id']==157
                    else:upgrades[key]=level
        if limited and gas_cost:
            issue('GAS_LIMIT','review','가스 목표량과 후속 운영을 함께 확인하세요','가스 제한 명령의 실제 잔고·소비 시점은 정적 순서 검사로 확정할 수 없습니다.',name)
        used=[m for m,v in p['matchups'].items() if v['fixed'] and v['opening']==name]
        if not used and name not in original['Strategy']['Strategies']:
            issue('UNSELECTED_BUILD','review','복사한 빌드가 종족전에 고정되지 않았습니다','편집한 빌드를 사용하려면 해당 종족전의 고정 선택도 확인하세요.',name)
    for s,k,label,kind,low,high,hint in M.FIELDS:
        if p['config'][s][k]==original[s][k]:continue
        groups=(['economy','production','placement'] if s=='Macro' else ['combat','scouting'] if s=='Micro' else ['scouting','combat','economy'])
        impact(label,groups)
        if k in ('BuildingSpacing','PylonSpacing'):
            issue('PLACEMENT','review','건물 간격 변경은 길찾기와 전력에 영향을 줍니다','같은 맵·시작 위치에서 통로와 건설 실패, 파일런 파괴 후 생산을 확인하세요.',label)
        if k=='ProductionJamFrameLimit' and p['config'][s][k]<original[s][k]:
            issue('EARLY_REPLAN','review','생산 재계획이 더 빨라집니다','자원 부족으로 정상 대기 중인 오프닝을 너무 일찍 포기하는지 확인하세요.',label)
    for matchup,choice in p['matchups'].items():
        if choice['fixed']:impact(matchup+' 고정 오프닝',['production','scouting','placement','combat'])
        if race_value(p['config'],'Macro','WorkersPerRefinery')==0:
            scope=dict(matchup=matchup,map='',opening=choice['opening'] if choice['fixed'] else '')
            restores=[r for r in p['rules'] if r['enabled'] and r['actions'].get('gasWorkers',0)>0 and covers_scope(r,scope) and feasible(r)]
            issue('ZERO_GAS','review' if restores else 'error','가스 일꾼 0명이 후속 테크를 막을 수 있습니다','전체 적용 범위를 포함하는 가스 복구 규칙이 있습니다. 실제 조건 도달·발동 시점은 경기 검증이 필요합니다.' if restores else '이 종족전의 모든 맵·선택 빌드를 포함하는 유효한 가스 재개 규칙이 없습니다. 가스 일꾼 수 또는 복구 조건과 범위를 함께 수정하세요.',matchup)

    rules=[r for r in p['rules'] if r['enabled']]
    for i,r in enumerate(rules):
        title=r.get('name',r['id']);where='규칙 · '+title
        for action in r['actions']:impact(title+' / '+M.ACTIONS[action][0],LINKS[action])
        if any(lo>hi for lo,hi in bounds(r).values()):
            issue('IMPOSSIBLE_CONDITION','error','동시에 만족할 수 없는 조건','같은 정보에 모순되는 범위가 있습니다.',where)
        if r['actions'].get('gasWorkers')==0:
            restores=[a for a in rules[:i] if covers_scope(a,r) and feasible(a) and a['actions'].get('gasWorkers',0)>0]
            severity='error' if r['mode']=='once' and not restores else 'review'
            issue('RULE_GAS_STOP',severity,'가스 중단 규칙과 재개 경로를 확인하세요','한 번 충족하면 채취가 계속 0명입니다. 중단하는 모든 범위를 포함하는 상위 재개 규칙이 없으면 후속 테크가 막힙니다.' if severity=='error' else '조건 해제 또는 우선 재개 규칙이 테크 생산 전에 작동하는지 확인하세요.',where)
        if r['mode']=='once' and any(c['field'] in ('enemyNearBase','enemyVisibleArmy','enemyCloakKnown') or c['field'].startswith('visible_') for c in r['conditions']):
            issue('LATCHED_REACTION','review','적이 사라져도 대응이 유지됩니다','일시적인 적 상황에 경기 내내 유지되는 행동을 붙였습니다. 해제 방식과 정상 운영 복귀를 확인하세요.',where)
        if r['actions'].get('aggression')==1:
            issue('ATTACK_DEFENSE','review','출발 조건과 방어·증원·테크를 함께 확인하세요','공격 시각은 순정의 전진 러시 종료와 후속 테크 전환에도 쓰입니다. 본진 방어, 첫 출발, 후속 합류, 테크 전환을 함께 확인하세요.',where)
        if r['actions'].get('retreatScore',0)<0 or r['actions'].get('retreatHoldFrames',48)<24:
            issue('RETREAT_RISK','review','불리한 교전 또는 공격·후퇴 반복 가능성','병력 생존과 후퇴 후 재진입을 함께 확인하세요.',where)
        for b in rules[i+1:]:
            shared=[k for k in r['actions'].keys()&b['actions'].keys() if r['actions'][k]!=b['actions'][k]]
            if not shared or not scoped_overlap(r,b):continue
            overlap=can_overlap(r,b)
            if not overlap and r['mode']!='once' and b['mode']!='once':continue
            intentional=b['id'] in r.get('overrides',[])
            if not overlap:
                issue('LATCH_PRIORITY','review','한 번 발동한 규칙과 이후 규칙의 우선순위',title+'가 유지되면 '+b.get('name',b['id'])+'보다 먼저 적용됩니다. 의도한 전환인지 확인하세요.',where)
            else:
                issue('RULE_CONFLICT','review' if intentional else 'error','같은 상황에서 서로 다른 행동을 지시합니다',title+' / '+b.get('name',b['id'])+': '+', '.join(M.ACTIONS[k][0] for k in shared)+(' — 위쪽 규칙 우선으로 명시됨.' if intentional else ' — 한쪽 조건을 나누거나 의도한 우선 관계를 명시하세요.'),where,None if intentional else {'type':'priority','higher':r['id'],'lower':b['id'],'label':'이 상황은 위쪽 규칙 우선으로 명시'})
    # Collapse repeated supply/prerequisite findings at the same source row.
    issues=list({x['id']:x for x in issues}.values())
    impacts=list({json.dumps(x,sort_keys=True):x for x in impacts}.values())
    active=p['id']!='baseline' and p['enabled']
    errors=sum(x['severity']=='error' for x in issues)
    affected=list(dict.fromkeys(g for item in impacts for g in item['areas']))
    return dict(version=VERSION,profileFingerprint=fingerprint(p),checkerSha256=digest(ROOT/'build/native-check/Release/nnb-build-catalog.exe') if names else None,active=active,issues=issues,impacts=impacts,transitions=transitions,
                areas=[dict(id=g,label=GROUPS[g][0],connection=GROUPS[g][1],verify=GROUPS[g][2]) for g in affected],
                blocked=active and errors>0,status='blocked' if active and errors else 'candidate' if active else 'baseline',
                errors=errors,reviews=sum(x['severity']=='review' for x in issues),
                gameplayValidated=False,productionEligible=False,
                explanation='정적 연결 검사입니다. 건설 시간·잔고·이동·전투 성능은 실제 경기 비교 전에는 검증되지 않습니다.')


def repair_dependencies(p,name):
    names,ids=catalog();rows=list(p['config']['Strategy']['Strategies'][name]['OpeningBuildOrder'])
    out=[];counts={64:4,154:1};changes=[];levels={}
    def ensure(item,trail=()):
        req,cost=prerequisites(item,levels.get(canonical(item['name']),0)+1)
        if cost['gas'] and not counts.get(157):req[157]=1
        for id,n in req.items():
            if counts.get(id,0)>=n:continue
            if id in trail or id not in ids:raise ValueError('자동으로 정리할 수 없는 선행 관계입니다')
            needed=ids[id];ensure(needed,trail+(id,))
            while counts.get(id,0)<n:
                label=needed['name'].replace('Protoss_','').replace('_',' ')
                found=None
                for j,row in enumerate(rows):
                    count,parts=parse_step(row)
                    if count==1 and len(parts)==1 and names.get(parts[0][0],{}).get('id')==id:found=j;break
                value=rows.pop(found) if found is not None else label
                out.append(value);counts[id]=counts.get(id,0)+1
                changes.append(('앞으로 이동: ' if found is not None else '추가: ')+value)
    while rows:
        row=rows.pop(0);count,parts=parse_step(row)
        for unused in range(count):
            for key,place in parts:
                if key.startswith('go '):continue
                item=names[key];ensure(item)
                if item['kind']=='unit':counts[item['id']]=counts.get(item['id'],0)+1
                else:levels[canonical(item['name'])]=levels.get(canonical(item['name']),0)+1
        out.append(row)
    p['config']['Strategy']['Strategies'][name]['OpeningBuildOrder']=out
    return changes


def propose(profile,issue_id):
    p=copy.deepcopy(profile);report=review(p)
    issue=next((x for x in report['issues'] if x['id']==issue_id),None)
    if not issue or not issue.get('fix'):raise ValueError('내용이 바뀌었습니다. 연결 검사를 다시 실행하세요.')
    fix=issue['fix']
    if fix['type']=='dependencies':changes=repair_dependencies(p,fix['build'])
    else:
        r=next(r for r in p['rules'] if r['id']==fix['higher'])
        lower=next(r for r in p['rules'] if r['id']==fix['lower'])
        r.setdefault('overrides',[]).append(fix['lower']);changes=['충돌 시 '+r.get('name',r['id'])+'를 '+lower.get('name',lower['id'])+'보다 우선 적용']
    import editor_model as M
    M.validate(p)
    build_changes=[dict(name=name,before=b['OpeningBuildOrder'],after=p['config']['Strategy']['Strategies'][name]['OpeningBuildOrder'])
                   for name,b in profile['config']['Strategy']['Strategies'].items()
                   if b['OpeningBuildOrder']!=p['config']['Strategy']['Strategies'][name]['OpeningBuildOrder']]
    return dict(profile=p,changes=changes,buildChanges=build_changes,report=review(p))
