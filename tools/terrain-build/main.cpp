#include "MapData.h"
#include "terrain_analysis.h"
#include <filesystem>
#include <cstdint>
#include <stdexcept>
#include <vector>
#include <cmath>
#include <fstream>
#include <iostream>

// Input carries exact CHK-derived grids, neutral units and the observed BWAPI map hash.
// The original BWTA 2.2 analyzer writes its genuine version-6 cache.
int main(int argc,char**argv) {
  try {
    if(argc!=3)throw std::runtime_error("nnb-terrain input.bin observed-map-hash");
    std::ifstream f(argv[1],std::ios::binary);
    auto integer=[&](){uint32_t n=0;f.read((char*)&n,4);if(!f)throw std::runtime_error("Truncated input");return n;};
    if(integer()!=0x31424E4E)throw std::runtime_error("Bad input magic");
    auto w=integer(),h=integer();if(w<1||w>256||h<1||h>256)throw std::runtime_error("Bad dimensions");
    BWTA::MapData::mapWidth=w;BWTA::MapData::mapHeight=h;
    BWTA::MapData::hash=argv[2];BWTA::MapData::mapFileName=argv[1];
    BWTA::MapData::rawWalkability.resize(w*4,h*4);
    BWTA::MapData::buildability.resize(w,h);
    for(unsigned y=0;y<h*4;y++)for(unsigned x=0;x<w*4;x++){char b=0;f.get(b);BWTA::MapData::rawWalkability[x][y]=b!=0;}
    for(unsigned y=0;y<h;y++)for(unsigned x=0;x<w;x++){char b=0;f.get(b);BWTA::MapData::buildability[x][y]=b!=0;}
    auto n=integer();if(n>10000)throw std::runtime_error("Too many units");
    for(unsigned i=0;i<n;i++){
      auto id=integer(),x=integer(),y=integer(),resources=integer();
      BWAPI::UnitType type(id);BWAPI::Position pos(x,y);
      if(type.isMineralField()){if(resources>200)BWTA::MapData::resourcesWalkPositions.emplace_back(type,BWAPI::WalkPosition(pos));}
      else if(type==BWAPI::UnitTypes::Resource_Vespene_Geyser)BWTA::MapData::resourcesWalkPositions.emplace_back(type,BWAPI::WalkPosition(pos));
      else if(type==BWAPI::UnitTypes::Special_Start_Location)BWTA::MapData::startLocations.push_back(BWAPI::TilePosition((int(x)-64)/32,(int(y)-48)/32));
      else if(type.isBuilding()||type==BWAPI::UnitTypes::Zerg_Lurker_Egg)BWTA::MapData::staticNeutralBuildings.emplace_back(type,pos);
    }
    std::filesystem::create_directories("logs");std::filesystem::create_directories("bwapi-data/logs");
    BWTA::analyze();
    std::cout<<"bases="<<BWTA::getBaseLocations().size()<<" starts="<<BWTA::getStartLocations().size()<<" regions="<<BWTA::getRegions().size()<<" chokes="<<BWTA::getChokepoints().size()<<std::endl;
    if(BWTA::getStartLocations().size()<2)throw std::runtime_error("Analyzer did not identify starts");
#ifdef NNB_CACHE_CHECK
    std::vector<BWTA::BaseLocation*> bases(BWTA::getBaseLocations().begin(),BWTA::getBaseLocations().end());
    if(BWTA::getStartLocations().size()!=BWTA::MapData::startLocations.size())throw std::runtime_error("Start count differs from CHK");
    for(auto start:BWTA::MapData::startLocations){
      bool found=false;for(auto b:bases)if(b->isStartLocation()&&b->getTilePosition().getDistance(start)<=1)found=true;
      if(!found)throw std::runtime_error("Start location does not match CHK");
    }
    for(auto a:BWTA::getStartLocations())for(auto b:BWTA::getStartLocations())if(a!=b&&a->getGroundDistance(b)<=0)throw std::runtime_error("Start locations disconnected");
    std::ofstream out("geometry.json");out<<"{\"width\":"<<w<<",\"height\":"<<h<<",\"bases\":[";
    bool first=true;for(auto b:bases){
      if(!b->getRegion())throw std::runtime_error("Base has no region");
      if(!first)out<<",";first=false;
      out<<"{\"x\":"<<b->getPosition().x<<",\"y\":"<<b->getPosition().y<<",\"tileX\":"<<b->getTilePosition().x<<",\"tileY\":"<<b->getTilePosition().y<<",\"start\":"<<(b->isStartLocation()?"true":"false")<<",\"island\":"<<(b->isIsland()?"true":"false")<<",\"distances\":[";
      bool f2=true;for(auto d:bases){if(!f2)out<<",";f2=false;out<<b->getGroundDistance(d);}out<<"]}";
    }
    out<<"],\"chokes\":[";first=true;
    for(auto c:BWTA::getChokepoints()){
      if(!c->getRegions().first||!c->getRegions().second||!std::isfinite(c->getWidth())||c->getWidth()<=0)throw std::runtime_error("Invalid choke");
      if(!first)out<<",";first=false;out<<"{\"x\":"<<c->getCenter().x<<",\"y\":"<<c->getCenter().y<<",\"width\":"<<c->getWidth()<<",\"sides\":[["<<c->getSides().first.x<<","<<c->getSides().first.y<<"],["<<c->getSides().second.x<<","<<c->getSides().second.y<<"]]}";
    }
    out<<"],\"regions\":[";first=true;
    for(auto r:BWTA::getRegions()){
      if(!first)out<<",";first=false;out<<"{\"x\":"<<r->getCenter().x<<",\"y\":"<<r->getCenter().y<<",\"polygon\":[";
      bool f2=true;for(auto p:r->getPolygon()){if(!f2)out<<",";f2=false;out<<"["<<p.x<<","<<p.y<<"]";}out<<"]}";
    }
    out<<"],\"cacheLoadVerified\":true,\"nativeGameTested\":false}";
#endif
    BWTA::cleanMemory();return 0;
  }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}
}
