"""Compile actual pinned and edited recognition/update bodies against identical observed inputs.

Sensor collection (worker visibility, geometry and snapshot estimation) is stubbed, not gameplay.
"""
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PIN='4e96da0b7e31831ee97aaef153b2bef977a235e1'


def function(source,signature):
    start=source.index(signature);a=source.index('{',start);depth=1;b=a+1
    while depth:
        if source[b]=='{':depth+=1
        if source[b]=='}':depth-=1
        b+=1
    return source[start:b]


def generate():
    legacy=subprocess.check_output(['git','show',PIN+':Steamhammer/Source/OpponentPlan.cpp'],cwd=ROOT,text=True)
    current=(ROOT/'Steamhammer/Source/OpponentPlan.cpp').read_text(encoding='utf-8')
    funcs=['bool OpponentPlan::fastPlan(OpeningPlan plan)','void OpponentPlan::recognize()','void OpponentPlan::update()']
    bodies='\n'.join(function(s,f).replace('OpponentPlan::',name+'::') for name,s in [('Legacy',legacy),('Candidate',current)] for f in funcs)
    units=sorted(set(re.findall(r'BWAPI::UnitTypes::(\w+)',bodies)))
    enum=re.search(r'enum class OpeningPlan\s*\{[\s\S]+?\};',(ROOT/'Steamhammer/Source/OpponentPlan.h').read_text()).group(0)
    source='''#include "NNBPlanSettings.h"
#include <iostream>
#include <climits>
#include <random>
struct State {int frame=0,race=0,bases=1;bool proxy=false,wall=false,worker=false;std::map<int,int> counts,frames;} state;
namespace Config {namespace Strategy {bool UsePlanRecognizer=true;}}
namespace BWAPI {
namespace UnitTypes {enum {'''+','.join(units)+'''};}
namespace Races {const int Terran=1;}
struct Player {int getRace(){return state.race;}} enemyPlayer;
struct Game {int getFrameCount(){return state.frame;} Player* enemy(){return &enemyPlayer;}} game;
Game* Broodwar=&game;
}
struct InformationManager {
static InformationManager& Instance(){static InformationManager i;return i;}
bool getEnemyProxy(){return state.proxy;} bool enemyHasWall(){return state.wall;}
int getNumBases(BWAPI::Player*){return state.bases;}
};
struct PlayerSnapshot {void takeEnemy(){} int getCount(int t){return state.counts[t];} int getFrame(int t){return state.frames.count(t)?state.frames[t]:INT_MAX;}};
namespace NNBPolicy {NNB::PlanSettings settings;int planValue(const char* key){return settings.get(key);}}
'''+enum+'\n'
    for name in ('Legacy','Candidate'):
        source+='struct '+name+''' {
OpeningPlan _openingPlan=OpeningPlan::Unknown;bool _planIsFixed=false;
bool fastPlan(OpeningPlan);void recognize();void update();
bool recognizeWorkerRush(){return state.worker;} bool recognizeFactoryTech(){return false;}
};
'''
    source+=bodies+'''
void require(bool v,const char* message){if(!v)throw std::runtime_error(message);}
int main(){try{
    std::mt19937 rng(9817);int cases=0;
    int boundaries[]={0,99,100,101,103,1599,1600,1601,2999,3000,3001,3999,4000,4001,5499,5500,5501,5999,6000,6001,6999,7000,7001,7999,8000,8001,9999,10000,10001};
    for(int i=0;i<6000;i++){
        state=State();state.frame=i<3000?boundaries[rng()%29]:rng()%11000;
        state.race=rng()%3;state.proxy=rng()%19==0;state.wall=rng()%3==0;state.worker=rng()%11==0;state.bases=rng()%4;
        for(int type=0;type<'''+str(len(units))+''';type++){
            state.counts[type]=rng()%3==0?rng()%14:0;
            if(rng()%10==0)state.frames[type]=rng()%12000;
        }
        for(int plan=0;plan<int(OpeningPlan::Size);plan++){
            Legacy a;Candidate b;a._openingPlan=b._openingPlan=OpeningPlan(plan);
            a.recognize();b.recognize();
            require(a._openingPlan==b._openingPlan&&a._planIsFixed==b._planIsFixed,"Default recognition diverged");cases++;
            Legacy c;Candidate d;c._openingPlan=d._openingPlan=OpeningPlan(plan);c._planIsFixed=d._planIsFixed=(i%2==0);
            c.update();d.update();require(c._openingPlan==d._openingPlan&&c._planIsFixed==d._planIsFixed,"Default update diverged");cases++;
        }
    }
    state=State();state.frame=1000;state.frames[BWAPI::UnitTypes::Zerg_Spawning_Pool]=1550;
    Candidate a;a.recognize();require(a._openingPlan==OpeningPlan::FastRush,"Default boundary fixture wrong");
    rapidjson::Document config;config.Parse("{\\"fastPool\\":1500}");NNBPolicy::settings.load(config);
    Candidate b;b.recognize();require(b._openingPlan!=OpeningPlan::FastRush,"Edited threshold was ignored");
    config.Parse("{\\"fastEnabled\\":0}");NNBPolicy::settings.load(config);Candidate c;c.recognize();require(c._openingPlan!=OpeningPlan::FastRush,"Disabled inference ran");
    config.Parse("{\\"startFrame\\":500,\\"endFrame\\":200}");bool rejected=false;try{NNBPolicy::settings.load(config);}catch(...){rejected=true;}require(rejected,"Invalid time window accepted");
    std::cout<<cases<<" default recognition/update comparisons passed; edited threshold, disable and invalid-window checks passed. Sensors and gameplay not tested.\\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what();return 1;}}
'''
    path=ROOT/'build/native-generated/plan-regression.cpp';path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists() or path.read_text(encoding='utf-8')!=source:path.write_text(source,encoding='utf-8')


if __name__=='__main__':generate()
