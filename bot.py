import sc2, math
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, CHRONOBOOSTENERGYCOST, EFFECT_CHRONOBOOSTENERGYCOST

#mineral collection rate for a single worker is 5 minerals per 5 seconds

class WabaBot(sc2.BotAI):


    def __init__(self):
        super().__init__()
        self.target_mineral_income = 5*16
        self.target_gas_income = 5*6
        self.mineral_per_worker = 5
        self.gas_per_worker = 5
        self.workers_per_geyser = 3

    async def on_step(self, iteration):
        # what to do every step
        await self.distribute_workers()  # in sc2/bot_ai.py
        await self.build_pylons()  # pylons are protoss supply buildings
        await self.aquire_income()

    async def aquire_income(self):
        await self.build_gas()
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
                            await self.do(worker.build(ASSIMILATOR, available_vespenes[i]))

    async def build_workers(self):
        # for all selectable nexus's that are finished building and has no orders
        for nexus in self.units(NEXUS).ready.idle.owned:
            vespenes = self.units(ASSIMILATOR).closer_than(10.0, nexus).owned
            workers_needed = sum([self.workers_per_geyser - vespene.assigned_harvesters for vespene in vespenes]) - nexus.surplus_harvesters
            if self.can_afford(PROBE) and workers_needed > 0:
                await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5 and not self.already_pending(PYLON):
            nexuses = self.units(NEXUS).ready
            if nexuses.exists:
                if self.can_afford(PYLON):
                    r = await self.build(PYLON, near=nexuses.first)
                    print(r)

run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Protoss, WabaBot()),
    Computer(Race.Terran, Difficulty.Easy)
], realtime=True)
