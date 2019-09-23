import sc2, math, asyncio
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, CHRONOBOOSTENERGYCOST, EFFECT_CHRONOBOOSTENERGYCOST, GATEWAY, CYBERNETICSCORE, FORGE, PHOTONCANNON, SHIELDBATTERY

import itertools
import random
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


class WabaBot(sc2.BotAI):

    def __init__(self):
        super().__init__()
        self.target_mineral_income = 5*16
        self.target_gas_income = 5*6
        self.mineral_per_worker = 5
        self.gas_per_worker = 5
        self.workers_per_geyser = 3
        self.build_order = [PYLON, GATEWAY, ASSIMILATOR, PYLON, ASSIMILATOR, CYBERNETICSCORE, GATEWAY, GATEWAY, PYLON, GATEWAY, FORGE] + [PHOTONCANNON]*10 + [PYLON] + [SHIELDBATTERY]*4
        self.target_owned_buildings = {NEXUS:1, self.build_order[0]:1}
        self.lock = asyncio.Lock()


    async def on_step(self, iteration):
        # what to do every step
        await self.distribute_workers()  # in sc2/bot_ai.py
        # await self.build_pylons()  # pylons are protoss supply buildings

        if iteration % 10 == 0:
            await self.build_in_order()
            await self.aquire_income()

    async def build_in_order(self):
        if len(self.build_order) > 0 and self.can_afford(self.build_order[0]):
            if self.already_pending(self.build_order[0]) + len(self.units(self.build_order[0]).owned.ready) < self.target_owned_buildings[self.build_order[0]]:
                if self.build_order[0] is ASSIMILATOR:
                    if await self.build_gas():
                        self.increment_order()
                else:
                    location = self.getLocation(self.build_order[0])
                    if not location is None and self.valid_build_permit(self.build_order[0]):
                        r = None
                        if self.build_order[0] == PYLON:# and self.target_owned_buildings[PYLON] == 1:
                            r = await self.build(self.build_order[0], near=location, min_distance=10, max_distance=11)
                        else:
                            r = await self.build(self.build_order[0], near=location)
                        if not r == ActionResult.NotSupported:
                            self.increment_order()

    def valid_build_permit(self, unit):
        if unit == CYBERNETICSCORE:
            return len(self.units(GATEWAY).owned.ready) > 0
        elif unit == PHOTONCANNON:
            return len(self.units(FORGE).owned.ready) > 0
        elif unit == SHIELDBATTERY:
            return len(self.units(CYBERNETICSCORE).owned.ready) > 0

        return True

    def increment_order(self):
        self.build_order = self.build_order[1:]
        if len(self.build_order) > 0:
            if self.build_order[0] in self.target_owned_buildings:
                self.target_owned_buildings[self.build_order[0]] += 1
            else:
                self.target_owned_buildings[self.build_order[0]] = 1

    def getLocation(self, unit):
        if unit is PYLON:
            return self.units(NEXUS).owned[0]
        else:
            ls = self.units(PYLON).ready.owned
            return ls[0] if len(ls) > 0 else None

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


    async def aquire_income(self):
        # await self.build_gas()
        await self.build_workers()
        await self.use_chrono()

    async def use_chrono(self):
        for nexus in self.units(NEXUS).ready.owned:
            if (not nexus.is_idle) and nexus.energy >= 50:
                if not nexus.has_buff(CHRONOBOOSTENERGYCOST):
                    # abilities = await self.get_available_abilities(nexus)
                    # if EFFECT_CHRONOBOOSTENERGYCOST in abilities:
                    await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, nexus))

    async def build_gas(self):
        target_geyser_count = self.target_gas_income / self.gas_per_worker / self.workers_per_geyser
        needed_geyser_count = target_geyser_count - self.already_pending(ASSIMILATOR)
        if needed_geyser_count > 0:
            assimilators = self.units(ASSIMILATOR).owned
            for nexus in self.units(NEXUS).owned: #if safe ?
                available_vespenes = [ v for v in self.state.vespene_geyser.closer_than(10.0, nexus) if not assimilators.closer_than(1.0, v).exists]
                needed_geyser_count = target_geyser_count - self.already_pending(ASSIMILATOR)
                for i in range(min(math.ceil(needed_geyser_count), len(available_vespenes))):
                    if self.can_afford(ASSIMILATOR):
                        worker = self.select_build_worker(available_vespenes[i].position)
                        if not worker is None:
                            r = await self.do(worker.build(ASSIMILATOR, available_vespenes[i]))
                            return not r == ActionResult.NotSupported
        return False
    async def build_workers(self):
        # for all selectable nexus's that are finished building and has no orders
        for nexus in self.units(NEXUS).ready.idle.owned:
            vespenes = self.units(ASSIMILATOR).closer_than(10.0, nexus).owned
            workers_needed = sum([self.workers_per_geyser - vespene.assigned_harvesters for vespene in vespenes]) - nexus.surplus_harvesters
            if self.can_afford(PROBE) and workers_needed > 0:
                await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5 and not self.already_pending(PYLON):
            nexuses = self.units(NEXUS).ready.owned
            if nexuses.exists:
                if self.can_afford(PYLON):
                    await self.build(PYLON, near=nexuses.first)

run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Protoss, WabaBot()),
    Computer(Race.Terran, Difficulty.Easy)
], realtime=True)
