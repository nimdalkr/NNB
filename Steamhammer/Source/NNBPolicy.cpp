#include "Common.h"
#include "NNBPolicy.h"
#include "NNBRuleEngine.h"
#include "NNBPlanSettings.h"
#include "OpponentModel.h"
#include "InformationManager.h"
#include "Config.h"
#include <fstream>
namespace NNBPolicy {
namespace {
NNB::RuleEngine engine;
NNB::PlanSettings recognition;
int maxWorkers=75,gasWorkers=3,meleeHP=0,meleeShields=0;
std::vector<std::string> lastMatched;
}
void load(const rapidjson::Value& doc){
    engine=NNB::RuleEngine();recognition=NNB::PlanSettings();lastMatched.clear();
    if(!doc.HasMember("NNBPolicy"))return;
    try{engine.load(doc["NNBPolicy"]);}catch(const std::exception& e){engine=NNB::RuleEngine();Log().Get()<<"NNB policy disabled: "<<e.what();return;}
    if(!engine.enabled)return;
    if(doc["NNBPolicy"].HasMember("recognition")){
        try{recognition.load(doc["NNBPolicy"]["recognition"]);}
        catch(const std::exception& e){recognition=NNB::PlanSettings();Log().Get()<<"NNB recognition defaults restored: "<<e.what();}
    }
    if(doc.HasMember("Macro")&&doc["Macro"].HasMember("AbsoluteMaxWorkers")&&doc["Macro"]["AbsoluteMaxWorkers"].IsInt())
        Config::Macro::AbsoluteMaxWorkers=std::max(4,std::min(100,doc["Macro"]["AbsoluteMaxWorkers"].GetInt()));
    maxWorkers=Config::Macro::AbsoluteMaxWorkers;gasWorkers=Config::Macro::WorkersPerRefinery;
    meleeHP=Config::Micro::RetreatMeleeUnitHP;meleeShields=Config::Micro::RetreatMeleeUnitShields;
}
double value(const char* key,double fallback){return engine.get(key,fallback);}
int planValue(const char* key){return recognition.get(key);}
void update(){
    if(!engine.enabled||BWAPI::Broodwar->getFrameCount()%8)return;
    auto self=BWAPI::Broodwar->self(), enemy=BWAPI::Broodwar->enemy();
    std::map<std::string,double> f={{"seconds",BWAPI::Broodwar->getFrameCount()/24.0},{"minerals",double(self->minerals())},{"gas",double(self->gas())},{"supply",self->supplyUsed()/2.0},{"workers",0},{"bases",0},{"army",0},{"enemyVisibleArmy",0},{"enemyNearBase",0}};
    std::vector<BWAPI::Position> bases;
    for(int id=0;id<228;id++){f["own_"+std::to_string(id)]=0;f["visible_"+std::to_string(id)]=0;}
    for(auto u:self->getUnits())if(u->exists()&&u->isCompleted()){
        auto t=u->getType();f["own_"+std::to_string(t.getID())]++;
        if(t.isWorker())f["workers"]++;else if(t.isResourceDepot()){f["bases"]++;bases.push_back(u->getPosition());}
        else if(!t.isBuilding()&&(t.canAttack()||t.isSpellcaster()))f["army"]+=t.mineralPrice()+t.gasPrice();
    }
    for(auto u:enemy->getUnits())if(u->exists()&&u->isVisible()){
        auto t=u->getType();f["visible_"+std::to_string(t.getID())]++;
        if(!t.isWorker()&&!t.isBuilding()&&t.canAttack()){
            auto v=t.mineralPrice()+t.gasPrice();f["enemyVisibleArmy"]+=v;
            for(auto p:bases)if(u->getDistance(p)<768){f["enemyNearBase"]+=v;break;}
        }
    }
    auto& info=UAlbertaBot::InformationManager::Instance();
    f["enemyMainKnown"]=info.getEnemyMainBaseLocation()!=nullptr;
    f["enemyCloakKnown"]=info.enemyHasCloakTech();
    using UAlbertaBot::OpeningPlan;
    auto plan=UAlbertaBot::OpponentModel::Instance().getEnemyPlan();
    for(auto entry:std::map<OpeningPlan,const char*>{{OpeningPlan::Proxy,"plan_proxy"},{OpeningPlan::WorkerRush,"plan_worker"},{OpeningPlan::FastRush,"plan_fast"},{OpeningPlan::NotFastRush,"plan_notFast"},{OpeningPlan::HeavyRush,"plan_heavy"},{OpeningPlan::HydraBust,"plan_hydra"},{OpeningPlan::WallIn,"plan_wall"},{OpeningPlan::DarkTemplar,"plan_dark"}})f[entry.second]=plan==entry.first?1:0;
    std::string matchup="Pv"+enemy->getRace().getName().substr(0,1);
    engine.evaluate(f,matchup,BWAPI::Broodwar->mapHash(),Config::Strategy::StrategyName);
    Config::Macro::AbsoluteMaxWorkers=int(value("maxWorkers",maxWorkers));
    Config::Macro::WorkersPerRefinery=int(value("gasWorkers",gasWorkers));
    Config::Micro::RetreatMeleeUnitHP=int(value("meleeHP",meleeHP));
    Config::Micro::RetreatMeleeUnitShields=int(value("meleeShields",meleeShields));
    if(engine.matched!=lastMatched){
        std::ofstream log(Config::IO::WriteDir+"NNB-decisions.jsonl",std::ios::app);
        log<<"{\"frame\":"<<BWAPI::Broodwar->getFrameCount()<<",\"matched\":[";
        bool first=true;for(auto& id:engine.matched){if(!first)log<<",";first=false;log<<"\""<<id<<"\"";}
        log<<"],\"facts\":{";first=true;std::set<std::string> recorded;
        for(auto& rule:engine.rules)for(auto& c:rule.conditions)if(recorded.insert(c.field).second&&f.count(c.field)){
            if(!first)log<<",";first=false;log<<"\""<<c.field<<"\":"<<f[c.field];
        }
        log<<"},\"actions\":{";first=true;for(auto& a:engine.output){if(!first)log<<",";first=false;log<<"\""<<a.first<<"\":"<<a.second;}log<<"}}\n";
        lastMatched=engine.matched;
    }
}
}
