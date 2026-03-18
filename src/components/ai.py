from __future__ import annotations

import random
from typing import List, Optional, Tuple, TYPE_CHECKING

import numpy as np  # type: ignore
import tcod

from actions import Action, BumpAction, MeleeAction, MovementAction, WaitAction
import tile_types
import consts

if TYPE_CHECKING:
    from entity import Actor, BuildRemoveTile


class BaseAI(Action):
    def __init__(self, entity: Actor, previous_ai: Optional[BaseAI] = None):
        super().__init__(entity)
        self.previous_ai = previous_ai
        self.path_entity_block_cost = 5

    def perform(self) -> Optional[Action]:
        raise NotImplementedError()

    def get_path_to(self, dest_z: int, dest_x: int, dest_y: int) -> List[Tuple[int, int, int]]:
        gamemap = self.entity.gamemap
        graph = tcod.path.CustomGraph(shape=(gamemap.depth, gamemap.width, gamemap.height))

        cost_arr = np.array(gamemap.tiles["walkable"], dtype=np.int16)

        cost_arr = cost_arr | ((gamemap.tiles["tile_type"] == tile_types.TileType.EMPTY) & (gamemap.water_float >= consts.SWIMMABLE_THRESHOLD))
        dstairs_arr = gamemap.tiles["tile_type"] == tile_types.TileType.DOWN_STAIRS
        ustairs_arr = gamemap.tiles["tile_type"] == tile_types.TileType.UP_STAIRS

        graph.add_edges(edge_map=consts.EDGE_MAP, cost=cost_arr)
        graph.add_edge((-1, 0, 0), 1, cost=cost_arr, condition=dstairs_arr)
        graph.add_edge((1, 0, 0), 1, cost=cost_arr, condition=ustairs_arr)

        water_z1 = np.roll(gamemap.water_float >= consts.DROWNING_LEVEL_THRESHOLD, shift=1, axis=0)
        water_z = gamemap.water_float > 0
        down_water = water_z1 & water_z
        down_water[0] = False
        graph.add_edge((-1, 0, 0), 1, cost=cost_arr, condition=down_water)

        water_z1 = np.roll(gamemap.water_float > 0, shift=-1, axis=0)
        water_z = gamemap.water_float >= consts.DROWNING_LEVEL_THRESHOLD
        up_water = water_z1 & water_z
        up_water[-1] = False
        graph.add_edge((1, 0, 0), 1, cost=cost_arr, condition=up_water)

        for entity in self.entity.gamemap.entities:
            if entity.blocks_movement and cost_arr[entity.z, entity.x, entity.y] and \
                not (entity.z == dest_z and entity.x == dest_x and entity.y == dest_y):
                cost_arr[entity.z, entity.x, entity.y] = self.path_entity_block_cost

        pathfinder = tcod.path.Pathfinder(graph)
        pathfinder.add_root((self.entity.z, self.entity.x, self.entity.y))  # Start position.
        path: List[List[List[int]]] = pathfinder.path_to((dest_z, dest_x, dest_y))[1:].tolist()

        return [(index[0], index[1], index[2]) for index in path]


class MultiTurn(BaseAI):
    def __init__(self, entity: Actor, previous_ai: Optional[BaseAI], turns_remaining: int):
        super().__init__(entity, previous_ai)
        self.turns_remaining = turns_remaining
        self.halt = False
        

class MoveAI(BaseAI):
    def __init__(self, entity: Actor, target_zxy: Tuple[int, int, int], previous_ai: Optional[BaseAI] = None):
        super().__init__(entity, previous_ai)
        self.target_zxy = target_zxy
        self.path: List[Tuple[int, int, int]] = self.get_path_to(target_zxy[0], target_zxy[1], target_zxy[2])
        self.entity.ai = self
        self.init = False
        self.path_entity_block_cost = 0

    def perform(self) -> Optional[Action]:
        if not self.init:
            self.init = True
        elif self.path:
            dest_z, dest_x, dest_y = self.path.pop(0)
            if self.entity.gamemap.get_blocking_entity_at_location(dest_z, dest_x, dest_y):
                self.path = self.get_path_to(self.target_zxy[0], self.target_zxy[1], self.target_zxy[2])
                if self.path:
                    dest_z, dest_x, dest_y = self.path.pop(0)
                else:
                    self.entity.ai = self.previous_ai
                    return
            return MovementAction(self.entity, dest_z - self.entity.z, dest_x - self.entity.x, dest_y - self.entity.y).perform()
        else:
            self.entity.ai = self.previous_ai
            # return WaitAction(self.entity).perform()


class BuildRemoveAI(BaseAI):
    def __init__(self, entity: Actor, previous_ai: Optional[BaseAI]):
        super().__init__(entity, previous_ai)
        self.work_item = None
        self.turns_remaining = None
        self.path = []
        self.entity.busy = True
        self.halt = False
        self.path_entity_block_cost = 0
        
    def perform(self) -> Optional[Action]:
        if self.halt:
            self.entity.ai = self.previous_ai
            self.entity.busy = False
            if self.work_item:
                self.entity.jobs.appendleft(self.work_item)  
        elif self.path:
            dest_z, dest_x, dest_y = self.path.pop(0)
            return MovementAction(self.entity, dest_z - self.entity.z, dest_x - self.entity.x, dest_y - self.entity.y).perform()
        elif self.work_item:
            n_tiles = self.engine.game_map.get_neighbor_tiles(self.entity.z, self.entity.x, self.entity.y)
            if (self.work_item.z, self.work_item.x, self.work_item.y) in n_tiles:
                if self.turns_remaining <= 0:
                    self.engine.message_log.add_message(f"{self.work_item.name} complete")
                    self.work_item.done()
                    self.engine.game_map.entities.remove(self.work_item)
                    self.engine.game_map.work_items.remove(self.work_item)
                    self.work_item = None
                else:
                    self.work_item.turns_remaining -= 1
                    self.turns_remaining -= 1
                    return WaitAction(self.entity).perform()
            else:
                self.work_item = None
        elif len(self.entity.jobs) > 0:
            self.work_item = self.entity.jobs.popleft()
            self.turns_remaining = self.work_item.turns_remaining
            self.path = self.get_path_to(self.work_item.z, self.work_item.x, self.work_item.y)[:-1]
        else:
            self.entity.ai = self.previous_ai
            self.entity.busy = False
        

class ConfusedEnemy(MultiTurn):
    """
    A confused enemy will stumble around aimlessly for a given number of turns, then revert back to its previous AI.
    If an actor occupies a tile it is randomly moving into, it will attack.
    """

    def perform(self) -> Optional[Action]:
        # Revert the AI back to the original state if the effect has run its course.
        if self.turns_remaining <= 0:
            self.engine.message_log.add_message(
                f"The {self.entity.name} is no longer confused."
            )
            self.entity.ai = self.previous_ai
        else:
            # Pick a random direction
            direction_x, direction_y = random.choice(
                [
                    (-1, -1),  # Northwest
                    (0, -1),  # North
                    (1, -1),  # Northeast
                    (-1, 0),  # West
                    (1, 0),  # East
                    (-1, 1),  # Southwest
                    (0, 1),  # South
                    (1, 1),  # Southeast
                ]
            )

            self.turns_remaining -= 1

            # The actor will either try to move or attack in the chosen random direction.
            # Its possible the actor will just bump into the wall, wasting a turn.
            return BumpAction(self.entity, direction_x, direction_y,).perform()


class HostileEnemy(BaseAI):
    def __init__(self, entity: Actor, previous_ai: Optional[BaseAI] = None):
        super().__init__(entity, previous_ai)
        self.path: List[Tuple[int, int]] = []

    def perform(self) -> Optional[Action]:
        if self.entity in self.engine.playable_entities:
            targets = list(self.engine.game_map.actors - set(self.engine.playable_entities))
            # targets = []
        else:
            targets = self.engine.playable_entities
        min_distance = 9999
        min_target = None
        min_dx = None
        min_dy = None
        for target in targets:
            if target.is_alive and target.z == self.entity.z:
                dx = target.x - self.entity.x
                dy = target.y - self.entity.y
                distance = max(abs(dx), abs(dy))  # Chebyshev distance.
                if distance < min_distance:
                    min_distance = distance
                    min_target = target
                    min_dx = dx
                    min_dy = dy
        if min_target:
            target = min_target
            if self.engine.game_map.visible[self.entity.z][self.entity.x, self.entity.y] and \
                self.engine.game_map.visible[target.z][target.x, target.y]:
                if min_distance <= 1:
                    return MeleeAction(self.entity, min_dx, min_dy).perform()

                self.path = self.get_path_to(target.z, target.x, target.y)

            if self.path:
                dest_z, dest_x, dest_y = self.path.pop(0)
                return MovementAction(
                    self.entity, dest_z - self.entity.z, dest_x - self.entity.x, dest_y - self.entity.y,
                ).perform()

        return WaitAction(self.entity).perform()


class CritterAI(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity, None)
        self.idle = True
        self.idle_tick = 0
        self.plants = []
        self.plants_index = 0
        self.last_hp = None
        self.path = []
        
    def perform(self) -> Optional[Action]:
        z, x, y = self.entity.z, self.entity.x, self.entity.y
        if self.plants_index == 0:
            self.plants = []
            for plant in self.entity.parent.plants:
                if plant.z == z:
                    self.plants.append(((plant.z, plant.x, plant.y), self.entity.distance(plant.x, plant.y)))
            self.plants = sorted(self.plants, key=lambda x: x[1])
        if self.idle:
            if self.last_hp is None or self.last_hp == self.entity.fighter.hp:
                self.idle_tick += 1
            else:
                self.idle = False
                self.idle_tick = 0
                self.path = self.get_path_to(*self.plants[self.plants_index][0])
                self.plants_index = (self.plants_index + 1) % len(self.plants)
            self.last_hp = self.entity.fighter.hp
            if self.idle_tick > consts.CRITTER_HIDE_THRESHOLD:
                tiles = []
                for t in self.entity.parent.get_neighbor_tiles(z, x, y):
                    if self.entity.parent.tiles["tile_type"][*t] == tile_types.TileType.FLOOR:
                        tiles.append(t)
                return MovementAction(self.entity, *tiles[random.randint(0, len(tiles) - 1)]).perform()
        if self.path:
            dest_z, dest_x, dest_y = self.path.pop(0)
            if self.path:
                MovementAction(self.entity, dest_z - self.entity.z, dest_x - self.entity.x, dest_y - self.entity.y).perform()
                dest_z, dest_x, dest_y = self.path.pop(0)
                return MovementAction(self.entity, dest_z - self.entity.z, dest_x - self.entity.x, dest_y - self.entity.y).perform()
            else:
                return MovementAction(self.entity, dest_z - self.entity.z, dest_x - self.entity.x, dest_y - self.entity.y).perform()
        else:
            self.idle = True
