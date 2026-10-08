#include <BWAPI.h>
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include <iostream>

// Read the same BWAPI type database linked into Locutus; no game is started.
int main() {
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> w(buffer);
    auto str=[&](const char* key,const std::string& value){w.String(key);w.String(value.c_str());};
    auto num=[&](const char* key,int value){w.String(key);w.Int(value);};
    auto required=[&](BWAPI::UnitType type,int count=1){
        if(type!=BWAPI::UnitTypes::None){w.StartObject();num("id",type.getID());num("count",count);w.EndObject();}
    };
    w.StartArray();
    for(auto t:BWAPI::UnitTypes::allUnitTypes()) {
        if(t.getRace()!=BWAPI::Races::Protoss||t.isHero()||t.whatBuilds().first==BWAPI::UnitTypes::None)continue;
        w.StartObject();str("kind","unit");str("name",t.getName());num("id",t.getID());
        num("minerals",t.mineralPrice());num("gas",t.gasPrice());num("supply",t.supplyRequired());num("capacity",t.supplyProvided());
        w.String("building");w.Bool(t.isBuilding());w.String("requires");w.StartArray();
        for(auto r:t.requiredUnits())required(r.first,r.second);
        required(t.whatBuilds().first,t.whatBuilds().second);
        w.EndArray();w.EndObject();
    }
    for(auto t:BWAPI::TechTypes::allTechTypes()) {
        if(t.getRace()!=BWAPI::Races::Protoss||t.whatResearches()==BWAPI::UnitTypes::None)continue;
        w.StartObject();str("kind","tech");str("name",t.getName());num("minerals",t.mineralPrice());num("gas",t.gasPrice());
        w.String("requires");w.StartArray();required(t.whatResearches());required(t.requiredUnit());w.EndArray();w.EndObject();
    }
    for(auto t:BWAPI::UpgradeTypes::allUpgradeTypes()) {
        if(t.getRace()!=BWAPI::Races::Protoss||t.whatUpgrades()==BWAPI::UnitTypes::None)continue;
        w.StartObject();str("kind","upgrade");str("name",t.getName());num("minerals",t.mineralPrice());num("gas",t.gasPrice());
        w.String("requires");w.StartArray();required(t.whatUpgrades());required(t.whatsRequired());w.EndArray();
        w.String("levels");w.StartArray();
        for(int level=1;level<=t.maxRepeats();++level){
            w.StartObject();num("minerals",t.mineralPrice(level));num("gas",t.gasPrice(level));
            w.String("requires");w.StartArray();required(t.whatUpgrades());required(t.whatsRequired(level));w.EndArray();w.EndObject();
        }
        w.EndArray();w.EndObject();
    }
    w.EndArray();std::cout<<buffer.GetString();
}
