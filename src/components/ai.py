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

    def perform(self) -> None:
        raise NotImplementedError()

    def get_path_to(self, dest_z: int, dest_x: int, dest_y: int) -> List[Tuple[int, int, int]]:
        gamemap = self.entity.gamemap
        graph = tcod.path.CustomGraph(shape=(gamemap.depth, gamemap.width, gamemap.height))

        cost_arr = np.array(gamemap.tiles["walkable"], dtype=np.int16)
        dstairs_arr = gamemap.tiles["tile_type"] == tile_types.TileType.DOWN_STAIRS
        ustairs_arr = gamemap.tiles["tile_type"] == tile_types.TileType.UP_STAIRS

        for entity in self.entity.gamemap.entities:
            # Check that an enitiy blocks movement and the cost isn't zero (blocking.)
            if entity.blocks_movement and cost_arr[entity.z, entity.x, entity.y]:
                # Add to the cost of a blocked position.
                # A lower number means more enemies will crowd behind each other in
                # hallways.  A higher number means enemies will take longer paths in
                # order to surround the player.
                cost_arr[entity.z, entity.x, entity.y] += 5

        graph.add_edges(edge_map=consts.EDGE_MAP, cost=cost_arr)
        graph.add_edge((-1, 0, 0), 1, cost=cost_arr, condition=dstairs_arr)
        graph.add_edge((1, 0, 0), 1, cost=cost_arr, condition=ustairs_arr)

        pathfinder = tcod.path.Pathfinder(graph)

        # """Compute and return a path to the target position.

        # If there is no valid path then returns an empty list.
        # """
        # # Copy the walkable array.
        # cost = np.array(self.entity.gamemap.tiles["walkable"][self.entity.z], dtype=np.int8)

        

        # # Create a graph from the cost array and pass that graph to a new pathfinder.
        # graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
        # pathfinder = tcod.path.Pathfinder(graph)

        pathfinder.add_root((self.entity.z, self.entity.x, self.entity.y))  # Start position.

        # Compute the path to the destination and remove the starting point.
        path: List[List[List[int]]] = pathfinder.path_to((dest_z, dest_x, dest_y))[1:].tolist()

        # Convert from List[List[int]] to List[Tuple[int, int]].
        return [(index[0], index[1], index[2]) for index in path]


class MultiTurn(BaseAI):
    def __init__(self, entity: Actor, previous_ai: Optional[BaseAI], turns_remaining: int):
        super().__init__(entity, previous_ai)
        self.turns_remaining = turns_remaining
        self.halt = False
        

class MoveAI(BaseAI):
    def __init__(self, entity: Actor, target_zxy: Tuple[int, int, int], previous_ai: Optional[BaseAI] = None):
        super().__init__(entity, previous_ai)
        self.path: List[Tuple[int, int, int]] = self.get_path_to(target_zxy[0], target_zxy[1], target_zxy[2])
        self.entity.ai = self

    def perform(self) -> None:
        if self.path:
            dest_z, dest_x, dest_y = self.path.pop(0)
            return MovementAction(self.entity, dest_z - self.entity.z, dest_x - self.entity.x, dest_y - self.entity.y).perform()
        else:
            self.entity.ai = self.previous_ai
            # return WaitAction(self.entity).perform()


class BuildRemoveAI(MultiTurn):
    def __init__(self, entity: Actor, previous_ai: Optional[BaseAI], turns_remaining: int, work_item: BuildRemoveTile):
        super().__init__(entity, previous_ai, turns_remaining)
        self.work_item = work_item
        self.entity.busy = True
        
    def perform(self) -> None:
        if self.turns_remaining <= 0 or self.halt:
            self.engine.message_log.add_message(f"Working on {self.work_item.name}")
            self.entity.ai = self.previous_ai
            self.entity.busy = False
            
            if self.turns_remaining <= 0:
                self.work_item.done()
                self.engine.game_map.entities.remove(self.work_item)
                self.engine.game_map.work_items.remove(self.work_item)
        else:
            self.work_item.turns_remaining -= 1
            self.turns_remaining -= 1
            return WaitAction(self.entity).perform()


class ConfusedEnemy(MultiTurn):
    """
    A confused enemy will stumble around aimlessly for a given number of turns, then revert back to its previous AI.
    If an actor occupies a tile it is randomly moving into, it will attack.
    """

    def perform(self) -> None:
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

    def perform(self) -> None:
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

                self.path = self.get_path_to(target.x, target.y)

            if self.path:
                dest_x, dest_y = self.path.pop(0)
                return MovementAction(
                    self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
                ).perform()

        return WaitAction(self.entity).perform()

