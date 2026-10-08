#pragma once
#include "rapidjson/document.h"
namespace NNBPolicy {
void load(const rapidjson::Value& doc);
void update();
double value(const char* key,double fallback);
int planValue(const char* key);
}
