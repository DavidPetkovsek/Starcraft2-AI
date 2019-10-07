import sc2, math
from botbase import BetterBot as BotBase
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *

class WabaBot(BotBase):

    def __init__(self):
        super().__init__()
        self.target_mineral_income = 5*16
        self.target_gas_income = 4*6
        # self.build_order = [PYLON, GATEWAY, ASSIMILATOR, PYLON, ASSIMILATOR, CYBERNETICSCORE, GATEWAY, GATEWAY, PYLON, GATEWAY, FORGE] + [PHOTONCANNON]*10 + [PYLON] + [SHIELDBATTERY]*4
        # self.build_order = [PYLON, GATEWAY, ASSIMILATOR, PYLON, ASSIMILATOR, CYBERNETICSCORE, TWILIGHTCOUNCIL, STARGATE, ROBOTICSFACILITY, DARKSHRINE, PYLON, TEMPLARARCHIVE, FLEETBEACON, ROBOTICSBAY, FORGE, PYLON, PYLON] + [PHOTONCANNON]*12
        self.build_order = [PYLON, GATEWAY, ASSIMILATOR, PYLON, ASSIMILATOR]
        self.ideal_build_path = [ROBOTICSBAY]
        self.target_owned_buildings = {NEXUS:1, self.build_order[0]:1}
        self.last_updated = 0

    async def on_step(self, iteration):
        # what to do every step
        await self.distribute_workers()  # in sc2/bot_ai.py

        if iteration % 10 == 0:
            if len(self.build_order) + len(self.ideal_build_path) == 0:
                if self.supply_left < 5 and not self.already_pending(PYLON):
                    self.build_order.append(PYLON)
                else:
                    if len(self.units(ROBOTICSBAY).owned.ready) > 0:
                        for rf in self.units(ROBOTICSFACILITY).owned.ready.idle:
                            if self.can_afford(COLOSSUS):
                                await self.do(rf.train(COLOSSUS))
            else:
                await self.build_in_order()
            await self.build_upgrades()
            await self.aquire_income()
            # if iteration - self.last_updated < 500:
            #     self.update_build_order()

    async def build_upgrades(self):
        if self.can_afford(EXTENDEDTHERMALLANCE) and len(self.units(ROBOTICSBAY).owned.ready.idle) > 0 and not self.already_pending(EXTENDEDTHERMALLANCE):
            await self.do(self.units(ROBOTICSBAY).owned.ready.idle[0].research(EXTENDEDTHERMALLANCE))
        if self.can_afford(WARPGATERESEARCH) and len(self.units(CYBERNETICSCORE).owned.ready.idle) > 0 and not self.already_pending(WARPGATERESEARCH):
            await self.do(self.units(CYBERNETICSCORE).owned.ready.idle[0].research(WARPGATERESEARCH))

    async def build_in_order(self):
        if len(self.build_order) > 0:
            if self.can_afford(self.build_order[0]) and self.already_pending(self.build_order[0]) + len(self.units(self.build_order[0]).owned.ready) < self.target_owned_buildings[self.build_order[0]]:
                if self.build_order[0] is ASSIMILATOR:
                    if await self.build_gas():
                        self.increment_order()
                        return True
                else:
                    location = self.getLocation(self.build_order[0])
                    if not location is None and self.valid_build_permit(self.build_order[0]):
                        failures = []
                        if self.build_order[0] == PYLON:# and self.target_owned_buildings[PYLON] == 1:
                            failures = await self.build(self.build_order[0], near=location, min_distance=10, max_distance=11)
                        else:
                            failures = await self.build(self.build_order[0], near=location)
                        if failures:
                            print("failed to build, did not increment")
                            return False
                        self.increment_order()
                        return True
        else:
            self.update_build_order()

        # else:
        #     self.update_build_order()
        return False

    def update_build_order(self):
        if len(self.build_order) == 0 and len(self.ideal_build_path) > 0:
            self.build_order.append(self.ideal_build_path[0])
            self.ideal_build_path = self.ideal_build_path[1:]
        did_something = False
        while True:
            changed = False

            if len(self.build_order) > 0 and not self.valid_build_permit(self.build_order[0], include_in_progress=True):
                self.build_order = [self.get_permit_requirements(self.build_order[0])] + self.build_order
                changed = True
                did_something = True

            if not changed:
                break
        if did_something and len(self.build_order) > 0:
            if self.build_order[0] in self.target_owned_buildings:
                self.target_owned_buildings[self.build_order[0]] += 1
            else:
                self.target_owned_buildings[self.build_order[0]] = 1

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
                            return True
        return False

    async def build_workers(self):
        # for all selectable nexus's that are finished building and has no orders
        for nexus in self.units(NEXUS).ready.idle.owned:
            vespenes = self.units(ASSIMILATOR).closer_than(10.0, nexus).owned
            workers_needed = sum([self.workers_per_geyser - vespene.assigned_harvesters for vespene in vespenes]) - nexus.surplus_harvesters
            if self.can_afford(PROBE) and workers_needed > 0:
                await self.do(nexus.train(PROBE))

run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Protoss, WabaBot()),
    Computer(Race.Terran, Difficulty.Easy)
], realtime=True)
