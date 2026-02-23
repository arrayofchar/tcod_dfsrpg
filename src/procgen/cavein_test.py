from __future__ import annotations

import random
from typing import Dict, Iterator, List, Tuple, TYPE_CHECKING

import tcod
import entity_factories
from game_map import GameMap
import tile_types
from procgen import RectangularRoom

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


def generate_map(
    map_depth: int,
    map_width: int,
    map_height: int,
    engine: Engine,
) -> GameMap:
    """Cave-in testing area."""
    ground_z = int(map_depth / 3)
    obj_z = int(map_depth / 2)
    center = (int(map_width / 2), int(map_height / 2))

    p_entities = engine.playable_entities
    map = GameMap(engine, map_depth, map_width, map_height, entities=[*p_entities])
    rooms = []
    rooms.append(RectangularRoom(center[0] - 3, center[1] - 2, 6, 4))
    rooms.append(RectangularRoom(center[0], center[1], 2, int(map_height / 2)))
    # rooms.append(RectangularRoom(center[0], -1, 2, map_height + 1))

    map.tiles[:] = tile_types.wall
    map.tiles[ground_z + 1:] = tile_types.empty
    map.tiles[ground_z] = tile_types.floor

    map.tiles[ground_z, center[0] + 1, map_height - 2] = tile_types.wall
    # map.tiles[ground_z, center[0] + 1, center[1] + 5] = tile_types.wall

    for i, r in enumerate(rooms):
        map.tiles[obj_z][r.inner] = tile_types.floor
        # if i == 0:
        #     map.tiles[obj_z + 1][r.inner] = tile_types.wall
    map.tiles[ground_z, *center] = tile_types.up_stairs
    map.tiles[ground_z + 1, *center] = tile_types.down_stairs

    p = p_entities[engine.p_index]
    p.place(ground_z, *center)

    return map
