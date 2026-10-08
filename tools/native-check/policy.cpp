#include "NNBRuleEngine.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include <iostream>
#include <sstream>
int main(){
    try {
        std::ostringstream input;input<<std::cin.rdbuf();rapidjson::Document d;d.Parse(input.str().c_str());
        if(d.HasParseError()||!d.IsObject()||!d.HasMember("policy")||!d.HasMember("facts"))throw std::runtime_error("Invalid request");
        NNB::RuleEngine e;e.load(d["policy"]);std::map<std::string,double> facts;
        for(auto i=d["facts"].MemberBegin();i!=d["facts"].MemberEnd();++i)facts[i->name.GetString()]=i->value.GetDouble();
        e.evaluate(facts,d["matchup"].GetString(),d["map"].GetString(),d["opening"].GetString());
        if(d.HasMember("nextFacts")){facts.clear();for(auto i=d["nextFacts"].MemberBegin();i!=d["nextFacts"].MemberEnd();++i)facts[i->name.GetString()]=i->value.GetDouble();e.evaluate(facts,d["matchup"].GetString(),d["map"].GetString(),d["opening"].GetString());}
        rapidjson::StringBuffer b;rapidjson::Writer<rapidjson::StringBuffer>w(b);w.StartObject();w.String("matched");w.StartArray();for(auto&i:e.matched)w.String(i.c_str());w.EndArray();w.String("actions");w.StartObject();for(auto&i:e.output){w.String(i.first.c_str());w.Double(i.second);}w.EndObject();w.EndObject();std::cout<<b.GetString();return 0;
    }catch(const std::exception&e){std::cerr<<e.what();return 1;}
}
