/* Cross-system review uses server results for the current draft, never a green gameplay badge. */
names.safety='연결 영향 검사';
let safetyReport=null,repairPlan=null;

views.safety=()=>intro('CHANGE IMPACT','한 곳을 바꿀 때, 함께 확인하기','생산·자원·정찰·교전·건설의 연결을 검사합니다. 확인된 충돌은 시험본 생성을 막고, 경기에서 확인해야 할 부분은 따로 표시합니다.')+note()+`
<section class="box"><div class="row between"><h2>현재 초안 검사</h2><button data-safety="refresh">다시 검사</button></div><div id="safety-result" aria-live="polite">연결된 영향을 확인하고 있습니다.</div></section>
<section class="box" id="repair-panel" hidden></section>
<section class="box"><h2>반영하는 순서</h2><div class="diagram"><span>초안 저장</span><b>→</b><span>연결 문제 해결</span><b>→</b><span>오프라인 시험본</span><b>→</b><span>순정과 경기 비교</span></div><p class="small">정적 검사 통과는 실력 유지의 증명이 아닙니다. 실제 게임에서 생산·정찰·전투가 함께 정상인지 검증할 때까지 실전 사용 검증은 미완료입니다.</p></section>`;

const originalReview=views.review;
views.review=()=>originalReview().replace('<section class="box">',`<section class="box"><h2>다른 부분에 미치는 영향</h2><div id="safety-summary" aria-live="polite">연결 검사 중…</div><button data-go="safety">문제와 연결된 영향 보기 →</button></section><section class="box">`)+`
<section class="box"><h2>이전 저장본으로 되돌리기</h2><p class="small">저장 전의 버전을 보존합니다. 복원하면 현재 내용도 기록한 뒤 새 저장 번호로 복원하며, 실행 중인 게임은 바꾸지 않습니다.</p><div id="history-controls">저장 기록을 확인하고 있습니다.</div></section>`;

function safetyHTML(r){
  const title=r.blocked?`해결할 문제 ${r.errors}개 · 시험본 생성 중단`:r.active?'정적 오류 없음 · 경기 비교 전 시험 후보':'현재 적용: 순정 기준본';
  const inactive=!r.active&&r.issues.length?'<p class="small">꺼진 프로필의 편집 내용도 아래에서 검사합니다. 현재 생성 대상은 순정입니다.</p>':'';
  return `<div class="note ${r.blocked?'warning':''}"><b>${title}</b><br>${esc(r.explanation)}</div>${inactive}
  ${r.issues.length?r.issues.map(x=>`<div class="safety-issue ${x.severity}"><div class="row between"><h3>${esc(x.title)}</h3><span class="pill ${x.severity==='error'?'amber':''}">${x.severity==='error'?'해결 필요':'경기 확인 필요'}</span></div><p class="small"><b>${esc(x.where)}</b><br>${esc(translate(x.detail))}</p>${x.fix&&!readOnly()?`<button class="secondary" data-fix-preview="${x.id}">${esc(x.fix.label)} · 미리보기</button>`:''}</div>`).join(''):'<p>현재 초안에서 지원하는 검사 항목의 충돌을 찾지 못했습니다.</p>'}
  <h2 style="margin-top:28px">변경이 이어지는 곳</h2>
  ${r.impacts.length?`<div class="impact-list">${r.impacts.map(x=>`<div class="list-line"><strong>${esc(x.change)}</strong><div class="row" style="margin-top:8px">${x.areas.map(g=>`<span class="pill">${esc(r.areas.find(a=>a.id===g).label)}</span>`).join('')}</div></div>`).join('')}</div>`:'<p class="small">순정에서 바뀐 동작이 없습니다.</p>'}
  <h2 style="margin-top:28px">오프닝 뒤에 남아 있는 순정 판단</h2>${r.transitions.map(t=>`<div class="list-line"><h3>${esc(t.build)}</h3><p class="small">${esc(t.behavior)}</p></div>`).join('')||'<p class="small">고정하거나 수정한 오프닝이 없습니다.</p>'}<h2 style="margin-top:28px">같은 맵·시작 위치에서 비교할 항목</h2>
  ${r.areas.map(a=>`<div class="list-line"><div class="row between"><h3>${esc(a.label)}</h3><span class="pill amber">게임 검증 미완료</span></div><p class="small">${esc(a.connection)}<br>확인: ${esc(a.verify)}</p></div>`).join('')||'<p class="small">순정 자체의 경기 기준부터 측정해야 합니다.</p>'}`;
}

async function loadSafety(){
  const seq=editVersion,id=p.id;
  try{
    const r=await api('/api/safety',{profile:p});
    if(seq!==editVersion||id!==p.id)return;
    safetyReport=r;
    if($('#safety-result'))$('#safety-result').innerHTML=safetyHTML(r);
    if($('#safety-summary'))$('#safety-summary').innerHTML=`<p><b>${r.blocked?'문제 '+r.errors+'개 · 시험본 생성 중단':r.active?'정적 오류 없음 · 오프라인 시험 후보':'순정 기준본 생성'}</b><br>${r.areas.map(a=>esc(a.label)).join(' · ')}<br><span class="small">경기에서 확인할 항목 ${r.reviews}개. 실제 경기 성능은 아직 검증되지 않았습니다.</span></p>`;
  }catch(e){for(const selector of ['#safety-result','#safety-summary'])if($(selector))$(selector).textContent='검사를 완료하지 못했습니다: '+e.message;}
}

async function loadHistory(){
  const id=p.id;
  try{const rows=await api('/api/history?id='+encodeURIComponent(id));if(id!==p.id||!$('#history-controls'))return;
    $('#history-controls').innerHTML=rows.length?`<div class="row"><select id="restore-version" aria-label="되돌릴 저장본">${rows.map(x=>opt(String(x.revision),'저장 '+x.revision+' · '+x.name,'' )).join('')}</select><button data-safety="restore" ${readOnly()?'disabled':''}>선택한 저장본 복원</button></div>`:'<p class="small">아직 이전 저장본이 없습니다. 다음 저장부터 현재 버전이 보존됩니다.</p>';
  }catch(e){if($('#history-controls'))$('#history-controls').textContent=e.message;}
}

document.addEventListener('click',async e=>{
  const b=e.target.closest('button');if(!b)return;
  try{
    if(b.dataset.safety==='refresh'){await loadSafety();return;}
    if(b.dataset.fixPreview){
      const seq=editVersion;
      const result=await api('/api/repair-preview',{profile:p,issueId:b.dataset.fixPreview});
      if(seq!==editVersion)throw Error('초안이 바뀌었습니다. 다시 검사하세요.');
      repairPlan={...result,editVersion:seq};const panel=$('#repair-panel');panel.hidden=false;
      panel.innerHTML=`<h2>함께 바꿀 내용</h2><ul>${result.changes.map(x=>`<li>${esc(translate(x))}</li>`).join('')}</ul>${result.buildChanges.map(c=>`<details><summary>${esc(c.name)} · 수정 전후 생산 순서 보기</summary><div class="grid"><div><h3>수정 전</h3><ol>${c.before.map(s=>`<li>${esc(translate(s))}</li>`).join('')}</ol></div><div><h3>수정 후</h3><ol>${c.after.map(s=>`<li>${esc(translate(s))}</li>`).join('')}</ol></div></div></details>`).join('')}<div class="note warning">선행 순서를 맞추면 자원 사용과 타이밍도 달라집니다. 필요한 건물을 추가하거나 이동하므로 전체 건물 수도 확인하세요. 고수 빌드를 자동으로 완성한 것이 아니며, 수정 후 다시 검사하고 경기에서 비교해야 합니다.</div><div class="row"><button class="primary" data-safety="apply">이 내용을 초안에 반영</button><button data-safety="cancel">취소</button></div>`;
      panel.scrollIntoView({block:'nearest',behavior:'smooth'});return;
    }
    if(b.dataset.safety==='apply'){
      if(!repairPlan||repairPlan.editVersion!==editVersion)throw Error('초안이 바뀌었습니다. 다시 검사하세요.');
      p=repairPlan.profile;repairPlan=null;edit();route();toast('연결된 변경을 초안에 반영했습니다. 아직 저장·게임 적용 전입니다.');return;
    }
    if(b.dataset.safety==='cancel'){repairPlan=null;$('#repair-panel').hidden=true;return;}
    if(b.dataset.safety==='restore'){
      const rev=Number($('#restore-version').value);if(dirty)await save();
      const result=await api('/api/restore',{id:p.id,revision:rev,expectedRevision:p.revision});
      await refresh(result.id);toast('이전 내용을 새 저장본으로 복원했습니다. 복원 전 내용도 보존했습니다.');
    }
  }catch(e){toast(e.message);}
});
