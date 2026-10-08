const OL=OpeningLanguage;
let stepEditor=-1,stepDraft=null,stepOwner='';
function buildLabel(id){
  if(p.buildLabels?.[id])return p.buildLabels[id];
  if(OL.builds[id])return OL.builds[id][0];
  const custom=Object.keys(p.config.Strategy.Strategies).filter(k=>!OL.builds[k]&&p.config.Strategy.Strategies[k].Race==='Protoss');
  return '내 빌드 '+(custom.indexOf(id)+1);
}
function buildDescription(id){
  const original=state.profiles[0].config.Strategy.Strategies[id],current=p.config.Strategy.Strategies[id];
  if(!original||JSON.stringify(original)!==JSON.stringify(current))return '직접 수정한 빌드입니다. 아래 생산 순서와 연결 영향 검사에서 현재 내용을 확인하세요.';
  return OL.builds[id]?.[1]||'아래 순서로 생산과 행동을 계획합니다.';
}
function openingChoices(value){
  const choices=OL.choices(state.catalog),groups=[...new Set(choices.map(x=>x.kind))];
  return groups.map(g=>`<optgroup label="${g}">${choices.filter(x=>x.kind===g).map(x=>opt(x.key,x.label,value)).join('')}</optgroup>`).join('');
}
function partFields(part,j,prefix){return `<div class="opening-fields"><label>무엇을 할까요?<select data-part="${j}|key" id="${prefix}-item-${j}" aria-label="${stepEditor+1}단계 ${j+1}번째 행동" ${readOnly()?'disabled':''}>${openingChoices(part.key)}</select></label>
  ${part.building?`<label>건설 위치<select data-part="${j}|location">${Object.entries(OL.locations).map(([k,v])=>opt(k,v,part.location)).join('')}</select></label>`:''}
  ${part.argument?`<label>${esc(part.argument)}<input type="number" min="0" step="${part.key==='go aggressive at'?'any':'1'}" data-part="${j}|amount" value="${part.amount===undefined?'':part.key==='go aggressive at'?part.amount/24:part.amount}"></label>`:''}</div><p class="small">${esc(part.description)}</p>`;}
function stepForm(){return `<div class="step-form"><h3>이 단계 수정</h3><label>이 단계의 반복 수<input id="step-count" type="number" min="1" max="100" value="${stepDraft.count}"></label>${stepDraft.parts.map((part,j)=>`<div class="step-part">${j?`<div class="row between"><b>${OL.trigger(stepDraft.parts[j-1])}</b><button data-remove-part="${j}">연결 해제</button></div>`:''}${partFields(part,j,'edit')}</div>`).join('')}
  <div class="row">${(stepDraft.parts.at(-1).building||stepDraft.parts.at(-1).upgrade)?'<button data-opening="chain">+ 이어서 할 행동</button>':''}<button class="primary" data-opening="apply">수정한 단계 반영</button><button data-opening="cancel">취소</button></div></div>`;}
function stepRow(raw,i){let d=OL.parse(raw,state.catalog);return `<article class="opening-step" id="opening-step-${i}"><div class="step-number">${i+1}<small>단계</small></div><div class="step-content">
  ${d.parts.map((part,j)=>`${j?`<p class="step-trigger">↳ ${OL.trigger(d.parts[j-1])}</p>`:''}<div class="row"><span class="pill">${part.kind}</span><strong>${esc(OL.actionTitle(part,d.count))}</strong></div><p class="small step-help">${esc(part.description)}</p>`).join('')}
  ${i===0?'<p class="small">시작할 때 가진 프로브 4기에서 출발합니다. “4기 생산”은 4기를 더 만들라는 뜻입니다.</p>':''}
  <details class="raw-step"><summary>고급 편집 · 원문 명령</summary><label>봇이 읽는 명령<input data-step="${i}" aria-label="${i+1}단계 원문 명령" value="${esc(raw)}" ${readOnly()?'readonly':''}></label><p class="small">원문을 직접 바꾼 경우 연결 영향 검사로 지원 여부를 확인하세요.</p></details>
  ${stepEditor===i?stepForm():''}</div><div class="step-buttons"><button data-edit-step="${i}" aria-label="${i+1}단계 수정" ${readOnly()||d.parts.some(x=>x.unknown)?'disabled':''}>수정</button><button data-step-up="${i}" aria-label="${i+1}단계 위로" ${readOnly()||i===0?'disabled':''}>↑</button><button data-step-down="${i}" aria-label="${i+1}단계 아래로" ${readOnly()?'disabled':''}>↓</button><button data-step-delete="${i}" aria-label="${i+1}단계 삭제" ${readOnly()?'disabled':''}>×</button></div></article>`;}
function easyBuildControls(){return `<div class="note"><h3>새 단계 추가</h3><div class="opening-fields"><label>무엇을 할까요?<select id="easy-item">${openingChoices('probe')}</select></label><label>몇 기 / 몇 개?<input id="easy-count" type="number" min="1" max="100" value="1"></label><label id="easy-place-label" hidden>건설 위치<select id="easy-location">${Object.entries(OL.locations).map(([k,v])=>opt(k,v,'')).join('')}</select></label><label id="easy-amount-label" hidden><span id="easy-amount-title"></span><input id="easy-amount" type="number" min="0" value="0"></label><button data-opening="add" ${readOnly()?'disabled':''}>맨 아래에 단계 추가</button></div><p id="easy-description" class="small">일꾼을 추가 생산합니다. 건물·업그레이드·정찰도 목록에서 고를 수 있습니다.</p></div>`;}
function openingView(){
  let m=p.matchups[tab];if(!opening||!p.config.Strategy.Strategies[opening])opening=m.opening;
  if(stepOwner!==p.id+'|'+opening){stepEditor=-1;stepDraft=null;}
  let b=p.config.Strategy.Strategies[opening];
  return intro('오프닝 만들기','무엇을, 어떤 순서로 할까요?','빌드를 고르고 각 단계를 한국어로 수정하세요. 순서 번호와 실제 게임 인구수는 서로 다릅니다.')+note()+`
  <div class="tabs">${[['PvP','프로토스 상대'],['PvT','테란 상대'],['PvZ','저그 상대']].map(([t,label])=>`<button data-matchup="${t}" class="${tab===t?'active':''}">${label}</button>`).join('')}</div>
  <section class="box"><h2>이 종족전에서 사용할 빌드</h2><select id="chosen-opening" aria-label="종족전 사용 빌드" ${readOnly()?'disabled':''}>${options(m.opening)}</select><label><input id="fixed" type="checkbox" ${m.fixed?'checked':''} ${readOnly()?'disabled':''}> 이 빌드로 고정하기</label><p class="small">끄면 순정 봇이 빌드를 고릅니다. 아래에서 다른 빌드를 열어 보는 것만으로 사용 빌드가 바뀌지는 않습니다.</p></section>
  <section class="box"><div class="row between"><label>열어서 수정할 빌드<select id="build-select">${options(opening)}</select></label><button data-act="copy-build" ${readOnly()?'disabled':''}>내 빌드로 복사</button></div>
  <div class="build-explanation"><h2>${esc(buildLabel(opening))}</h2><p>${esc(buildDescription(opening))}</p></div>
  <div class="opening-fields"><label>내가 알아보기 쉬운 이름<input id="build-label" maxlength="80" value="${esc(buildLabel(opening))}" ${readOnly()?'disabled':''}></label><label>이 순서가 끝난 뒤의 기본 운영<select id="group" ${readOnly()?'disabled':''}>${[['zealots','질럿 중심 압박'],['dragoons','드라군 중심'],['dark templar','다크 템플러 견제'],['carriers','캐리어 중심'],['drop','수송선으로 병력 투입 (드롭)']].map(([k,v])=>opt(k,v,b.OpeningGroup)).join('')}</select></label></div>
  <p class="small">후속 운영에는 정찰 결과에 따른 순정 대응도 남습니다. <a href="#safety">연결 영향 검사에서 확인하기 →</a></p>
  <details class="raw-step"><summary>고급 정보 · 원래 빌드 이름</summary><code>${esc(opening)}</code></details>
  <div class="note"><b>1단계 → 2단계 → 3단계는 실행 순서입니다.</b><br>“3단계”가 인구수 3이라는 뜻은 아닙니다. 병력은 생산을 시작하며 다음 항목으로 넘어갈 수 있습니다. 건설·연구 뒤의 연결 행동은 각 단계에 적힌 시점에 실행합니다.</div>
  <div id="steps">${b.OpeningBuildOrder.map(stepRow).join('')}</div>${easyBuildControls()}</section>`;
}
document.addEventListener('change',e=>{
  let t=e.target;try{
    if(t.id==='easy-item'){
      let part=OL.item(t.value,state.catalog);$('#easy-count').disabled=part.command||part.upgrade;
      $('#easy-place-label').hidden=!part.building;$('#easy-amount-label').hidden=!part.argument;
      $('#easy-amount-title').textContent=part.argument||'';$('#easy-description').textContent=part.description;return;
    }
    if(readOnly())return;
    if(t.id==='build-label'){p.buildLabels??={};p.buildLabels[opening]=t.value.trim()||buildLabel(opening);edit();return;}
    if(t.id==='step-count'&&stepDraft){stepDraft.count=Number(t.value);return;}
    if(t.dataset.part&&stepDraft){let[j,key]=t.dataset.part.split('|'),old=stepDraft.parts[j];
      if(key==='key')stepDraft.parts[j]={...OL.item(t.value,state.catalog),location:'',amount:0};
      else old[key]=key==='amount'?(old.key==='go aggressive at'?Math.round(Number(t.value)*24):Number(t.value)):t.value;
      if(key==='key')route();return;
    }
    if(t.dataset.step!==undefined){stepEditor=-1;stepDraft=null;route();}
    if(['build-select','chosen-opening'].includes(t.id)){stepEditor=-1;stepDraft=null;route();}
  }catch(err){toast(err.message);}
});
document.addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b)return;const d=b.dataset;
  try{
    if(readOnly())return;
    if(d.editStep!==undefined){stepOwner=p.id+'|'+opening;stepEditor=+d.editStep;stepDraft=OL.parse(p.config.Strategy.Strategies[opening].OpeningBuildOrder[stepEditor],state.catalog);route();return;}
    if(d.opening==='cancel'){stepEditor=-1;stepDraft=null;route();return;}
    if(d.opening==='chain'){stepDraft.parts.push({...OL.item('go scout while safe',state.catalog),location:''});route();return;}
    if(d.removePart!==undefined){stepDraft.parts.splice(+d.removePart,1);route();return;}
    if(d.opening==='apply'){p.config.Strategy.Strategies[opening].OpeningBuildOrder[stepEditor]=OL.serialize(stepDraft);stepEditor=-1;stepDraft=null;edit();route();return;}
    if(d.opening==='add'){
      const part={...OL.item($('#easy-item').value,state.catalog),location:$('#easy-location').value,amount:Number($('#easy-amount').value)};
      if(part.key==='go aggressive at')part.amount=Math.round(part.amount*24);
      const count=part.command||part.upgrade?1:Number($('#easy-count').value);
      p.config.Strategy.Strategies[opening].OpeningBuildOrder.push(OL.serialize({parts:[part],count}));edit();route();toast('맨 아래에 새 단계를 추가했습니다. 위아래 화살표로 위치를 바꿀 수 있습니다.');return;
    }
    if(d.matchup||d.stepUp!==undefined||d.stepDown!==undefined||d.stepDelete!==undefined||d.act==='copy-build'){stepEditor=-1;stepDraft=null;route();}
  }catch(err){toast(err.message);}
});
