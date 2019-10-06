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

class BetterBot(sc2.BotAI):

    def __init__(self):
        super().__init__()
        self.mineral_per_worker = 5 # generates 5 minerals at 5 second intervals
        self.gas_per_worker = 4 # generates 4 gas at 4 second intervals
        self.workers_per_geyser = 3
        self._build_req = {CYBERNETICSCORE:GATEWAY, PHOTONCANNON:FORGE, SHIELDBATTERY:CYBERNETICSCORE,
        TWILIGHTCOUNCIL:CYBERNETICSCORE, STARGATE:CYBERNETICSCORE,
        TWILIGHTCOUNCIL:CYBERNETICSCORE, ROBOTICSFACILITY:CYBERNETICSCORE,
        TEMPLARARCHIVE:TWILIGHTCOUNCIL, DARKSHRINE:TWILIGHTCOUNCIL, FLEETBEACON:STARGATE,
        ROBOTICSBAY:ROBOTICSFACILITY}

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
