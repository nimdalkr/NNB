/* Presentation and explicit form serialization only. Reading a build never rewrites it. */
(function(root){
  const builds={
    ForgeExpandSpeedlots:['포지 확장 → 발업 질럿','입구에 포지와 캐논을 세우고 앞마당을 확보한 뒤, 이동 속도를 올린 질럿을 늘립니다.'],
    ForgeExpand4Gate2Archon:['포지 확장 → 4게이트·아칸','캐논으로 입구를 지키고 확장한 뒤 질럿과 하이 템플러를 생산하는 순서입니다.'],
    ForgeExpand5GateGoon:['포지 확장 → 5게이트 드라군','입구 방어와 앞마당 확장 후 게이트웨이를 늘려 드라군을 생산합니다.'],
    '4GateGoon':['4게이트 드라군','드라군 사거리를 업그레이드하고 게이트웨이 4개로 드라군을 생산합니다.'],
    FakeDTRush:['다크 테크를 보여준 뒤 드라군','아둔까지 건설하지만 오프닝에는 다크 템플러를 넣지 않고 드라군을 늘립니다.'],
    '2GateDTRush':['2게이트 다크 템플러 → 앞마당','게이트웨이 2개에서 다크 템플러를 생산하고 앞마당을 확장합니다.'],
    '4GateGoonWithObs':['옵저버를 갖춘 4게이트 드라군','드라군 사거리 업그레이드에 로보틱스·옵저버 생산을 더한 순서입니다.'],
    ZealotDrop:['캐논 방어 → 질럿 드롭','캐논으로 방어하면서 셔틀과 질럿을 준비합니다. 드롭은 수송선으로 병력을 옮겨 내리는 공격입니다.'],
    '10Gate25NexusFE':['10게이트 → 25넥서스 확장','먼저 게이트웨이와 드라군 사거리를 준비한 뒤 앞마당을 확장하는 순정 빌드입니다. 숫자는 원래 빌드의 이름이며 실전 인구수 보장은 아닙니다.'],
    '10-15GateGoon':['10·15게이트 드라군','게이트웨이 2개와 드라군 사거리 업그레이드를 준비합니다. 10·15는 원래 빌드 이름에 붙은 인구수 기준입니다.'],
    DTDrop:['앞마당 후 다크 템플러 드롭','드라군과 사거리 업그레이드 → 앞마당 → 다크 템플러와 셔틀 순서입니다. 셔틀은 병력을 실어 나르는 수송선입니다.'],
    '13Nexus':['13넥서스 빠른 확장','게이트웨이보다 넥서스를 먼저 짓고, 이후 게이트웨이 2개와 드라군을 준비합니다. 13은 원래 빌드 이름의 인구수 기준입니다.'],
    Turtle:['캐논·질럿으로 입구 방어 → 확장','입구 건물과 캐논·질럿을 먼저 갖춘 뒤 앞마당과 드라군을 준비합니다.'],
    ForgeExpand:['입구 방어 후 앞마당·드라군','입구에 게이트웨이·포지·캐논을 세우고 앞마당을 확보한 뒤 드라군으로 이어갑니다.'],
    '9-9GateDefensive':['9·9게이트 방어 → 질럿 공격','게이트웨이 2개에서 질럿을 모으며 방어하다가 오프닝 중 공격을 허용합니다.'],
    CannonFirst4GateGoon:['캐논 먼저 방어 → 4게이트 드라군','게이트웨이보다 포지와 캐논을 먼저 갖추고 드라군 생산으로 이어갑니다.'],
    'Proxy9-9Gate':['전진 9·9게이트 질럿','본진 밖 전진 위치에 파일런과 게이트웨이 2개를 짓고 질럿을 생산합니다.'],
    Proxy2ZealotsIntoGoons:['전진 2질럿 → 드라군','전진 게이트웨이에서 질럿 2기를 생산한 뒤 가스·코어를 올려 드라군으로 이어갑니다.'],
    ProxyDTRush:['전진 게이트 다크 템플러','전진 게이트웨이와 다크 템플러 기술을 준비하고 상대 정찰을 막는 순서입니다.'],
    PlasmaCarriers:['플라즈마 맵용 · 빠른 캐리어','빠르게 확장하며 스타게이트·플릿 비콘·캐리어를 준비합니다. 현재 시즌 맵에서는 순정이 후속 계열을 바꾸므로 연결 검사가 필요합니다.'],
    PlasmaCorsairsCarriers:['플라즈마 맵용 · 커세어 후 캐리어','확장과 스타게이트 2개를 준비해 커세어부터 생산합니다. 캐리어는 후속 운영 계열이며, 현재 시즌 맵에서는 전환을 확인해야 합니다.'],
    PlasmaProxy2Gate:['플라즈마 맵용 · 전진 2게이트','상대 본진 위치를 확인한 뒤 전진 파일런과 게이트웨이 2개를 짓습니다.'],
  };
  const upgrades={
    'singularity charge':['드라군 사거리 업그레이드','사이버네틱스 코어에서 드라군의 공격 사거리를 늘립니다.'],
    'leg enhancements':['질럿 이동 속도 업그레이드 (발업)','아둔에서 질럿의 이동 속도를 올립니다.'],
    'protoss ground weapons':['지상 유닛 공격력 업그레이드','포지에서 프로토스 지상 유닛의 공격력을 올립니다.'],
    'protoss air weapons':['공중 유닛 공격력 업그레이드','사이버네틱스 코어에서 프로토스 공중 유닛의 공격력을 올립니다.'],
    'carrier capacity':['캐리어 인터셉터 수 증가','플릿 비콘에서 캐리어가 보유할 수 있는 인터셉터 수를 늘립니다.'],
  };
  const commands={
    'go scout while safe':['안전한 동안 일꾼 정찰','일꾼을 정찰 보냅니다. 체력이 줄거나 위협을 확인하면 순정 판단에 따라 정찰을 중단합니다. 적 입구 안쪽 등 예외 상황은 순정 정찰 판단을 따릅니다.','정찰'],
    'go scout location':['상대 본진 위치 찾기','상대 본진 위치를 찾는 정찰입니다. 위치를 찾으면 가스 견제 등 남은 임무를 고려해 복귀합니다.','정찰'],
    'go scout once around':['상대 본진을 한 바퀴 정찰','정찰 일꾼으로 상대 본진을 한 바퀴 확인하는 방식입니다.','정찰'],
    'go scout if needed':['필요할 때 일꾼 정찰','상대 본진 위치를 더 확인해야 하는지 보고 일꾼 정찰을 요청합니다.','정찰'],
    'go scout':['일꾼 정찰 보내기','일꾼에게 상대 본진을 찾아 정찰하도록 요청합니다.','정찰'],
    'go aggressive':['공격 허용하기','공격 부대의 진출을 허용합니다. 위험한 교전의 후퇴와 본진 방어 판단은 계속 작동합니다.','운영'],
    'go defensive':['방어 유지하기','공격 부대의 적극적인 진출을 막고 방어하도록 설정합니다.','운영'],
    'go start gas':['가스 채취 재개','가스 채취를 허용합니다. 어시밀레이터와 배정할 일꾼이 필요합니다.','자원'],
    'go stop gas':['가스 채취 중단','가스를 캐는 일을 중단합니다. 이후 필요한 가스와 재개 시점을 함께 확인하세요.','자원'],
    'go gas until':['정해진 양만큼 가스 확보','현재 보유량을 기준으로 목표량에 모자란 가스를 더 캡니다. 이후 소비한 가스를 계속 보충하는 목표 잔고는 아닙니다.','자원','가스 목표량'],
    'go aggressive at':['정해진 시각부터 공격 허용','게임이 시작된 뒤 지정한 시각부터 공격을 허용합니다. 병력 수 조건은 조건과 판단에서 만드세요.','운영','게임 시작 후 시간 (초)'],
    'go rush':['초반 러시 운영으로 전환','순정 전략 관리자에 초반 러시 상태를 설정합니다. 후속 테크 판단에도 영향을 줍니다.','운영'],
    'go proxy':['전진 건물 운영으로 전환','본진 밖 전진 건물을 사용하는 전략 상태를 설정합니다.','운영'],
    'go to proxy':['전진 건설용 일꾼 준비','전진 건설을 맡을 일꾼을 확보하도록 요청합니다.','건설 준비'],
    'go center proxy':['중앙 쪽에 전진 건물 배치','전진 건물을 배치할 때 맵 중앙 쪽을 고려하도록 설정합니다.','건설 준비'],
    'go block enemy scout':['상대 정찰 일꾼 막기','순정 전투 관리자에 상대 정찰을 차단하도록 요청합니다.','정찰'],
    'go wait until enemy location known':['상대 본진을 찾을 때까지 기다리기','상대 본진 위치를 확인하기 전에는 뒤의 생산 순서로 넘어가지 않습니다.','운영'],
    'go queue barrier':['앞 단계보다 뒤 생산이 앞서가지 않게 하기','순정 생산 대기열의 순서 경계입니다. 모든 건물이나 연구가 완성될 때까지 기다리는 명령은 아닙니다.','운영'],
    'go pull workers':['일꾼을 전투에 동원','지정한 수의 일꾼을 전투에 동원하도록 요청합니다.','운영','동원할 일꾼 수'],
    'go pull workers leaving':['일부 일꾼만 남기고 전투에 동원','자원 채취 일꾼 중 지정한 수를 남기고 나머지를 전투에 동원합니다.','운영','남길 일꾼 수'],
  };
  const locations={'':'자동으로 선택',main:'본진',natural:'앞마당',expo:'확장 기지',hidden:'숨겨진 위치',wall:'입구를 막는 자리',choke:'좁은 길목',proxy:'전진 위치',center:'맵 중앙', 'hidden tech':'숨겨진 기술 건물 자리',macro:'추가 생산 건물 자리','min only':'미네랄 전용 확장'};
  const norm=s=>s.trim().toLowerCase().replaceAll('_',' ');
  function item(key,catalog){
    key=norm(key);
    if(commands[key]){let [label,description,kind,argument]=commands[key];return {key,label,description,kind,argument,command:true};}
    if(upgrades[key])return {key,label:upgrades[key][0],description:upgrades[key][1],kind:'업그레이드',upgrade:true};
    let found=Object.entries(catalog.units).find(([id,u])=>norm(u.name)===key||'protoss '+norm(u.name)===key);
    if(!found)return {key,label:'해석하지 못한 항목',description:'고급 편집에서 원문을 확인하세요. 내용을 임의로 바꾸지 않습니다.',kind:'확인 필요',unknown:true};
    let [id,u]=found,building=+id>=154;
    return {key,label:u.label,description:+id===64?'자원을 채취하고 건물을 짓는 일꾼입니다.':building?'건설 위치·전력·자원이 갖춰져야 지을 수 있습니다.':'생산 건물과 자원이 갖춰지면 병력을 생산합니다.',kind:building?'건설':'생산',building,unit:true};
  }
  function parse(raw,catalog){
    let text=norm(raw),count=1,m=text.match(/^(\d+)\s+x\s+(.+)$/);if(m){count=Number(m[1]);text=m[2];}
    const parts=text.split(' then ').map(s=>{let [key,location='']=s.split(' @ '),amount;
      if(/^go (gas until|aggressive at|pull workers|pull workers leaving) \d+$/.test(key)){let at=key.lastIndexOf(' ');amount=Number(key.slice(at+1));key=key.slice(0,at);}
      return {...item(key,catalog),location,amount};
    });
    return {raw,count,parts};
  }
  function actionTitle(part,count=1){
    if(part.unknown)return part.label;
    if(part.key==='go aggressive at')return `게임 시작 ${part.amount/24}초 후 공격 허용`;
    if(part.key==='go gas until')return `가스 ${part.amount} 확보 후 채취 중단`;
    if(part.key==='go pull workers')return `일꾼 ${part.amount}기 전투 동원`;
    if(part.key==='go pull workers leaving')return `일꾼 ${part.amount}기만 남기고 전투 동원`;
    if(part.command)return part.label;
    const place=part.location?' · '+(locations[part.location]||'위치 확인 필요'):'';
    if(part.building)return `${part.label} ${count}개 건설${place}`;
    if(part.unit)return `${part.label} ${count}기 생산`;
    return part.label+(count>1?` · ${count}회`:'');
  }
  const trigger=part=>part.building?'건설이 시작되면':part.upgrade?'업그레이드가 완료되면':'연결 방식 확인 필요';
  function describe(raw,catalog){const p=parse(raw,catalog);return p.parts.map((part,i)=>(i?trigger(p.parts[i-1])+' → ':'')+actionTitle(part,p.count)).join(' · ');}
  function serialize(draft){
    if(!Number.isInteger(draft.count)||draft.count<1||draft.count>100)throw Error('반복 수는 1~100 사이의 정수로 입력하세요.');
    let parts=draft.parts.map((p,i)=>{
      if(p.unknown)throw Error('해석하지 못한 항목은 고급 편집에서 확인하세요.');
      if(i<draft.parts.length-1&&!p.building&&!p.upgrade)throw Error('이어서 할 행동은 건물 또는 업그레이드 뒤에 연결하세요.');
      if(p.argument&&(!Number.isInteger(p.amount)||p.amount<0||p.amount>2147483647))throw Error('수치가 비어 있거나 실행 범위를 벗어났습니다.');
      return p.key+(p.argument?' '+p.amount:'')+(p.building&&p.location?' @ '+p.location:'');
    });
    if(draft.count>1&&draft.parts.some(p=>p.argument))throw Error('숫자가 들어간 행동은 반복 생산과 묶지 말고 별도 단계로 추가하세요.');
    return (draft.count>1?draft.count+' x ':'')+parts.join(' then ');
  }
  function choices(catalog){
    const allowed=new Set(catalog.buildItems.map(norm));
    return [...Object.entries(catalog.units).filter(([id])=>+id>=60&&![68,103].includes(+id)).map(([,u])=>norm(u.name)),...Object.keys(upgrades).filter(k=>allowed.has(k)),...Object.keys(commands).filter(k=>allowed.has(k)||commands[k][3])].map(k=>item(k,catalog));
  }
  function humanizeText(text,catalog){
    const words=[...Object.entries(commands).filter(([,v])=>!v[3]).map(([k,v])=>[k,v[0]]),...Object.entries(upgrades).map(([k,v])=>[k,v[0]]),...Object.values(catalog.units).map(u=>[u.name,u.label])].sort((a,b)=>b[0].length-a[0].length);
    // One pass prevents replacing "scout" inside a command before its full translation.
    const escaped=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    const mapping=new Map(words.map(([k,v])=>[k.toLowerCase(),v]));
    return text.replace(new RegExp(words.map(([k])=>escaped(k)).join('|'),'gi'),s=>mapping.get(s.toLowerCase())).replaceAll(' then ',' → ');
  }
  const api={builds,upgrades,commands,locations,item,parse,actionTitle,trigger,describe,serialize,choices,humanizeText};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.OpeningLanguage=api;
})(globalThis);
