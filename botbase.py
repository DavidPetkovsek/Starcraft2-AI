import itertools
import random
import sc2
from sc2.constants import * #NEXUS, PROBE, PYLON, ASSIMILATOR, CHRONOBOOSTENERGYCOST, EFFECT_CHRONOBOOSTENERGYCOST, GATEWAY, CYBERNETICSCORE, FORGE, PHOTONCANNON, SHIELDBATTERY
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple, Union  # mypy type checking
from sc2.cache import property_cache_forever, property_cache_once_per_frame
from sc2.data import ActionResult, Alert, Race, Result, Target, race_gas, race_townhalls, race_worker
from sc2.data import ActionResult, Attribute, Race, race_worker, race_townhalls, race_gas, Target, Result
from sc2.game_data import AbilityData, GameData

# imports for mypy and pycharm autocomplete
from sc2.game_state import GameState
from sc2.game_data import GameData, AbilityData
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.pixel_map import PixelMap
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units

"""
This is a list of the possible values from ActionResult
['Success', 'NotSupported', 'Error', 'CantQueueThatOrder', 'Retry', 'Cooldown', 'QueueIsFull', 'RallyQueueIsFull', 'NotEnoughMinerals', 'NotEnoughVespene', 'NotEnoughTerrazine', 'NotEnoughCustom', 'NotEnoughFood', 'FoodUsageImpossible', 'NotEnoughLife', 'NotEnoughShields', 'NotEnoughEnergy', 'LifeSuppressed', 'ShieldsSuppressed', 'EnergySuppressed', 'NotEnoughCharges', 'CantAddMoreCharges', 'TooMuchMinerals', 'TooMuchVespene', 'TooMuchTerrazine', 'TooMuchCustom', 'TooMuchFood', 'TooMuchLife', 'TooMuchShields', 'TooMuchEnergy', 'MustTargetUnitWithLife', 'MustTargetUnitWithShields', 'MustTargetUnitWithEnergy', 'CantTrade', 'CantSpend', 'CantTargetThatUnit', 'CouldntAllocateUnit', 'UnitCantMove', 'TransportIsHoldingPosition', 'BuildTechRequirementsNotMet', 'CantFindPlacementLocation', 'CantBuildOnThat', 'CantBuildTooCloseToDropOff', 'CantBuildLocationInvalid', 'CantSeeBuildLocation', 'CantBuildTooCloseToCreepSource', 'CantBuildTooCloseToResources', 'CantBuildTooFarFromWater', 'CantBuildTooFarFromCreepSource', 'CantBuildTooFarFromBuildPowerSource', 'CantBuildOnDenseTerrain', 'CantTrainTooFarFromTrainPowerSource', 'CantLandLocationInvalid', 'CantSeeLandLocation', 'CantLandTooCloseToCreepSource', 'CantLandTooCloseToResources', 'CantLandTooFarFromWater', 'CantLandTooFarFromCreepSource', 'CantLandTooFarFromBuildPowerSource', 'CantLandTooFarFromTrainPowerSource', 'CantLandOnDenseTerrain', 'AddOnTooFarFromBuilding', 'MustBuildRefineryFirst', 'BuildingIsUnderConstruction', 'CantFindDropOff', 'CantLoadOtherPlayersUnits', 'NotEnoughRoomToLoadUnit', 'CantUnloadUnitsThere', 'CantWarpInUnitsThere', 'CantLoadImmobileUnits', 'CantRechargeImmobileUnits', 'CantRechargeUnderConstructionUnits', 'CantLoadThatUnit', 'NoCargoToUnload', 'LoadAllNoTargetsFound', 'NotWhileOccupied', 'CantAttackWithoutAmmo', 'CantHoldAnyMoreAmmo', 'TechRequirementsNotMet', 'MustLockdownUnitFirst', 'MustTargetUnit', 'MustTargetInventory', 'MustTargetVisibleUnit', 'MustTargetVisibleLocation', 'MustTargetWalkableLocation', 'MustTargetPawnableUnit', 'YouCantControlThatUnit', 'YouCantIssueCommandsToThatUnit', 'MustTargetResources', 'RequiresHealTarget', 'RequiresRepairTarget', 'NoItemsToDrop', 'CantHoldAnyMoreItems', 'CantHoldThat', 'TargetHasNoInventory', 'CantDropThisItem', 'CantMoveThisItem', 'CantPawnThisUnit', 'MustTargetCaster', 'CantTargetCaster', 'MustTargetOuter', 'CantTargetOuter', 'MustTargetYourOwnUnits', 'CantTargetYourOwnUnits', 'MustTargetFriendlyUnits', 'CantTargetFriendlyUnits', 'MustTargetNeutralUnits', 'CantTargetNeutralUnits', 'MustTargetEnemyUnits', 'CantTargetEnemyUnits', 'MustTargetAirUnits', 'CantTargetAirUnits', 'MustTargetGroundUnits', 'CantTargetGroundUnits', 'MustTargetStructures', 'CantTargetStructures', 'MustTargetLightUnits', 'CantTargetLightUnits', 'MustTargetArmoredUnits', 'CantTargetArmoredUnits', 'MustTargetBiologicalUnits', 'CantTargetBiologicalUnits', 'MustTargetHeroicUnits', 'CantTargetHeroicUnits', 'MustTargetRoboticUnits', 'CantTargetRoboticUnits', 'MustTargetMechanicalUnits', 'CantTargetMechanicalUnits', 'MustTargetPsionicUnits', 'CantTargetPsionicUnits', 'MustTargetMassiveUnits', 'CantTargetMassiveUnits', 'MustTargetMissile', 'CantTargetMissile', 'MustTargetWorkerUnits', 'CantTargetWorkerUnits', 'MustTargetEnergyCapableUnits', 'CantTargetEnergyCapableUnits', 'MustTargetShieldCapableUnits', 'CantTargetShieldCapableUnits', 'MustTargetFlyers', 'CantTargetFlyers', 'MustTargetBuriedUnits', 'CantTargetBuriedUnits', 'MustTargetCloakedUnits', 'CantTargetCloakedUnits', 'MustTargetUnitsInAStasisField', 'CantTargetUnitsInAStasisField', 'MustTargetUnderConstructionUnits', 'CantTargetUnderConstructionUnits', 'MustTargetDeadUnits', 'CantTargetDeadUnits', 'MustTargetRevivableUnits', 'CantTargetRevivableUnits', 'MustTargetHiddenUnits', 'CantTargetHiddenUnits', 'CantRechargeOtherPlayersUnits', 'MustTargetHallucinations', 'CantTargetHallucinations', 'MustTargetInvulnerableUnits', 'CantTargetInvulnerableUnits', 'MustTargetDetectedUnits', 'CantTargetDetectedUnits', 'CantTargetUnitWithEnergy', 'CantTargetUnitWithShields', 'MustTargetUncommandableUnits', 'CantTargetUncommandableUnits', 'MustTargetPreventDefeatUnits', 'CantTargetPreventDefeatUnits', 'MustTargetPreventRevealUnits', 'CantTargetPreventRevealUnits', 'MustTargetPassiveUnits', 'CantTargetPassiveUnits', 'MustTargetStunnedUnits', 'CantTargetStunnedUnits', 'MustTargetSummonedUnits', 'CantTargetSummonedUnits', 'MustTargetUser1', 'CantTargetUser1', 'MustTargetUnstoppableUnits', 'CantTargetUnstoppableUnits', 'MustTargetResistantUnits', 'CantTargetResistantUnits', 'MustTargetDazedUnits', 'CantTargetDazedUnits', 'CantLockdown', 'CantMindControl', 'MustTargetDestructibles', 'CantTargetDestructibles', 'MustTargetItems', 'CantTargetItems', 'NoCalldownAvailable', 'WaypointListFull', 'MustTargetRace', 'CantTargetRace', 'MustTargetSimilarUnits', 'CantTargetSimilarUnits', 'CantFindEnoughTargets', 'AlreadySpawningLarva', 'CantTargetExhaustedResources', 'CantUseMinimap', 'CantUseInfoPanel', 'OrderQueueIsFull', 'CantHarvestThatResource', 'HarvestersNotRequired', 'AlreadyTargeted', 'CantAttackWeaponsDisabled', 'CouldntReachTarget', 'TargetIsOutOfRange', 'TargetIsTooClose', 'TargetIsOutOfArc', 'CantFindTeleportLocation', 'InvalidItemClass', 'CantFindCancelOrder']
"""

class BetterBot(sc2.BotAI):

    def __init__(self):
        super().__init__()
        self.square_side_length = 1
        self.mineral_per_worker = 5 # generates 5 minerals at 5 second intervals
        self.gas_per_worker = 4 # generates 4 gas at 4 second intervals
        self.workers_per_geyser = 3
        self.pylon_build_radius = 7+0.25 # it is 7 but when doing math to ensure something fits increase it a little
        self._build_req = {CYBERNETICSCORE:GATEWAY, PHOTONCANNON:FORGE, SHIELDBATTERY:CYBERNETICSCORE,
        TWILIGHTCOUNCIL:CYBERNETICSCORE, STARGATE:CYBERNETICSCORE,
        TWILIGHTCOUNCIL:CYBERNETICSCORE, ROBOTICSFACILITY:CYBERNETICSCORE,
        TEMPLARARCHIVE:TWILIGHTCOUNCIL, DARKSHRINE:TWILIGHTCOUNCIL, FLEETBEACON:STARGATE,
        ROBOTICSBAY:ROBOTICSFACILITY}
        self.building_size = {NEXUS:5, ASSIMILATOR:3, PYLON:2, GATEWAY:3, FORGE:3, CYBERNETICSCORE:3,
        PHOTONCANNON:2, SHIELDBATTERY:2, TWILIGHTCOUNCIL:3, STARGATE:3, ROBOTICSFACILITY:3,
        TEMPLARARCHIVE:3, FLEETBEACON:3, ROBOTICSBAY:3, DARKSHRINE:2}

    def get_permit_requirements(self, unit):
        """
        Given a building
        Returns the type of building required to build the specified one, None if no requirement
        """
        return self._build_req[unit] if unit in self._build_req else None

    def valid_build_permit(self, unit, include_in_progress=False):
        """
        Given a building
        Returns true if all prerequasite buildings are finished building
        """
        req = self.get_permit_requirements(unit)
        if req == None:
            return True
        elif include_in_progress:
            return len(self.units(req).owned.ready) + self.already_pending(req) > 0
        else:
            return len(self.units(req).owned.ready) > 0

    async def build_at(self, building, at, worker=None, detailed_failures=False):
        """
        Build the given building at the x,y coordinate of 'at'.
        Where the x,y coordinate denotes the top left corner of the structure's grid.
        Uses the given worker but by default will find the closest available worker.
        Returns True on success False otherwise.
        If detailed_failures is True (by default False) then it
        returns the ActionResult of the build command. If no worker can be found
        ActionResult.Error is returned.
        """
        if isinstance(at, Unit):
            raise "must specify top left position to place building, not the position of a unit"
        at[0] = int(at[0])
        at[1] = int(at[1])
        if building == None or at == None:
            return False

        placement = Point2([at[0]+self.building_size[building]/2, at[1]+self.building_size[building]/2])
        worker = worker or self.select_build_worker(placement)

        if worker is None:
            if detailed_failures:
                return ActionResult.Error
            return False

        res = self.do(worker.build(building, placement))

        if detailed_failures:
            return res

        if res: # returns an empty list if successful otherwise list given contains list of errors
            return False
        return True

    ##########################################################
    # THE BELLOW ARE SLIGHTLY MODIFIED VERSIONS OF sc2.BotAI #
    ##########################################################
    async def build(self, building: UnitTypeId, near: Union[Point2, Point3], min_distance: int=0, max_distance: int=20, unit: Optional[Unit]=None, random_alternative: bool=True, placement_step: int=2):
        assert min_distance < max_distance, "min_distance must be less than max_distance"
        if isinstance(near, Unit):
            near = near.position.to2
        elif near is not None:
            near = near.to2
        else:
            return

        p = await self.find_placement(building, near.rounded, min_distance, max_distance, random_alternative, placement_step)
        if p is None:
            return ActionResult.CantFindPlacementLocation

        unit = unit or self.select_build_worker(p)
        if unit is None or not self.can_afford(building):
            return ActionResult.Error
        return await self.do(unit.build(building, p))

    async def find_placement(
        self,
        building: UnitTypeId,
        near: Union[Unit, Point2, Point3],
        min_distance: int = 0,
        max_distance: int = 20,
        random_alternative: bool = True,
        placement_step: int = 2,
    ) -> Optional[Point2]:
        """Finds a placement location for building."""
        assert min_distance < max_distance, "min_distance must be less than max_distance"
        assert isinstance(building, (AbilityId, UnitTypeId))
        assert isinstance(near, Point2)

        if isinstance(building, UnitTypeId):
            building = self._game_data.units[building.value].creation_ability
        else:  # AbilityId
            building = self._game_data.abilities[building.value]

        if await self.can_place(building, near):
            return near

        if max_distance == 0:
            return None

        for distance in range(min_distance, max_distance, placement_step):
            possible_positions = [
                Point2(p).offset(near).to2
                for p in (
                    [(dx, -distance) for dx in range(-distance, distance + 1, placement_step)]
                    + [(dx, distance) for dx in range(-distance, distance + 1, placement_step)]
                    + [(-distance, dy) for dy in range(-distance, distance + 1, placement_step)]
                    + [(distance, dy) for dy in range(-distance, distance + 1, placement_step)]
                )
            ]
            res = await self._client.query_building_placement(building, possible_positions)
            possible = [p for r, p in zip(res, possible_positions) if r == ActionResult.Success]
            if not possible:
                continue

            if random_alternative:
                return random.choice(possible)
            else:
                return min(possible, key=lambda p: p.distance_to_point2(near))
        return None
