#include "OpponentPlan.h"
#include "NNBPolicy.h"

#include "InformationManager.h"
#include "ScoutManager.h"
#include "PlayerSnapshot.h"

using namespace UAlbertaBot;

// Attempt to recognize what the opponent is doing, so we can cope with it.
// For now, only try to recognize a small number of opening situations that require
// different handling.

// This is part of the OpponentModel module. Access should normally be through the OpponentModel instance.

// -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --

bool OpponentPlan::fastPlan(OpeningPlan plan)
{
	return
		plan == OpeningPlan::Proxy ||
		plan == OpeningPlan::WorkerRush ||
		plan == OpeningPlan::FastRush;
}

// NOTE Incomplete test! We don't measure the distance of enemy units from the enemy base,
//      so we don't recognize all the rushes that we should.
bool OpponentPlan::recognizeWorkerRush()
{
	BWAPI::Position myOrigin = InformationManager::Instance().getMyMainBaseLocation()->getPosition();

	int enemyWorkerRushCount = 0;

	for (const auto & kv : InformationManager::Instance().getUnitData(BWAPI::Broodwar->enemy()).getUnits())
	{
		const UnitInfo & ui(kv.second);

		if (ui.type.isWorker() && ui.unit->isVisible() && myOrigin.getDistance(ui.unit->getPosition()) < NNBPolicy::planValue("workerRadius"))
		{
			++enemyWorkerRushCount;
		}
	}

	return enemyWorkerRushCount >= NNBPolicy::planValue("workerCount");
}

// Factory, possibly with starport, and no sign of many marines intended.
bool OpponentPlan::recognizeFactoryTech()
{
	if (BWAPI::Broodwar->enemy()->getRace() != BWAPI::Races::Terran)
	{
		return false;
	}

	int nMarines = 0;
	int nBarracks = 0;
	int nTechProduction = 0;
	bool tech = false;

	for (const auto & kv : InformationManager::Instance().getUnitData(BWAPI::Broodwar->enemy()).getUnits())
	{
		const UnitInfo & ui(kv.second);

		if (ui.type == BWAPI::UnitTypes::Terran_Marine)
		{
			++nMarines;
		}

		else if (ui.type.whatBuilds().first == BWAPI::UnitTypes::Terran_Barracks)
		{
			return false;			// academy implied, marines seem to be intended
		}

		else if (ui.type == BWAPI::UnitTypes::Terran_Barracks)
		{
			++nBarracks;
		}

		else if (ui.type == BWAPI::UnitTypes::Terran_Academy)
		{
			return false;			// marines seem to be intended
		}

		else if (ui.type == BWAPI::UnitTypes::Terran_Factory ||
			ui.type == BWAPI::UnitTypes::Terran_Starport)
		{
			++nTechProduction;
		}

		else if (ui.type.whatBuilds().first == BWAPI::UnitTypes::Terran_Factory ||
			ui.type.whatBuilds().first == BWAPI::UnitTypes::Terran_Starport ||
			ui.type == BWAPI::UnitTypes::Terran_Armory)
		{
			tech = true;			// indicates intention to rely on tech units
		}
	}

	return (nTechProduction >= 2 || tech) && nMarines <= 6 && nBarracks <= 1;
}

void OpponentPlan::recognize()
{
	// Recognize fast plans first, slow plans below.

	// Recognize in-base proxy buildings. Info manager does it for us.
	if (NNBPolicy::planValue("proxyEnabled") && InformationManager::Instance().getEnemyProxy())
	{
		_openingPlan = OpeningPlan::Proxy;
		_planIsFixed = true;
		return;
	}

    int frame = BWAPI::Broodwar->getFrameCount();

	// Recognize worker rushes.
	if (NNBPolicy::planValue("workerEnabled") && frame < NNBPolicy::planValue("workerUntil") && recognizeWorkerRush())
	{
		_openingPlan = OpeningPlan::WorkerRush;
		return;
	}

	PlayerSnapshot snap;
	snap.takeEnemy();

	// Recognize fast rushes.
	if (NNBPolicy::planValue("fastEnabled") && (snap.getFrame(BWAPI::UnitTypes::Zerg_Spawning_Pool) < NNBPolicy::planValue("fastPool") ||
		snap.getFrame(BWAPI::UnitTypes::Zerg_Zergling) < NNBPolicy::planValue("fastLing") ||
		snap.getFrame(BWAPI::UnitTypes::Protoss_Gateway) < NNBPolicy::planValue("fastGateway") ||
		snap.getFrame(BWAPI::UnitTypes::Protoss_Zealot) < NNBPolicy::planValue("fastZealot") ||
		snap.getFrame(BWAPI::UnitTypes::Terran_Barracks) < NNBPolicy::planValue("fastBarracks") ||
		snap.getFrame(BWAPI::UnitTypes::Terran_Marine) < NNBPolicy::planValue("fastMarine")))
	{
		_openingPlan = OpeningPlan::FastRush;
		_planIsFixed = true;
		return;
	}

	// Plans below here are slow plans. Do not overwrite a fast plan with a slow plan.
	if (fastPlan(_openingPlan))
	{
		return;
	}

    // When we know the enemy is not doing a fast plan, set it
    // May get overridden by a more appropriate plan below later on
    if (NNBPolicy::planValue("notFastEnabled") && (_openingPlan == OpeningPlan::Unknown && (
        snap.getCount(BWAPI::UnitTypes::Zerg_Drone) > NNBPolicy::planValue("notFastDrone") ||     // 4- or 5-pool
        snap.getCount(BWAPI::UnitTypes::Terran_SCV) > NNBPolicy::planValue("notFastSCV") ||     // BBS
        snap.getCount(BWAPI::UnitTypes::Protoss_Probe) > NNBPolicy::planValue("notFastProbe")) || // 9-gate
        frame > NNBPolicy::planValue("notFastAfter"))) // Failsafe if we have no other information at this point
    {
        _openingPlan = OpeningPlan::NotFastRush;
    }

	// Recognize slower rushes.
	// TODO make sure we've seen the bare geyser in the enemy base!
	// TODO seeing a unit carrying gas also means the enemy has gas
	if (NNBPolicy::planValue("heavyEnabled") && (frame < NNBPolicy::planValue("heavyLingUntil") &&
        snap.getCount(BWAPI::UnitTypes::Zerg_Zergling) > NNBPolicy::planValue("heavyLingCount")
        ||
        frame > NNBPolicy::planValue("oneHatchAfter") &&
        snap.getCount(BWAPI::UnitTypes::Zerg_Hatchery) == NNBPolicy::planValue("oneHatchCount") &&
        snap.getCount(BWAPI::UnitTypes::Zerg_Drone) <= NNBPolicy::planValue("oneHatchDrones")
        ||
        snap.getCount(BWAPI::UnitTypes::Zerg_Hatchery) >= NNBPolicy::planValue("heavyHatchCount") &&
		snap.getCount(BWAPI::UnitTypes::Zerg_Spawning_Pool) > 0 &&
		snap.getCount(BWAPI::UnitTypes::Zerg_Extractor) == 0 &&
        snap.getCount(BWAPI::UnitTypes::Zerg_Zergling) > NNBPolicy::planValue("heavyHatchLings")
		||
		snap.getCount(BWAPI::UnitTypes::Terran_Barracks) >= NNBPolicy::planValue("heavyBarracks") &&
		snap.getCount(BWAPI::UnitTypes::Terran_Refinery) == 0 &&
		snap.getCount(BWAPI::UnitTypes::Terran_Command_Center) <= NNBPolicy::planValue("heavyCC") &&
		snap.getCount(BWAPI::UnitTypes::Terran_Marine) > NNBPolicy::planValue("heavyMarines")
		||
		snap.getCount(BWAPI::UnitTypes::Protoss_Gateway) >= NNBPolicy::planValue("heavyGateways") &&
		snap.getCount(BWAPI::UnitTypes::Protoss_Assimilator) == 0 &&
		snap.getCount(BWAPI::UnitTypes::Protoss_Nexus) <= NNBPolicy::planValue("heavyNexus") &&
		snap.getCount(BWAPI::UnitTypes::Protoss_Zealot) > NNBPolicy::planValue("heavyZealots")))
	{
		_openingPlan = OpeningPlan::HeavyRush;
		_planIsFixed = true;
		return;
	}

    // Recognize a hydra bust
    if (NNBPolicy::planValue("hydraEnabled") && frame < NNBPolicy::planValue("hydraUntil") &&
        snap.getCount(BWAPI::UnitTypes::Zerg_Hatchery) >= NNBPolicy::planValue("hydraHatches") &&
        snap.getCount(BWAPI::UnitTypes::Zerg_Hydralisk_Den) > 0 &&
        snap.getCount(BWAPI::UnitTypes::Zerg_Zergling) < NNBPolicy::planValue("hydraLings"))
    {
        _openingPlan = OpeningPlan::HydraBust;
        _planIsFixed = true;
        return;
    }

    // Terran wall-in
    if (NNBPolicy::planValue("wallEnabled") && frame < NNBPolicy::planValue("wallUntil") &&
        BWAPI::Broodwar->enemy()->getRace() == BWAPI::Races::Terran &&
        InformationManager::Instance().enemyHasWall())
    {
        _openingPlan = OpeningPlan::WallIn;
        _planIsFixed = true;
        return;
    }

    // Protoss dark templar opening
    if (NNBPolicy::planValue("darkEnabled") && frame < NNBPolicy::planValue("darkUntil") &&
        snap.getCount(BWAPI::UnitTypes::Protoss_Dark_Templar) > NNBPolicy::planValue("darkCount"))
    {
        _openingPlan = OpeningPlan::DarkTemplar;
        _planIsFixed = true;
        return;
    }

    // Disabling the rest, as we do no specific counters or reactions to them
    // Better to leave it as NotFastRush so we don't confuse our opening selection
    return;

	// Recognize terran factory tech openings.
	if (recognizeFactoryTech())
	{
		_openingPlan = OpeningPlan::Factory;
		return;
	}

	// Recognize expansions with pre-placed static defense.
	// Zerg can't do this.
	// NOTE Incomplete test! We don't check the location of the static defense
	if (InformationManager::Instance().getNumBases(BWAPI::Broodwar->enemy()) >= 2)
	{
		if (snap.getCount(BWAPI::UnitTypes::Terran_Bunker) > 0 ||
			snap.getCount(BWAPI::UnitTypes::Protoss_Photon_Cannon) > 0)
		{
			_openingPlan = OpeningPlan::SafeExpand;
			return;
		}
	}

	// Recognize a naked expansion.
	// This has to run after the SafeExpand check, since it doesn't check for what's missing.
	if (InformationManager::Instance().getNumBases(BWAPI::Broodwar->enemy()) >= 2)
	{
		_openingPlan = OpeningPlan::NakedExpand;
		return;
	}

	// Recognize a turtling enemy.
	// NOTE Incomplete test! We don't check where the defenses are placed.
	if (InformationManager::Instance().getNumBases(BWAPI::Broodwar->enemy()) < 2)
	{
		if (snap.getCount(BWAPI::UnitTypes::Terran_Bunker) >= 2 ||
			snap.getCount(BWAPI::UnitTypes::Protoss_Photon_Cannon) >= 2 ||
			snap.getCount(BWAPI::UnitTypes::Zerg_Sunken_Colony) >= 2)
		{
			_openingPlan = OpeningPlan::Turtle;
			return;
		}
	}

	// Nothing recognized: Opening plan remains unchanged.
}

// -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --

OpponentPlan::OpponentPlan()
	: _openingPlan(OpeningPlan::Unknown)
	, _planIsFixed(false)
{
}

// Update the recognized plan.
// Call this every frame. It will take care of throttling itself down to avoid unnecessary work.
void OpponentPlan::update()
{
	if (!Config::Strategy::UsePlanRecognizer)
	{
		return;
	}

	// The plan is decided. Don't change it any more.
	if (_planIsFixed)
	{
		return;
	}

	int frame = BWAPI::Broodwar->getFrameCount();

	if (frame > NNBPolicy::planValue("startFrame") && frame < NNBPolicy::planValue("endFrame") &&       // only try to recognize openings
		frame % 12 == 7)                      // update interval
	{
		recognize();
	}
}
