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
        self.target_mineral_income = 5*16
        self.target_gas_income = 5*6
        self.mineral_per_worker = 5
        self.gas_per_worker = 5
        self.workers_per_geyser = 3

    def valid_build_permit(self, unit):
        """
        Given a building
        Returns true if all prerequasite buildings are finished building
        """
        if unit == CYBERNETICSCORE:
            return len(self.units(GATEWAY).owned.ready) > 0
        elif unit == PHOTONCANNON:
            return len(self.units(FORGE).owned.ready) > 0
        elif unit == SHIELDBATTERY:
            return len(self.units(CYBERNETICSCORE).owned.ready) > 0
        elif unit == TWILIGHTCOUNCIL:
            return len(self.units(CYBERNETICSCORE).owned.ready) > 0
        elif unit == STARGATE:
            return len(self.units(CYBERNETICSCORE).owned.ready) > 0
        elif unit == TWILIGHTCOUNCIL:
            return len(self.units(CYBERNETICSCORE).owned.ready) > 0
        elif unit == ROBOTICSFACILITY:
            return len(self.units(CYBERNETICSCORE).owned.ready) > 0
        elif unit == TEMPLARARCHIVE:
            return len(self.units(TWILIGHTCOUNCIL).owned.ready) > 0
        elif unit == DARKSHRINE:
            return len(self.units(TWILIGHTCOUNCIL).owned.ready) > 0
        elif unit == FLEETBEACON:
            return len(self.units(STARGATE).owned.ready) > 0
        elif unit == ROBOTICSBAY:
            return len(self.units(ROBOTICSFACILITY).owned.ready) > 0

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
