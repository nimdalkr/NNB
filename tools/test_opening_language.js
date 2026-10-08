const assert=require('node:assert/strict'),fs=require('node:fs');
const L=require('../editor/opening-language.js');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
let count=0;
for(const [id,build] of Object.entries(input.strategies)){
  if(build.Race!=='Protoss')continue;
  assert.ok(L.builds[id],`Missing build explanation: ${id}`);
  for(const raw of build.OpeningBuildOrder){
    const parsed=L.parse(raw,input.catalog);
    assert.ok(parsed.parts.every(x=>!x.unknown),`Unknown: ${raw}`);
    assert.equal(L.serialize(parsed),raw.toLowerCase(),`Form roundtrip changed: ${raw}`);
    assert.ok(!/\bgo\b|\bwhile\b|singularity|enhancements|\bthen\b/i.test(L.describe(raw,input.catalog)),raw);
    count++;
  }
}
const chain=L.parse('pylon then go scout while safe',input.catalog);
assert.match(L.describe(chain.raw,input.catalog),/건설이 시작되면/);
assert.match(L.describe('singularity charge then go aggressive',input.catalog),/업그레이드가 완료되면/);
chain.parts[0].location='natural';assert.equal(L.serialize(chain),'pylon @ natural then go scout while safe');
assert.equal(L.describe('go aggressive at 1440',input.catalog),'게임 시작 60초 후 공격 허용');
assert.match(L.humanizeText('pylon then go scout while safe',input.catalog),/안전한 동안 일꾼 정찰/);
assert.throws(()=>L.serialize(L.parse('go scout then pylon',input.catalog)));
assert.throws(()=>L.serialize(L.parse('2 x go aggressive at 1440',input.catalog)));
console.log(`${count} opening rows: Korean coverage and exact form roundtrip passed; chain and timing semantics passed.`);
