from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING, List, Tuple, Set, Dict

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

import numpy as np  # type: ignore
from queue import Queue
from tcod.console import Console

from entity import Actor, Item
import tile_types
import color

empty = tile_types.empty
wall = tile_types.wall

cavein_unit_dmg = 10

class GameMap:
    def __init__(
        self, engine: Engine, depth: int, width: int, height: int, entities: Iterable[Entity] = ()
    ):
        self.engine = engine
        self.depth, self.width, self.height = depth, width, height
        self.tiles = np.full((depth, width, height), fill_value=tile_types.wall, order="F")
        self.entities = set(entities)

        self.visible = np.full((depth, width, height), fill_value=False, order="F")
        self.explored = np.full((depth, width, height), fill_value=False, order="F")
        self.cavein = np.full((depth, width, height), fill_value=None, order="F")
        self.outside = np.full((width, height), fill_value=depth, order="F")

    @property
    def gamemap(self) -> GameMap:
        return self

    @property
    def actors(self) -> Iterator[Actor]:
        """Iterate over this maps living actors."""
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Actor) and entity.is_alive
        )

    @property
    def items(self) -> Iterator[Item]:
        yield from (entity for entity in self.entities if isinstance(entity, Item))

    def get_neighbor_tiles(self, z: int, x: int, y: int) -> List[Tuple(int, int, int)]:
        tiles = []
        for i in range(x - 1, x + 2):
            for j in range(y - 1, y + 2):
                if not (i == x and j == y) and self.in_bounds_no_z(i, j):
                    tiles.append((z, i, j))
        return tiles

    def get_blocking_entity_at_location(
        self, location_z: int, location_x: int, location_y: int,
    ) -> Optional[Entity]:
        for entity in self.entities:
            if (
                entity.blocks_movement
                and entity.z == location_z
                and entity.x == location_x
                and entity.y == location_y
            ):
                return entity

        return None

    def get_actor_at_location(self, z: int, x: int, y: int) -> Optional[Actor]:
        for actor in self.actors:
            if actor.x == x and actor.y == y and actor.z == z:
                return actor

        return None

    def in_bounds_x(self, x: int):
        return 0 <= x < self.width
    
    def in_bounds_y(self, y: int):
        return 0 <= y < self.height

    def in_bounds_z(self, z: int):
        return 0 <= z < self.depth

    def in_bounds_no_z(self, x: int, y: int) -> bool:
        return self.in_bounds_x(x) and self.in_bounds_y(y)

    def in_bounds(self, z: int, x: int, y: int) -> bool:
        return self.in_bounds_z(z) and self.in_bounds_x(x) and self.in_bounds_y(y)

    def render(self, console: Console, z: int, x: int, y: int, map_mode: bool) -> None:
        """
        Renders the map.

        If a tile is in the "visible" array, then draw it with the "light" colors.
        If it isn't, but it's in the "explored" array, then draw it with the "dark" colors.
        Otherwise, the default is "SHROUD".
        """

        cam_width = self.engine.cam_width
        cam_height = self.engine.cam_height
        if map_mode:
            default_type = self.tiles["dark"][z][x : x + cam_width, y : y + cam_height]
        else:
            default_type = tile_types.SHROUD
            
        console.rgb[0 : cam_width, 0 : cam_height] = np.select(
            condlist=[
                self.visible[z][x : x + cam_width, y : y + cam_height],
                self.explored[z][x : x + cam_width, y : y + cam_height],
            ],
            choicelist=[
                self.tiles["light"][z][x : x + cam_width, y : y + cam_height],
                self.tiles["dark"][z][x : x + cam_width, y : y + cam_height],
            ],
            default=default_type,
        )

        entities_sorted_for_rendering = sorted(
            self.entities, key=lambda x: x.render_order.value
        )

        for entity in entities_sorted_for_rendering:
            # Only print entities that are in the FOV
            if (self.engine.cam_x <= entity.x < self.engine.cam_x + cam_width) and \
                (self.engine.cam_y <= entity.y < self.engine.cam_y + cam_height) and \
                entity.z == z and \
                (map_mode or self.visible[z][entity.x, entity.y]):
                console.print(
                    x=entity.x - self.engine.cam_x, y=entity.y - self.engine.cam_y, string=entity.char, fg=entity.color
                )


    def get_cavein_neighbors(self, visited: Set, z: int, x: int, y: int) -> List[Tuple(int, int ,int)]:
        tiles = []
        if self.in_bounds(z, x - 1, y) and (z, x - 1, y) not in visited and self.tiles[z, x - 1, y] != empty:
            tiles.append((z, x - 1, y))
        if self.in_bounds(z, x + 1, y) and (z, x + 1, y) not in visited and self.tiles[z, x + 1, y] != empty:
            tiles.append((z, x + 1, y))
        if self.in_bounds(z, x, y - 1) and (z, x, y - 1) not in visited and self.tiles[z, x, y - 1] != empty:
            tiles.append((z, x, y - 1))
        if self.in_bounds(z, x, y + 1) and (z, x, y + 1) not in visited and self.tiles[z, x, y + 1] != empty:
            tiles.append((z, x, y + 1))
        if self.in_bounds(z - 1, x, y) and (z - 1, x, y) not in visited and self.tiles[z - 1, x, y] == wall:
            tiles.append((z - 1, x, y))
        if self.in_bounds(z + 1, x, y) and (z + 1, x, y) not in visited and \
            self.tiles[z, x, y] == wall and self.tiles[z + 1, x, y] != empty:
            tiles.append((z + 1, x, y))
        return tiles

    def cavein_init(self) -> None:
        q = Queue()
        visited = set()
        for z in range(self.depth):
            for x in range(self.width):
                for y in range(self.height):
                    if self.tiles[z, x, y] == empty:
                        self.cavein[z, x, y] = False
                    elif z == 0 or z == self.depth - 1 or \
                        x == 0 or x == self.width - 1 or \
                        y == 0 or y == self.height - 1:
                        q.put((z, x, y))
        while not q.empty():
            z, x, y = q.get()
            self.cavein[z, x, y] = True
            visited.add((z, x, y))
            for nz, nx, ny in self.get_cavein_neighbors(visited, z, x, y):
                q.put((nz, nx, ny))

    def get_cavein_dmg_tiles(self) -> Dict(Tuple(int, int, int), int):
        dmg_tiles_d = {}
        for z in range(self.depth):
            for x in range(self.width):
                for y in range(self.height):
                    if not self.cavein[z, x, y] and self.tiles[z, x, y] != empty:
                        self.tiles[z, x, y] = empty
                        cur_z = z - 1
                        while cur_z >= 0:
                            if self.tiles[cur_z, x, y] != empty:
                                break
                            else:
                                cur_z -= 1
                        if cur_z >= 0:
                            if (cur_z, x, y) in dmg_tiles_d:
                                dmg_tiles_d[cur_z, x, y] += 1
                            else:
                                dmg_tiles_d[cur_z, x, y] = 1
                        if self.outside[x, y] == z:
                            self.outside[x, y] = cur_z
        return dmg_tiles_d

    def apply_cavein_dmg(self, dmg_tiles_d: Dict(Tuple(int, int, int), int)) -> None:
        for a in self.actors:
            if (a.z, a.x, a.y) in dmg_tiles_d:
                damage = cavein_unit_dmg - a.fighter.defense
                if damage > 0:
                    self.engine.message_log.add_message(f"Falling debris for {damage} hit points.", color.enemy_atk)
                    a.fighter.hp -= damage
                else:
                    self.engine.message_log.add_message("Falling debris but does no damage.", color.enemy_atk)

    def outside_init(self) -> None:
        for x in range(self.width):
            for y in range(self.height):
                cur_z = self.depth - 1
                while cur_z >= 0:
                    if self.tiles[cur_z, x, y] != empty:
                        break
                    else:
                        cur_z -= 1
                self.outside[x, y] = cur_z






    # def cavein_count_tiles(self, q: Queue) -> int:
    #     cur_tile_count = 0
    #     for k in range(self.depth):
    #         for i in range(self.width):
    #             for j in range(self.height):
    #                 if self.cavein[k, i, j] is not None:
    #                     cur_tile_count += 1
    #                 else:
    #                     q.put((k, i, j))
    #     return cur_tile_count

    # def process_cavein(self) -> None:
    #     d = {}
    #     q = Queue()
    #     self.calc_cavein(d)

    #     total_tile_count = self.depth * self.width * self.height
    #     cur_tile_count = self.cavein_count_tiles(q)
    #     last_count = 0
    #     while cur_tile_count < total_tile_count and last_count != cur_tile_count:
    #         last_count = cur_tile_count
    #         while not q.empty():
    #             z, x, y = q.get()
    #             if self.cavein[z, x, y] is None:
    #                 self.check_cavein(q, d, z, x, y)
    #         cur_tile_count = self.cavein_count_tiles(q)
    #     # for k in range(self.depth):
    #     #     for i in range(self.width):
    #     #         for j in range(self.height):
    #     #             if self.cavein[k, i, j] is None:
    #     #                 self.cavein[k, i, j] = False
        
                

    # def calc_cavein(self, d: dict) -> None:
    #     empty = tile_types.empty
    #     q = Queue()
    #     for z in range(self.depth):
    #         for x in range(self.width):
    #             for y in range(self.height):
    #                 if self.tiles[z, x, y] == empty:
    #                     self.cavein[z, x, y] = False
    #                     continue
    #                 if z == 0 or z == self.depth - 1 or \
    #                     x == 0 or x == self.width - 1 or \
    #                     y == 0 or y == self.height - 1:
    #                     self.cavein[z, x, y] = True
    #                     # self.cavein[z, x, y] = False if self.tiles[z, x, y] == empty else True
    #                     continue
    #                 self.check_cavein(q, d, z, x, y)
    #     # print(q.qsize())
    #     while not q.empty():
    #         z, x, y = q.get()
    #         # print(z, x, y)
    #         if self.cavein[z, x, y] is None:
    #             self.check_cavein(q, d, z, x, y)


    # def check_cavein(self, q: Queue, d: dict, z: int, x: int, y:int):
    #     floor = tile_types.floor
    #     wall = tile_types.wall
    #     t_neighbors, cavein_vals = self.cavein_neighbors_tuple(z, x, y)
    #     q_flag = False
    #     for tz, tx, ty in t_neighbors:
    #         if self.tiles[z, x, y] == floor and \
    #             (tz== z + 1 or (tz == z - 1 and self.tiles[tz, tx, ty] != wall)):
    #             continue
    #         elif self.tiles[z, x, y] == wall and \
    #             (tz == z - 1 and self.tiles[tz, tx, ty] == floor):
    #             continue
    #         if self.cavein[tz, tx, ty]:
    #             self.cavein[z, x, y] = True
    #             break
    #         elif self.cavein[tz, tx, ty] is None:
    #             q_flag = True
    #     if q_flag:
    #         if self.cavein[z, x, y] is None:
    #             # print(cavein_vals)
    #             if (z, x, y) in d:
    #                 # print(d[(z, x, y)])
    #                 if d[(z, x, y)] != cavein_vals:
    #                     d[(z, x, y)] = cavein_vals
    #                     q.put((z, x, y))
    #                 else:
    #                     self.cavein[z, x, y] = False
    #                     del d[(z, x, y)]
    #             else:
    #                 d[(z, x, y)] = cavein_vals
    #                 q.put((z, x, y))
    #     else:
    #         self.cavein[tz, tx, ty] = False
