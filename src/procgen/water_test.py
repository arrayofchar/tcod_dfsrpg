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
    """Water testing area."""
    ground_z = int(map_depth / 3)
    obj_z = int(map_depth / 2)
    center = (int(map_width / 2), int(map_height / 2))

    p_entities = engine.playable_entities
    map = GameMap(engine, map_depth, map_width, map_height, entities=[*p_entities])
    rooms = []
    rooms.append(RectangularRoom(center[0] - 3, center[1] - 2, 15, 15))
    # rooms.append(RectangularRoom(center[0], center[1], 2, int(map_height / 2)))
    # rooms.append(RectangularRoom(center[0], -1, 2, map_height + 1))

    map.tiles[:] = tile_types.wall

    for i, r in enumerate(rooms):
        if i == 0:
            map.tiles[ground_z][r.inner] = tile_types.floor
            for z in range(ground_z + 1, map_depth - 2):
                map.tiles[z][r.inner] = tile_types.empty
    
    map.tiles[ground_z, *center] = tile_types.up_stairs
    map.tiles[ground_z + 1, *center] = tile_types.down_stairs
    # map.tiles[ground_z - 1, center[0]-1, center[1]-1] = tile_types.up_stairs
    # map.tiles[ground_z, center[0]-1, center[1]-1] = tile_types.down_stairs

    p = p_entities[engine.p_index]
    p.place(ground_z, *center)

    return map
