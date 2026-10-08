let judgmentTab='native';
const customRulesView=views.rules;
const groupEffects={
  proxy:'전진 러시 판단으로 유지됩니다. 정찰 기록과 다음 경기의 오프닝 선택에도 쓰입니다.',
  worker:'일꾼 러시 판단을 유지하며, 다음 추정 검사에서 더 빠른 위협을 확인할 수 있습니다.',
  fast:'안전 정찰 중단·가스 견제 취소, 조건에 따른 일꾼·캐논 방어 판단에 영향을 줍니다.',
  notFast:'아직 구체적인 전략을 못 찾았을 때의 임시 판단입니다. 뒤에서 다른 전략으로 바뀔 수 있습니다.',
  heavy:'가스 견제를 중단하고, 방어가 필요한 상황에서는 시간에 따라 캐논 수를 늘리는 기준이 됩니다.',
  hydra:'해당 방어 조건이 맞으면 캐논 수를 늘리는 판단에 쓰입니다. 모든 상황에서 바로 캐논을 짓는 명령은 아닙니다.',
  wall:'진행 중인 질럿·전진 러시를 끝내고 후속 테크로 전환하는 판단에 쓰입니다.',
  dark:'정찰 상태·은폐 예상 시점과 함께 옵저버·캐논을 준비하는 판단에 쓰입니다.',
};
const decisionCards=[
  ['불리한 싸움에서 후퇴','전투 계산 점수가 0보다 낮으면 후퇴합니다. 후퇴 직후에는 기본 2초 동안 재공격을 기다립니다. 길목·기습 등 다른 순정 예외도 먼저 검사합니다.','retreat'],
  ['일꾼이 많아지면 확장 검토','쉬는 일꾼이 10기를 넘거나 프로브 수가 넥서스 수 × 18을 넘으면 확장 후보로 봅니다. 미완성 넥서스·건설 계획과 다른 자원·안전 조건도 함께 고려합니다.','expand'],
  ['생산이 막혔을 때 재계획','선행 조건이 없는 생산은 대기열에서 빠질 수 있습니다. 생산 정체 대기 시간·선행 건물·가스가 함께 영향을 줍니다. 아래 기본 수치와 연결 영향 검사에서 확인할 수 있습니다.',''],
  ['은폐 유닛과 공중 유닛 대응','은폐 전투 유닛이나 다크 템플러 예상·정찰 상태를 보고 탐지 수단을 준비합니다. 저그 공중 전투 유닛 확인 시에는 커세어를 고려하는 순정 대응도 있습니다. 이 생산 분기의 전체 코드는 현재 숫자 설정으로 바꾸지 않습니다.',''],
];
function ownValue(profile,section,key){const v=profile.config[section][key];return typeof v==='object'?v.Protoss??0:v;}
function nativeFields(){return ['Macro','Micro','Strategy'].map(section=>`<details class="decision-section" ${section==='Micro'?'open':''}><summary>${{Macro:'경제·생산·건설',Micro:'교전·생존·방어',Strategy:'정찰·상대 추정'}[section]}의 순정 기준 수정</summary>${state.catalog.fields.filter(f=>f.section===section).map(f=>{
  const raw=p.config[section][f.key],race=typeof raw==='object'?'Protoss':'공통',value=ownValue(p,section,f.key),original=ownValue(state.profiles[0],section,f.key);
  return `<div class="settings-row"><div><h3>${esc(f.label)}</h3><p class="small">${esc(f.hint)} · 순정 기준: ${f.type==='bool'?(original?'사용':'사용 안 함'):original}</p></div><label class="decision-value">내 기준 <input aria-label="${esc(f.label+' 내 기준')}" data-setting="${section}|${f.key}|${race}" type="${f.type==='bool'?'checkbox':'number'}" ${f.type==='bool'?(value?'checked':''):`value="${value}" min="${f.min}" max="${f.max}" step="${f.type==='float'?'any':'1'}"`} ${readOnly()?'disabled':''}></label></div>`;
}).join('')}</details>`).join('');}
function nativeJudgments(){return `<section class="box"><h2>순정은 이런 기준으로 판단합니다</h2><p>규칙 목록에 없던 판단은 대부분 봇 내부에 들어 있습니다. 아래에서 원래 기준을 보고 수정하거나, 그 판단에 덧붙일 대응을 만들 수 있습니다.</p><div class="decision-list">${decisionCards.map(([title,desc,template])=>`<div class="list-line"><h3>${title}</h3><p>${desc}</p>${template?`<button data-decision-template="${template}" ${readOnly()?'disabled':''}>이 기준을 바꾸는 대응 만들기</button>`:'<span class="small muted">동작 설명 · 관련 기본 수치는 아래에서 수정</span>'}</div>`).join('')}</div></section><section class="box"><h2>기존 설정 직접 수정</h2><p class="small">NNB의 프로토스 플레이에 적용되는 기준입니다. 운영과 컨트롤 메뉴와 같은 설정을 수정합니다.</p>${nativeFields()}</section>`;}
function recognitionView(){return `<section class="box"><div class="row between"><div><h2>정찰 정보를 보고 상대 전략 추정</h2><p>정찰 → 관측한 병력·건물과 추정 시각 → 상대 전략 → 기존 방어·테크 판단</p></div><label><input type="checkbox" id="recognizer-enabled" ${ownValue(p,'Strategy','UsePlanRecognizer')?'checked':''} ${readOnly()?'disabled':''}> 전략 추정 사용</label></div><p class="small">실시간 경기 화면이 아닌 저장된 판단 기준입니다. 보지 못한 적 정보를 가져오지 않습니다. 아래 순서대로 검사하며, ‘확정’한 판단은 그 경기에서 다시 바꾸지 않습니다.</p><p class="small">빠른 러시의 시각은 단순 발견 시각이 아닙니다. 건물의 건설 시간, 병력의 이동 거리·속도를 이용한 추정치이며 정찰이 늦으면 오차가 생깁니다.</p></section>
  ${state.catalog.judgments.map((g,i)=>`<section class="box"><div class="row between"><h2>${i===0?'검사 범위':i+'. '+g.label}</h2>${g.id!=='window'?`<span class="pill">${g.fixed?'충족하면 판단 확정':'다시 판단할 수 있음'}</span>`:''}</div><p>${esc(g.description)}</p>${groupEffects[g.id]?`<div class="note"><b>이 판단이 바꾸는 것</b><br>${esc(groupEffects[g.id])}</div>`:''}<div class="recognition-fields">${g.fields.map(f=>{
    let value=p.recognition?.[f.key]??f.default;const shown=v=>f.unit==='frames'?Number((v/24).toFixed(3)):v;
    return `<label>${esc(f.label)}${f.unit==='frames'?' (게임 시간·초)':''}<input aria-label="${esc(g.label+' '+f.label)}" data-recognition="${f.key}" type="${f.unit==='bool'?'checkbox':'number'}" ${f.unit==='bool'?(value?'checked':''):`value="${shown(value)}" min="${shown(f.min)}" max="${shown(f.max)}" step="${f.unit==='frames'?'any':'1'}"`} ${readOnly()?'disabled':''}><span class="small muted">순정: ${f.unit==='bool'?'사용':shown(f.default)+(f.unit==='frames'?'초':'')}</span></label>`;
  }).join('')}</div><div class="row" style="margin-top:18px"><button data-reset-recognition="${g.id}" aria-label="${esc(g.label)} 순정 기준으로 복원" ${readOnly()?'disabled':''}>이 판단을 순정 기준으로</button>${['fast','hydra','dark'].includes(g.id)?`<button data-decision-template="${g.id}" aria-label="${esc(g.label)} 방어 대응 추가" ${readOnly()?'disabled':''}>이렇게 추정하면 방어하도록 추가</button>`:''}</div></section>`).join('')}
  <section class="box"><h2>코드는 있지만 현재 사용하지 않는 추정</h2><p>팩토리 테크 · 방어를 갖춘 확장 · 무방비 확장 · 수비에 집중한 운영</p><p class="small">순정 코드가 이 분기 앞에서 종료하므로 현재의 정찰 추정에는 쓰이지 않습니다. 이름만 있는 기능을 작동 중인 판단으로 표시하거나, 연결된 대응 검증 없이 켜지 않습니다.</p></section>`;}
function responseChoices(){return `<section class="box"><h2>빈 규칙 대신, 예시에서 시작하세요</h2><div class="row">${[['fast','빠른 러시로 추정 → 방어'],['hydra','히드라 준비로 추정 → 방어'],['pressure','본진 근처 적 → 방어'],['retreat','전투 후퇴 기준 바꾸기'],['expand','확장 검토 기준 바꾸기']].map(([k,v])=>`<button data-decision-template="${k}" ${readOnly()?'disabled':''}>${v}</button>`).join('')}</div><p class="small">예시는 꺼진 상태로 추가됩니다. 조건과 값을 확인한 뒤 ‘사용’을 켜세요. 같은 행동은 위쪽 규칙이 먼저 적용되며 연결 검사에서 충돌을 확인합니다.</p></section>`;}
views.rules=()=>intro('판단 살펴보기','순정의 생각을 보고, 바꿔 보세요','먼저 원래 기준을 살펴보고 필요한 부분을 수정하세요. 새 대응은 준비된 예시에서 시작할 수 있습니다.')+note()+`<div class="tabs">${[['native','순정 판단과 기본 기준'],['recognition','정찰로 전략 추정'],['custom','내 추가 대응 ('+p.rules.length+')']].map(([k,v])=>`<button data-judgment-tab="${k}" class="${judgmentTab===k?'active':''}">${v}</button>`).join('')}</div>`+(judgmentTab==='native'?nativeJudgments():judgmentTab==='recognition'?recognitionView():responseChoices()+customRulesView());
document.addEventListener('change',e=>{
  if(readOnly())return;const t=e.target;
  if(t.id==='recognizer-enabled'){let v=p.config.Strategy.UsePlanRecognizer;if(typeof v==='object')v.Protoss=t.checked;else p.config.Strategy.UsePlanRecognizer=t.checked;edit();return;}
  if(t.dataset.recognition){const key=t.dataset.recognition,f=state.catalog.judgments.flatMap(g=>g.fields).find(f=>f.key===key);let value=f.unit==='bool'?Number(t.checked):Number(t.value);if(f.unit==='frames')value=Math.round(value*24);p.recognition??={};p.recognition[key]=value;edit();}
});
document.addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b)return;const d=b.dataset;
  if(d.judgmentTab){judgmentTab=d.judgmentTab;route();return;}
  if(readOnly())return;
  if(d.resetRecognition){for(const f of state.catalog.judgments.find(g=>g.id===d.resetRecognition).fields)if(p.recognition)delete p.recognition[f.key];edit();route();return;}
  if(d.decisionTemplate){const key=d.decisionTemplate,r=newRule();r.enabled=false;r.matchup='';r.opening='';
    const templates={
      fast:['빠른 러시로 추정하면 방어','plan_fast',1,{aggression:0}],
      hydra:['히드라 공격 준비로 추정하면 방어','plan_hydra',1,{aggression:0}],
      dark:['다크 템플러로 추정하면 방어','plan_dark',1,{aggression:0}],
      pressure:['기지 근처 적 병력 확인 시 방어','enemyNearBase',100,{aggression:0}],
      retreat:['기본 후퇴 기준 조정','seconds',0,{retreatScore:0,retreatHoldFrames:48}],
      expand:['기본 확장 검토 기준 조정','seconds',0,{expandWorkersPerBase:18,expandIdleWorkers:10}],
    };
    const [name,field,value,actions]=templates[key];Object.assign(r,{name,mode:'while',conditions:[{field,op:field.startsWith('plan_')?'==':'>=',value}],actions,note:'순정 판단에서 만든 수정 예시입니다. 값을 조정하고 같은 맵·빌드의 리플레이 근거를 적은 뒤 사용을 켜세요. 방어 허용 설정은 탐지 유닛·캐논 생산 자체를 새로 구현하지 않습니다.'});p.rules.push(r);judgmentTab='custom';edit();route();toast('조건과 행동이 채워진 예시를 추가했습니다. 값을 확인한 뒤 사용을 켜세요.');
  }
});
