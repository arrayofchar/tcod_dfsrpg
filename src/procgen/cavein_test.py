from __future__ import annotations

import random
from typing import Dict, Iterator, List, Tuple, TYPE_CHECKING

import tcod
import random
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
    rooms.append(RectangularRoom(center[0] - 3, center[1] - 2, 15, 15))
    rooms.append(RectangularRoom(center[0], center[1], 2, int(map_height / 2)))
    # rooms.append(RectangularRoom(center[0], -1, 2, map_height + 1))

    map.tiles[:] = tile_types.wall
    map.tiles[ground_z + 1:] = tile_types.empty
    map.tiles[ground_z] = tile_types.floor

    map.tiles[ground_z, center[0] + 1, map_height - 2] = tile_types.wall
    # map.tiles[ground_z, center[0] + 1, center[1] + 5] = tile_types.wall

    for i, r in enumerate(rooms):
        map.tiles[obj_z][r.inner] = tile_types.floor
        if i == 0:
            map.tiles[ground_z - 1][r.inner] = tile_types.floor
    map.tiles[ground_z, *center] = tile_types.up_stairs
    map.tiles[ground_z + 1, *center] = tile_types.down_stairs
    map.tiles[ground_z - 1, center[0]-1, center[1]-1] = tile_types.up_stairs
    map.tiles[ground_z, center[0]-1, center[1]-1] = tile_types.down_stairs

    # for i in range(10):
    #     map.tiles[ground_z - 1, 1 + i, 5] = tile_types.floor
    # map.tiles[ground_z - 1][RectangularRoom(10, 1, 10, 10).inner] = tile_types.floor
    # p = p_entities[0]
    # p.place(ground_z - 1, 1, 5)

    for i, p in enumerate(p_entities):
        p.place(ground_z + i, *center)

    return map

def place_entities(engine: Engine) -> None:
    ground_z = int(engine.game_map.depth / 3)

    # engine.game_map.remove_tile(1, 6, 6)
    # engine.game_map.remove_tile(2, 41, 40)
    # engine.game_map.remove_tile(2, 41, 2)
    # engine.game_map.remove_tile(1, 41, 41)

    # engine.game_map.tiles["hp"][2, 45, 25] = 0

    l_src = entity_factories.light_src.spawn(engine.game_map, 0, 39, 30)
    # l_src = entity_factories.light_src.spawn(engine.game_map, 0, 7, 5)
    l_src.effect.activate()
    # l_src.effect.deactivate()
    l_src = entity_factories.light_src.spawn(engine.game_map, 0, 47, 30)
    # l_src = entity_factories.light_src.spawn(engine.game_map, 0, 15, 5)
    l_src.effect.activate()
    
    entity_factories.troll.spawn(engine.game_map, 0, 9, 5)

    # entity_factories.smoke.spawn(engine.game_map, 0, 40, 25, density=10000)
    # entity_factories.fire.spawn(engine.game_map, 1, 41, 48)
    # entity_factories.fire.spawn(engine.game_map, 0, 40, 34)
    # entity_factories.aquifer.spawn(engine.game_map, 1, 40, 34)

    for i in range(20):
        x = random.randint(0, engine.game_map.width - 1)
        y = random.randint(0, engine.game_map.height - 1)
        entity_factories.tall_grass.spawn(engine.game_map, ground_z, x, y)

    for i in range(20):
        x = random.randint(0, engine.game_map.width - 1)
        y = random.randint(0, engine.game_map.height - 1)
        entity_factories.shrub.spawn(engine.game_map, ground_z, x, y)

    # for i in range(5):
    #     x = random.randint(0, engine.game_map.width - 1)
    #     y = random.randint(0, engine.game_map.height - 1)
    #     entity_factories.critter.spawn(engine.game_map, ground_z, x, y)

    for i in range(5):
        x = random.randint(0, engine.game_map.width - 1)
        y = random.randint(0, engine.game_map.height - 1)
        entity_factories.predator.spawn(engine.game_map, ground_z, x, y)
