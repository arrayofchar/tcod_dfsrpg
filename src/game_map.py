from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

import numpy as np  # type: ignore
from queue import Queue
from tcod.console import Console

from entity import Actor, Item
import tile_types


class GameMap:
    def __init__(
        self, engine: Engine, depth: int, width: int, height: int, entities: Iterable[Entity] = ()
    ):
        self.engine = engine
        self.depth, self.width, self.height = depth, width, height
        self.tiles = np.full((depth, width, height), fill_value=tile_types.wall, order="F")
        self.entities = set(entities)

        self.visible = np.full(
            (depth, width, height), fill_value=False, order="F"
        )  # Tiles the player can currently see
        self.explored = np.full(
            (depth, width, height), fill_value=False, order="F"
        )  # Tiles the player has seen before
        self.cavein = np.full(
            (depth, width, height), fill_value=None, order="F"
        )  # True if tile touches edge tile

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
                if not (i == x and j == y) and \
                    self.in_bounds_x(i) and self.in_bounds_y(j):
                    tiles.append((z, i, j))
        return tiles

    def get_neighbor_tiles_include_z(self, z: int, x: int, y: int) -> List[Tuple(int, int, int)]:
        tiles = []
        for k in range(z - 1, z + 2):
            for i in range(x - 1, x + 2):
                for j in range(y - 1, y + 2):
                    if not (k == z and i == x and j == y) and self.in_bounds:
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
        # if map_mode:
        #     console.rgb[0 : cam_width, 0 : cam_height] = self.tiles["dark"][z][x : x + cam_width, y : y + cam_height]
        # else:
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

    def calc_cavein(self) -> None:
        wall = tile_types.wall
        floor = tile_types.floor
        q = Queue()
        for z in range(self.depth):
            for x in range(self.width):
                for y in range(self.height):
                    if z == 0 or self.depth - 1 or \
                        x == 0 or self.width - 1 or \
                        y == 0 or self.height - 1:
                        t = self.tiles[z, x, y]
                        if t == wall or t == floor:
                            self.cavein[z, x, y] = True
                        else:
                            self.cavein[z, x, y] = False
                        continue
                    self.check_cavein(q, z, x, y)
        while not q.empty():
            z, x, y = q.get()
            self.check_cavein(q, z, x, y)


    def check_cavein(self, q: Queue, z: int, x: int, y:int):
        t_neighbors = self.get_neighbor_tiles_include_z()
        q_flag = False
        for tn in t_neighbors:
            if self.cavein[tn]:
                self.cavein[z, x, y] = True
                break
            elif self.cavein[tn] is None:
                q_flag = True
        if not self.cavein[z, x, y]:
            if q_flag:
                q.put((z, x, y))
            else:
                self.cavein[z, x, y] = False