#pragma once
#include "rapidjson/document.h"
#include <map>
#include <set>
#include <string>
#include <vector>
#include <stdexcept>
#include <cmath>

namespace NNB {
struct Condition {std::string field, op; double value;};
struct Rule {
    std::string id, matchup, map, opening;
    bool once=false, latched=false;
    std::vector<Condition> conditions;
    std::map<std::string,double> actions;
};
inline bool compare(double a,const std::string& op,double b) {
    if(op==">=")return a>=b;if(op=="<=")return a<=b;if(op=="==")return a==b;
    if(op==">")return a>b;if(op=="<")return a<b;throw std::runtime_error("Unknown comparison");
}
inline bool validField(const std::string&s) {
    static const std::set<std::string> names={"seconds","minerals","gas","supply","workers","bases","army","enemyVisibleArmy","enemyNearBase","enemyMainKnown","enemyCloakKnown"};
    if(names.count(s))return true;
    for(auto prefix:{std::string("own_"),std::string("visible_")})if(s.rfind(prefix,0)==0){
        auto id=s.substr(prefix.size());if(id.empty()||id.find_first_not_of("0123456789")!=std::string::npos)return false;
        return id.size()<=3 && std::stoi(id)<228;
    }
    return false;
}
inline bool validAction(const std::string& s,double v) {
    if(!std::isfinite(v))return false;
    if(s=="aggression")return v==0||v==1;
    if(s=="retreatScore")return v>=-100000&&v<=100000;
    if(s=="retreatHoldFrames")return v>=0&&v<=1440&&std::floor(v)==v;
    if(s=="expandWorkersPerBase")return v>=8&&v<=50;
    if(s=="expandIdleWorkers")return v>=0&&v<=50;
    if(s=="maxWorkers")return v>=4&&v<=100;
    if(s=="gasWorkers")return v>=0&&v<=3;
    if(s=="meleeHP")return v>=0&&v<=100;
    if(s=="meleeShields")return v>=0&&v<=100;
    return false;
}
class RuleEngine {
public:
    bool enabled=false;
    std::vector<Rule> rules;
    std::vector<std::string> matched;
    std::map<std::string,double> output;
    void load(const rapidjson::Value& value) {
        *this=RuleEngine();
        if(!value.IsObject()||!value.HasMember("enabled")||!value["enabled"].IsBool())throw std::runtime_error("Invalid NNB policy");
        if(!value["enabled"].GetBool())return;
        if(!value.HasMember("rules")||!value["rules"].IsArray()||value["rules"].Size()>100)throw std::runtime_error("Invalid rule list");
        std::vector<Rule> pending;
        for(rapidjson::SizeType ri=0;ri<value["rules"].Size();++ri) {
            const auto& v=value["rules"][ri];
            if(!v.IsObject()||!v.HasMember("id")||!v["id"].IsString()||!v.HasMember("enabled")||!v["enabled"].IsBool())throw std::runtime_error("Invalid rule");
            if(!v["enabled"].GetBool())continue;
            Rule r;r.id=v["id"].GetString();
            if(r.id.empty()||r.id.size()>64||r.id.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789-")!=std::string::npos)throw std::runtime_error("Invalid rule id");
            for(auto key:{"matchup","map","opening","mode"})if(!v.HasMember(key)||!v[key].IsString())throw std::runtime_error("Missing rule scope");
            r.matchup=v["matchup"].GetString();r.map=v["map"].GetString();r.opening=v["opening"].GetString();
            std::string mode=v["mode"].GetString();if(mode!="once"&&mode!="while")throw std::runtime_error("Invalid rule mode");r.once=mode=="once";
            if(!v.HasMember("conditions")||!v["conditions"].IsArray()||v["conditions"].Empty())throw std::runtime_error("Empty conditions");
            for(rapidjson::SizeType ci=0;ci<v["conditions"].Size();++ci) {
                const auto& c=v["conditions"][ci];
                if(!c.IsObject()||!c.HasMember("field")||!c["field"].IsString()||!c.HasMember("op")||!c["op"].IsString()||!c.HasMember("value")||!c["value"].IsNumber())throw std::runtime_error("Invalid condition");
                Condition n{c["field"].GetString(),c["op"].GetString(),c["value"].GetDouble()};
                if(!validField(n.field)||!std::isfinite(n.value))throw std::runtime_error("Invalid field");compare(0,n.op,0);r.conditions.push_back(n);
            }
            if(!v.HasMember("actions")||!v["actions"].IsObject()||v["actions"].ObjectEmpty())throw std::runtime_error("Empty actions");
            for(auto a=v["actions"].MemberBegin();a!=v["actions"].MemberEnd();++a){
                if(!a->value.IsNumber()||!validAction(a->name.GetString(),a->value.GetDouble()))throw std::runtime_error("Invalid action");
                r.actions[a->name.GetString()]=a->value.GetDouble();
            }
            pending.push_back(r);
        }
        rules=std::move(pending);enabled=true;
    }
    void evaluate(const std::map<std::string,double>& facts,const std::string& matchup,const std::string& map,const std::string& opening) {
        output.clear();matched.clear();if(!enabled)return;
        for(auto& r:rules){
            if((!r.matchup.empty()&&r.matchup!=matchup)||(!r.map.empty()&&r.map!=map)||(!r.opening.empty()&&r.opening!=opening))continue;
            bool match=r.once&&r.latched;
            if(!match){match=true;for(auto& c:r.conditions){auto i=facts.find(c.field);if(i==facts.end()||!compare(i->second,c.op,c.value)){match=false;break;}}}
            if(!match)continue;r.latched=true;matched.push_back(r.id);
            for(auto& a:r.actions)output.emplace(a.first,a.second); // Top rule wins each action.
        }
    }
    double get(const std::string& key,double fallback)const {auto i=output.find(key);return i==output.end()?fallback:i->second;}
};
}
