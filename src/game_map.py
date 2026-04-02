from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING, List, Tuple, Set, Dict

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

from enum import IntEnum
import numpy as np  # type: ignore
from collections import deque
from tcod.console import Console
import exceptions

from entity import Actor, Item, BuildRemoveTile, Particle, Elemental, Fire, Aquifer, Fixture
import tile_types
import consts
import color

empty = tile_types.TileType.EMPTY
wall = tile_types.TileType.WALL
window = tile_types.TileType.WINDOW
door = tile_types.TileType.DOOR
floor = tile_types.TileType.FLOOR
dstairs = tile_types.TileType.DOWN_STAIRS
ustairs = tile_types.TileType.UP_STAIRS


class GameMap:
    def __init__(
        self, engine: Engine, depth: int, width: int, height: int, entities: Iterable[Entity] = ()
    ):
        self.engine = engine
        self.depth, self.width, self.height = depth, width, height
        self.tiles = np.full((depth, width, height), fill_value=tile_types.empty, order="F")
        self.entities = set(entities) # entries deleted
        self.actors = set(entities)
        
        self.items = set()
        self.particles = set()
        self.work_items = set()
        self.elementals = set()
        self.fixtures = set()
        self.plants = set()

        self.light_fov = {} # entries not deleted
        self.fire_orig_light = {}

        self.visible = np.full((depth, width, height), fill_value=False, order="F")
        self.explored = np.full((depth, width, height), fill_value=False, order="F")
        self.cavein = np.full((depth, width, height), fill_value=None, order="F")
        self.outside = np.full((width, height), fill_value=int(depth), dtype=np.int16, order="F")
        self.on_fire = np.full((depth, width, height), fill_value=False, order="F")

        self.light = [np.full((depth, width, height), fill_value=True, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),]

        self.water = [np.full((depth, width, height), fill_value=False, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),]
        self.water_float = np.full((depth, width, height), fill_value=0.0, dtype=np.float16, order="F")

        self.cavein_dep_graph = {} # edge cavein=True tiles don't have entries

        self.resource_counts = {
            tile_types.Resource.WOOD: 0,
            tile_types.Resource.STONE: 0,
            tile_types.Resource.COPPER: 0,
            tile_types.Resource.TIN: 0,
            tile_types.Resource.ZINC: 0,
            tile_types.Resource.IRON: 0,
        }

    @property
    def gamemap(self) -> GameMap:
        return self

    @property
    def work_blocking_entities(self) -> Iterator[Entity]:
        yield from (entity for entity in self.entities \
            if not isinstance(entity, Particle) and not isinstance(entity, BuildRemoveTile))


    def set_light_tile(self, z: int, x: int, y:int, level: int) -> None:
        for i, light_matrix in enumerate(self.light):
            if i == level:
                light_matrix[z, x, y] = True
            else:
                light_matrix[z, x, y] = False

    def get_light_tile(self, z: int, x: int, y:int) -> int:
        for i, light_matrix in enumerate(self.light):
            if light_matrix[z, x, y]:
                return i

    def set_water_tile(self, z: int, x: int, y:int, level: float) -> None:
        self.water_float[z, x, y] = level
        if level == 0:
            for water_matrix in self.water:
                water_matrix[z, x, y] = False
        else:
            level = min(int(level), 4)
            for i, water_matrix in enumerate(self.water):
                if i == level:
                    water_matrix[z, x, y] = True
                else:
                    water_matrix[z, x, y] = False

    def get_water_tile(self, z: int, x: int, y: int) -> float:
        return self.water_float[z, x, y]

    def get_neighbor_tiles(self, z: int, x: int, y: int) -> List[Tuple(int, int, int)]:
        tiles = []
        for i in range(x - 1, x + 2):
            for j in range(y - 1, y + 2):
                if not (i == x and j == y) and self.in_bounds_no_z(i, j):
                    tiles.append((z, i, j))
        return tiles

    def get_z_neighbor_tiles(self, z: int, x: int, y: int) -> List[Tuple(int, int, int)]:
        tiles = []
        for k in range (z - 1, z + 2):
            for i in range(x - 1, x + 2):
                for j in range(y - 1, y + 2):
                    if not (k == z and i == x and j == y) and self.in_bounds(k, i, j):
                        tiles.append((k, i, j))
        return tiles

    def get_all_entities_at_location(self, z: int, x: int, y: int) -> List[Optional[Entity]]:
        entities = []
        for entity in self.entities:
            if (entity.z == z and entity.x == x and entity.y == y):
                entities.append(entity)
        return entities

    def get_blocking_entity_at_location(self, location_z: int, location_x: int, location_y: int) -> Optional[Entity]:
        for entity in self.entities:
            if (entity.blocks_movement
                and entity.z == location_z
                and entity.x == location_x
                and entity.y == location_y):
                return entity
        return None

    def get_actor_at_location(self, z: int, x: int, y: int) -> Optional[Actor]:
        for actor in self.actors:
            if actor.is_alive and actor.z == z and actor.x == x and actor.y == y:
                return actor
        return None

    def get_particles_at_location(self, z: int, x: int, y: int) -> List[Optional[Particle]]:
        ret_list = []
        for p in self.particles:
            if p.z == z and p.x == x and p.y == y:
                ret_list.append(p)
        return ret_list

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

    def is_edge_tile(self, z: int, x: int, y: int) -> bool:
        return z == 0 or z == self.depth - 1 or \
                x == 0 or x == self.width - 1 or \
                y == 0 or y == self.height - 1

    def check_fire_orig_light(self, z: int, x: int, y: int) -> None:
        if (z, x, y) in self.fire_orig_light:
            self.set_light_tile(z, x, y, \
                min(self.fire_orig_light[z, x, y], self.get_light_tile(z, x, y)))
            del self.fire_orig_light[z, x, y]

    def update_tiles(self) -> None:
        indexes = np.argwhere(self.on_fire)
        for z, x, y in indexes:
            if self.get_water_tile(z, x, y) > 0:
                self.on_fire[z, x, y] = False
                self.check_fire_orig_light(z, x, y)
            else:
                self.tiles["hp"][z, x, y] -= consts.FIRE_DMG

        indexes = np.argwhere((self.tiles["tile_type"] != empty) & (self.tiles["hp"] <= 0))
        for z, x, y in indexes:
            self.remove_tile(z, x, y)
            self.check_fire_orig_light(z, x, y)
        
        np.place(self.light[4], self.on_fire, True)
        np.place(self.light[3], self.on_fire, False)
        np.place(self.light[2], self.on_fire, False)
        np.place(self.light[1], self.on_fire, False)
        np.place(self.light[0], self.on_fire, False)

    def handle_elementals(self) -> None:
        for elem in list(self.elementals):
            if isinstance(elem, Fire):
                fire = elem
                if fire.turn_count >= fire.duration or \
                        self.get_water_tile(fire.z, fire.x, fire.y) >= consts.DROWNING_LEVEL_THRESHOLD:
                    self.entities.remove(fire)
                    self.elementals.remove(fire)
                else:
                    fire.handle_turn()
            elif isinstance(elem, Aquifer):
                aquifer = elem
                if aquifer.turn_count >= aquifer.duration:
                    self.entities.remove(aquifer)
                    self.elementals.remove(aquifer)
                else:
                    aquifer.handle_turn()

    def handle_entities(self) -> None:
        for entity in list(self.entities):
            z, x, y = entity.z, entity.x, entity.y
            # handle fall
            if entity not in self.work_items and self.tiles["tile_type"][z, x, y] == tile_types.TileType.EMPTY and \
                    self.get_water_tile(z, x, y) == 0:
                cur_z = z - 1
                while cur_z >= 0:
                    if self.tiles["tile_type"][cur_z, x, y] != tile_types.TileType.EMPTY:
                        break
                    else:
                        cur_z -= 1
                if cur_z >= 0:
                    entity.z = cur_z # teleport a after damage calculation
                    if isinstance(entity, Actor):
                        damage = consts.FALL_DMG_MULT * (entity.z - cur_z)
                        if damage > 0:
                            self.engine.message_log.add_message(f"Fallen for {damage} hit points.")
                            entity.fighter.hp -= damage
                        else:
                            self.engine.message_log.add_message("Fallen but does no damage.")
                else:
                    pass
                    # self.entities.remove(entity)
            # handle actors
            if isinstance(entity, Actor):
                if self.get_water_tile(z, x, y) >= consts.DROWNING_LEVEL_THRESHOLD:
                    entity.fighter.breath -= consts.BREATH_LOSS
                else:
                    entity.fighter.breath = entity.fighter.max_breath
                if entity.fighter.on_fire:
                    if self.get_water_tile(z, x, y) >= consts.SWIMMABLE_THRESHOLD:
                        entity.fighter.on_fire = False
                    else:
                        entity.fighter.take_damage(consts.FIRE_DMG)
                if self.on_fire[z, x, y]:
                    entity.fighter.fire_buildup += 1
                else:
                    entity.fighter.fire_buildup -= 1
                if entity.ai:
                    try:
                        entity.ai.perform()
                    except exceptions.Impossible:
                        pass  # Ignore impossible action exceptions from AI.


    def render(self, console: Console, z: int, x: int, y: int, map_mode: bool) -> None:
        """
        Renders the map.

        If a tile is in the "visible" array, then draw it with the "light" colors.
        If it isn't, but it's in the "explored" array, then draw it with the "dark" colors.
        Otherwise, the default is "SHROUD".
        """

        cam_width = self.engine.cam_width
        cam_height = min(self.engine.cam_height, self.height)
        if map_mode:
            default_type = self.tiles["dark"][z][x : x + cam_width, y : y + cam_height]
        else:
            # default_type = self.tiles["dark"][z][x : x + cam_width, y : y + cam_height]
            default_type = tile_types.SHROUD
            
        console.rgb[0 : cam_width, 0 : cam_height] = np.select(
            condlist=[
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.water[4][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.water[3][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.water[2][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.water[1][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.water[0][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.on_fire[z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.light[4][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.light[3][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.light[2][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.light[1][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.light[0][z][x : x + cam_width, y : y + cam_height]),
                self.explored[z][x : x + cam_width, y : y + cam_height],
            ],
            choicelist=[
                self.tiles["water4"][z][x : x + cam_width, y : y + cam_height],
                self.tiles["water3"][z][x : x + cam_width, y : y + cam_height],
                self.tiles["water2"][z][x : x + cam_width, y : y + cam_height],
                self.tiles["water1"][z][x : x + cam_width, y : y + cam_height],
                self.tiles["water0"][z][x : x + cam_width, y : y + cam_height],
                self.tiles["fire_color"][z][x : x + cam_width, y : y + cam_height],
                self.tiles["light4"][z][x : x + cam_width, y : y + cam_height],
                self.tiles["light3"][z][x : x + cam_width, y : y + cam_height],
                self.tiles["light2"][z][x : x + cam_width, y : y + cam_height],
                self.tiles["light1"][z][x : x + cam_width, y : y + cam_height],
                self.tiles["light0"][z][x : x + cam_width, y : y + cam_height],
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


    def all_init(self) -> None:
        self.outside_init()
        self.cavein_init()
        self.light_init()


    def get_cavein_neighbors(self, q_set: Set, z: int, x: int, y: int) -> List[Tuple(int, int ,int)]:
        tiles = []
        if self.in_bounds_x(x - 1) and self.cavein[z, x - 1, y] is not False:
            if self.cavein[z, x - 1, y]:
                if (z, x - 1, y) in self.cavein_dep_graph:
                    if (z, x, y) in self.cavein_dep_graph and \
                        (z, x - 1, y) not in self.cavein_dep_graph[(z, x, y)]:
                        self.cavein_dep_graph[(z, x - 1, y)].add((z, x, y))
                elif not self.is_edge_tile(z, x - 1, y):
                    self.cavein_dep_graph[(z, x - 1, y)] = set([(z, x, y)])
            elif (z, x - 1, y) not in q_set:
                tiles.append((z, x - 1, y))
        if self.in_bounds_x(x + 1) and self.cavein[z, x + 1, y] is not False:
            if self.cavein[z, x + 1, y]:
                if (z, x + 1, y) in self.cavein_dep_graph:
                    if (z, x, y) in self.cavein_dep_graph and \
                        (z, x + 1, y) not in self.cavein_dep_graph[(z, x, y)]:
                        self.cavein_dep_graph[(z, x + 1, y)].add((z, x, y))
                elif not self.is_edge_tile(z, x + 1, y):
                    self.cavein_dep_graph[(z, x + 1, y)] = set([(z, x, y)])
            elif (z, x + 1, y) not in q_set:
                tiles.append((z, x + 1, y))
        if self.in_bounds_y(y - 1) and self.cavein[z, x, y - 1] is not False:
            if self.cavein[z, x, y - 1]:
                if (z, x, y - 1) in self.cavein_dep_graph:
                    if (z, x, y) in self.cavein_dep_graph and \
                        (z, x, y - 1) not in self.cavein_dep_graph[(z, x, y)]:
                        self.cavein_dep_graph[(z, x, y - 1)].add((z, x, y))
                elif not self.is_edge_tile(z, x, y - 1):
                    self.cavein_dep_graph[(z, x, y - 1)] = set([(z, x, y)])
            elif (z, x, y - 1) not in q_set:
                tiles.append((z, x, y - 1))
        if self.in_bounds_y(y + 1) and self.cavein[z, x, y + 1] is not False:
            if self.cavein[z, x, y + 1]:
                if (z, x, y + 1) in self.cavein_dep_graph:
                    if (z, x, y) in self.cavein_dep_graph and \
                        (z, x, y + 1) not in self.cavein_dep_graph[(z, x, y)]:
                        self.cavein_dep_graph[(z, x, y + 1)].add((z, x, y))
                elif not self.is_edge_tile(z, x, y + 1):
                    self.cavein_dep_graph[(z, x, y + 1)] = set([(z, x, y)])
            elif (z, x, y + 1) not in q_set:
                tiles.append((z, x, y + 1))
        if self.in_bounds_z(z - 1) and self.cavein[z - 1, x, y] is not False and \
                (self.tiles["tile_type"][z - 1, x, y] == wall or \
                self.tiles["tile_type"][z - 1, x, y] == door or \
                self.tiles["tile_type"][z - 1, x, y] == window or \
                self.tiles["tile_type"][z - 1, x, y] == ustairs):
            if self.cavein[z - 1, x, y]:
                if (z - 1, x, y) in self.cavein_dep_graph:
                    if (z, x, y) in self.cavein_dep_graph and \
                        (z - 1, x, y) not in self.cavein_dep_graph[(z, x, y)]:
                        self.cavein_dep_graph[(z - 1, x, y)].add((z, x, y))
                elif not self.is_edge_tile(z - 1, x, y):
                    self.cavein_dep_graph[(z - 1, x, y)] = set([(z, x, y)])
            elif (z - 1, x, y) not in q_set:
                tiles.append((z - 1, x, y))
        if self.in_bounds_z(z + 1) and self.cavein[z + 1, x, y] is not False and \
                (self.tiles["tile_type"][z, x, y] == wall or \
                self.tiles["tile_type"][z, x, y] == door or \
                self.tiles["tile_type"][z, x, y] == window or \
                self.tiles["tile_type"][z, x, y] == ustairs):
            if self.cavein[z + 1, x, y]:
                if (z + 1, x, y) in self.cavein_dep_graph:
                    if (z, x, y) in self.cavein_dep_graph and \
                        (z + 1, x, y) not in self.cavein_dep_graph[(z, x, y)]:
                        self.cavein_dep_graph[(z + 1, x, y)].add((z, x, y))
                elif not self.is_edge_tile(z + 1, x, y):
                    self.cavein_dep_graph[(z + 1, x, y)] = set([(z, x, y)])
            elif (z + 1, x, y) not in q_set:
                tiles.append((z + 1, x, y))
        return tiles

    def cavein_init(self) -> None:
        q = deque()
        q_set = set()
        for z in range(self.depth):
            for x in range(self.width):
                for y in range(self.height):
                    if self.tiles["tile_type"][z, x, y] == empty:
                        self.cavein[z, x, y] = False
                    elif z == 0 or z == self.depth - 1 or \
                        x == 0 or x == self.width - 1 or \
                        y == 0 or y == self.height - 1:
                        self.cavein[z, x, y] = True # saves first round of edge neighbor check to put in queue
                        q.append((z, x, y))
                        q_set.add((z, x, y))
        
        while len(q) > 0:
            z, x, y = q.popleft()
            q_set.remove((z, x, y))
            self.cavein[z, x, y] = True
            for nz, nx, ny in self.get_cavein_neighbors(q_set, z, x, y):
                q.append((nz, nx, ny))
                q_set.add((nz, nx, ny))
                if (nz, nx, ny) in self.cavein_dep_graph:
                    self.cavein_dep_graph[nz, nx, ny].add((z, x, y))
                elif not self.is_edge_tile(nz, nx, ny):
                    self.cavein_dep_graph[nz, nx, ny] = set([(z, x, y)])
        
        np.place(self.cavein, self.cavein == None, False)
        dmg_tiles_d = self.get_cavein_dmg_tiles()
        self.apply_cavein_dmg(dmg_tiles_d)


    # outside updated in remove tile in this function
    # set tile to empty in this method
    def get_cavein_dmg_tiles(self) -> Dict(Tuple(int, int, int), int):
        dmg_tiles_d = {}
        indexes = np.argwhere((self.tiles["tile_type"] != empty) & (~self.cavein))
        for z, x, y in indexes:
            self.tiles[z, x, y] = tile_types.empty
            self.cavein[z, x, y] = False
            cur_z = z - 1
            while cur_z >= 0:
                if self.tiles["tile_type"][cur_z, x, y] != empty:
                    break
                else:
                    cur_z -= 1
            if cur_z >= 0:
                if (cur_z, x, y) in dmg_tiles_d:
                    dmg_tiles_d[cur_z, x, y] += 1
                else:
                    dmg_tiles_d[cur_z, x, y] = 1
            # update outside matrix
            if self.outside[x, y] == z:
                self.outside[x, y] = cur_z
                for k in range(cur_z, z):
                    if k >= 0:
                        self.set_light_tile(k, x, y, 4)
        return dmg_tiles_d

    def apply_cavein_dmg(self, dmg_tiles_d: Dict(Tuple(int, int, int), int)) -> None:
        for a in self.actors:
            if (a.z, a.x, a.y) in dmg_tiles_d:
                damage = consts.CAVEIN_DMG_MULT * dmg_tiles_d[(a.z, a.x, a.y)] - a.fighter.defense
                if damage > 0:
                    self.engine.message_log.add_message(f"Falling debris for {damage} hit points.")
                    a.fighter.hp -= damage
                else:
                    self.engine.message_log.add_message("Falling debris but does no damage.")

    def outside_init(self) -> None:
        for x in range(self.width):
            for y in range(self.height):
                cur_z = self.depth - 1
                while cur_z >= 0:
                    if self.tiles["tile_type"][cur_z, x, y] != empty:
                        break
                    else:
                        cur_z -= 1
                self.outside[x, y] = cur_z

    def get_cavein_dfs_neighbors(self, z: int, x: int, y:int) -> List[Tuple(int, int, int)]:
        tiles = []
        if self.in_bounds_x(x - 1) and self.cavein[z, x - 1, y]:
            tiles.append((z, x - 1, y))
        if self.in_bounds_x(x + 1) and self.cavein[z, x + 1, y]:
            tiles.append((z, x + 1, y))
        if self.in_bounds_y(y - 1) and self.cavein[z, x, y - 1]:
            tiles.append((z, x, y - 1))
        if self.in_bounds_y(y + 1) and self.cavein[z, x, y + 1]:
            tiles.append((z, x, y + 1))
        if self.in_bounds_z(z - 1) and self.cavein[z - 1, x, y]:
            tiles.append((z - 1, x, y))
        if self.in_bounds_z(z + 1) and self.cavein[z + 1, x, y]:
            tiles.append((z + 1, x, y))
        return tiles

    def cavein_dfs(self, z: int, x: int, y: int, pz: int, px: int, py: int) -> None:
        if (z, x, y) in self.cavein_dep_graph:
            dependencies = self.cavein_dep_graph[z, x, y]
            if (pz, px, py) in dependencies:
                if len(dependencies) > 1:
                    dependencies.remove((pz, px, py))
                else: # remove tile z, x, y by setting tile to empty and cavein to False
                    del self.cavein_dep_graph[z, x, y]
                    self.cavein[z, x, y] = False
                    for nz, nx, ny in self.get_cavein_dfs_neighbors(z, x, y):
                        if (nz, nx, ny) != (pz, px, py):
                            self.cavein_dfs(nz, nx, ny, z, x, y)

    def light_init(self) -> None:
        for z in range(self.depth):
            self.light[4][z][z >= self.outside] = True
            self.light[3][z][z >= self.outside] = False
            self.light[2][z][z >= self.outside] = False
            self.light[1][z][z >= self.outside] = False
            self.light[0][z][z >= self.outside] = False

            self.light[4][z][z < self.outside] = False
            self.light[3][z][z < self.outside] = False
            self.light[2][z][z < self.outside] = False
            self.light[1][z][z < self.outside] = True
            self.light[0][z][z < self.outside] = False
        for z in range(self.depth):
            for x in range(self.width):
                for y in range(self.height):
                    if z < self.outside[x, y]:
                        self.diffuse_tile(z, x, y)

    def diffuse_tile(self, z: int, x: int, y: int) -> None:
        neighbors = self.get_neighbor_tiles(z, x, y)
        index_list = [0, 0, 0, 0, 0]
        for n in neighbors:
            index_list[self.get_light_tile(*n)] += 1
        # average of neighbor tile light values
        prod_sum = 0
        total = 0
        for i, count in enumerate(index_list):
            prod_sum += (i + 1) * count
            total += count
        self.set_light_tile(z, x, y, int(prod_sum / total) - 1)

    def remove_tile(self, z: int, x: int, y: int) -> None:
        self.cavein[z, x, y] = False
        # print(self.cavein_dep_graph[z, x, y])
        if (z, x, y) in self.cavein_dep_graph:
            del self.cavein_dep_graph[z, x, y]
        for nz, nx, ny in self.get_cavein_dfs_neighbors(z, x, y):
            # print(nz, nx, ny)
            self.cavein_dfs(nz, nx, ny, z, x, y)
        dmg_tiles_d = self.get_cavein_dmg_tiles()
        self.apply_cavein_dmg(dmg_tiles_d)

    def build_update_tile(self, z: int, x: int, y: int, build_type: IntEnum, material: IntEnum) -> List[Tuple(int, int, int)]:
        self.cavein[z, x, y] = True
        tmp = tile_types.get_obj_from_type(build_type, material)
        self.tiles[z, x, y] = tmp
        if self.outside[x, y] < z:
            self.outside[x, y] = z
            for k in range(self.outside[x, y], z):
                self.diffuse_tile(k, x, y)

    def build_after_check(self, z: int, x: int, y: int, build_type: IntEnum, material: IntEnum) -> None:
        valid_neighbors = []
        if self.in_bounds_x(x - 1) and self.cavein[z, x - 1, y]:
            valid_neighbors.append((z, x - 1, y))
        if self.in_bounds_x(x + 1) and self.cavein[z, x + 1, y]:
            valid_neighbors.append((z, x + 1, y))
        if self.in_bounds_y(y - 1) and self.cavein[z, x, y - 1]:
            valid_neighbors.append((z, x, y - 1))
        if self.in_bounds_y(y + 1) and self.cavein[z, x, y + 1]:
            valid_neighbors.append((z, x, y + 1))
        if self.in_bounds_z(z - 1) and self.cavein[z - 1, x, y] and \
                (self.tiles["tile_type"][z - 1, x, y] == wall or \
                self.tiles["tile_type"][z - 1, x, y] == door or \
                self.tiles["tile_type"][z - 1, x, y] == window or \
                self.tiles["tile_type"][z - 1, x, y] == ustairs):
            valid_neighbors.append((z - 1, x, y))
        if self.in_bounds_z(z + 1) and self.cavein[z + 1, x, y] and \
                (build_type == wall or build_type == door or build_type == window or build_type == ustairs) and \
                self.tiles["tile_type"][z + 1, x, y] != empty:
            valid_neighbors.append((z + 1, x, y))

        if self.is_edge_tile(z, x, y): # build on edge tile, no dep graph entry
            self.build_update_tile(z, x, y, build_type, material)
            for n in valid_neighbors: # one way dependency
                if n in self.cavein_dep_graph:
                    self.cavein_dep_graph[n].add((z, x, y))
        elif valid_neighbors:
            self.build_update_tile(z, x, y, build_type, material)
            for i, n in enumerate(valid_neighbors): # two way dependency
                if (z, x, y) in self.cavein_dep_graph:
                    self.cavein_dep_graph[(z, x, y)].add(n)
                else:
                    self.cavein_dep_graph[(z, x, y)] = set([n])
                if i > 0 and n in self.cavein_dep_graph:
                    self.cavein_dep_graph[n].add((z, x, y))
        else:
            raise exceptions.Impossible("Can't build, no supporting tile")

    def build_tile_check(self, z: int, x: int, y: int, build_type: IntEnum) -> bool:
        if build_type == floor or (build_type == dstairs and z > 0):
            if self.tiles["tile_type"][z, x, y] == empty:
                return True
            else:
                raise exceptions.Impossible("Cannot build floor type on non-empty tile")
                return False
        elif build_type == wall or build_type == door or build_type == window or \
            (build_type == ustairs and z < self.depth - 1):
            if self.tiles["tile_type"][z, x, y] == empty or self.tiles["tile_type"][z, x, y] == floor:
                return True
            else:
                raise exceptions.Impossible("Cannot build wall type on wall or stair tile")
                return False

    def remove_tile_check(self, z: int, x: int, y: int) -> bool:
        if self.tiles["tile_type"][z, x, y] == empty:
            raise exceptions.Impossible("Cannot remove empty tile")
            return False
        else:
            return True

    def particle_spread(self) -> None:
        p_coord_dict = {}
        for p in self.particles:
            if (p.z, p.x, p.y) in p_coord_dict:
                p_coord_dict[p.z, p.x, p.y].append(p)
            else:
                p_coord_dict[p.z, p.x, p.y] = [p]
        for p in set(self.particles):
            p.spread(p_coord_dict)

        for p in self.particles:
            p.effect.activate()

    def get_fire_neighbors(self, z: int, x: int, y: int) -> List[Tuple(int, int, int)]:
        tiles = []
        if self.in_bounds_x(x - 1) and self.cavein[z, x - 1, y] and not self.on_fire[z, x - 1, y] and \
                self.tiles["material"][z, x - 1, y] == tile_types.Material.WOOD and \
                self.get_water_tile(z, x - 1, y) == 0:
            tiles.append((z, x - 1, y))
        if self.in_bounds_x(x + 1) and self.cavein[z, x + 1, y] and not self.on_fire[z, x + 1, y] and \
                self.tiles["material"][z, x + 1, y] == tile_types.Material.WOOD and \
                self.get_water_tile(z, x + 1, y) == 0:
            tiles.append((z, x + 1, y))
        if self.in_bounds_y(y - 1) and self.cavein[z, x, y - 1] and not self.on_fire[z, x, y - 1] and \
                self.tiles["material"][z, x, y - 1] == tile_types.Material.WOOD and \
                self.get_water_tile(z, x, y - 1) == 0:
            tiles.append((z, x, y - 1))
        if self.in_bounds_y(y + 1) and self.cavein[z, x, y + 1] and not self.on_fire[z, x, y + 1] and \
                self.tiles["material"][z, x, y + 1] == tile_types.Material.WOOD and \
                self.get_water_tile(z, x, y + 1) == 0:
            tiles.append((z, x, y + 1))
        if self.in_bounds_z(z - 1) and self.cavein[z - 1, x, y] and not self.on_fire[z - 1, x, y] and \
                (self.tiles["tile_type"][z - 1, x, y] == wall or \
                self.tiles["tile_type"][z - 1, x, y] == door or \
                self.tiles["tile_type"][z - 1, x, y] == window or \
                self.tiles["tile_type"][z - 1, x, y] == ustairs) and \
                self.tiles["material"][z - 1, x, y] == tile_types.Material.WOOD and \
                self.get_water_tile(z - 1, x, y) == 0:
            tiles.append((z - 1, x, y))
        if self.in_bounds_z(z + 1) and self.cavein[z + 1, x, y] and not self.on_fire[z + 1, x, y] and \
                (self.tiles["tile_type"][z, x, y] == wall or \
                self.tiles["tile_type"][z, x, y] == door or \
                self.tiles["tile_type"][z, x, y] == window or \
                self.tiles["tile_type"][z, x, y] == ustairs) and \
                self.tiles["material"][z + 1, x, y] == tile_types.Material.WOOD and \
                self.get_water_tile(z + 1, x, y) == 0:
            tiles.append((z + 1, x, y))
        return tiles

    def fire_spread(self) -> None:
        indexes = np.argwhere(self.on_fire)
        for z, x, y in indexes:
            if int(self.tiles["hp"][z, x, y]) * 2 < self.tiles["default_wood_hp"][z, x, y]:
                n_tiles = self.get_fire_neighbors(z, x, y)
                for t in n_tiles:
                    self.on_fire[*t] = True
                    if t in self.fire_orig_light:
                        raise exceptions.Impossible("TODO: gamemap.fire_orig_light dict entries should be removed")
                    else:
                        self.gamemap.fire_orig_light[*t] = self.gamemap.get_light_tile(*t)


    def set_max_pressure(self, pressure_dict: Dict[Tuple(int, int, int), int], z: int, x: int, y: int, no_z: bool) -> None:
        # pressure reset in diagonals, as they are simply not checked here, less code more features
        if not no_z and self.in_bounds_z(z + 1) and (z + 1, x, y) in pressure_dict and \
            (self.tiles["tile_type"][z + 1, x, y] == empty or self.tiles["tile_type"][z + 1, x, y] == empty):
            pressure = pressure_dict[z + 1, x, y]
        else:
            pressure = z
        if self.in_bounds_x(x - 1) and (z, x - 1, y) in pressure_dict and \
            self.tiles["tile_type"][z, x - 1, y] != empty and self.tiles["tile_type"][z, x - 1, y] != door:
            pressure = max(pressure, pressure_dict[z, x - 1, y])
        elif self.in_bounds_x(x + 1) and (z, x + 1, y) in pressure_dict and \
            self.tiles["tile_type"][z, x + 1, y] != empty and self.tiles["tile_type"][z, x + 1, y] != door:
            pressure = max(pressure, pressure_dict[z, x + 1, y])
        elif self.in_bounds_y(y - 1) and (z, x, y - 1) in pressure_dict and \
            self.tiles["tile_type"][z, x, y - 1] != empty and self.tiles["tile_type"][z, x, y - 1] != door:
            pressure = max(pressure, pressure_dict[z, x, y - 1])
        elif self.in_bounds_y(y + 1) and (z, x, y + 1) in pressure_dict and \
            self.tiles["tile_type"][z, x, y + 1] != empty and self.tiles["tile_type"][z, x, y + 1] != door:
            pressure = max(pressure, pressure_dict[z, x, y + 1])
        if (z, x, y) in pressure_dict:
            pressure_dict[z, x, y] = max(pressure, pressure_dict[z, x, y])
        else:
            pressure_dict[z, x, y] = pressure

    def water_horizontal(self, z: int, x: int, y: int, level_z: float, ignore_higher=False) -> float:
        neighbors = self.get_neighbor_tiles(z, x, y)
        available_tiles = []
        for nz, nx, ny in neighbors:
            nl = self.get_water_tile(nz, nx, ny)
            if self.tiles["tile_type"][nz, nx, ny] != wall and \
                    self.tiles["tile_type"][nz, nx, ny] != door and \
                    self.tiles["tile_type"][nz, nx, ny] != window:
                if ignore_higher or (consts.WATER_HORIZONTAL_THRESHOLD < level_z - nl):
                    available_tiles.append((nz, nx, ny))
        total = 0
        for t in available_tiles:
            total += self.get_water_tile(*t)
        total += level_z
        each_amount = total / (len(available_tiles) + 1)
        for nz, nx, ny in available_tiles:
            self.set_water_tile(nz, nx, ny, each_amount)
        if each_amount != 0:
            return each_amount
        else:
            return level_z

    def water_spread(self) -> None:
        drying_indexes = np.argwhere((self.water_float < consts.DRYING_THRESHOLD) & (self.water_float > 0))
        for z, x, y in drying_indexes:
            after_drying = self.get_water_tile(z, x, y) - consts.DRYING_AMT
            if after_drying >= 0:
                self.set_water_tile(z, x, y, after_drying)
            else:
                self.set_water_tile(z, x, y, 0)
        water_indexes = np.argwhere(self.water_float)
        water_indexes_sorted = sorted(water_indexes, key=lambda x: x[0])
        pressure_dict = {}

        for z, x, y in reversed(water_indexes_sorted):
            if self.tiles["tile_type"][z, x, y] != wall and \
                    self.tiles["tile_type"][z, x, y] != door and \
                    self.tiles["tile_type"][z, x, y] != window:
                self.set_max_pressure(pressure_dict, z, x, y, False)
        for z, x, y in water_indexes_sorted:
            if self.tiles["tile_type"][z, x, y] != wall and \
                self.tiles["tile_type"][z, x, y] != door and \
                self.tiles["tile_type"][z, x, y] != window:
                self.set_max_pressure(pressure_dict, z, x, y, True)

        extra_water = {}
        for z, x, y in water_indexes_sorted:
            level_z = self.get_water_tile(z, x, y)
            cur_z1 = z - 1

            if self.in_bounds_z(cur_z1) and \
                (self.tiles["tile_type"][z, x, y] == empty or self.tiles["tile_type"][z, x, y] == dstairs):
                while self.in_bounds_z(cur_z1) and \
                    self.get_water_tile(cur_z1, x, y) == 0 and \
                        (self.tiles["tile_type"][cur_z1, x, y] == empty or self.tiles["tile_type"][cur_z1, x, y] == dstairs):
                    cur_z1 -= 1
                if cur_z1 < 0:
                    self.set_water_tile(z, x, y, 0)
                    continue
                level_z1 = self.get_water_tile(cur_z1, x, y)
                level_room = 4 - level_z1
                left_over = level_z - level_room
                if left_over > 0:
                    self.set_water_tile(cur_z1, x, y, 4)
                    self.set_water_tile(cur_z1 + 1, x, y, left_over)
                    level_z = left_over
                else:
                    self.set_water_tile(cur_z1, x, y, level_z1 + level_z)
                    self.set_water_tile(cur_z1 + 1, x, y, 0)
                    level_z = 0
                if cur_z1 + 1 < z:
                    self.set_water_tile(z, x, y, 0)
                    level_z = 0
            if cur_z1 < 0 and (self.tiles["tile_type"][z, x, y] == empty or self.tiles["tile_type"][z, x, y] == dstairs):
                self.set_water_tile(z, x, y, 0)
                continue

            if level_z > 0:
                level_z = self.water_horizontal(z, x, y, level_z, False)
                self.set_water_tile(z, x, y, level_z)
                
            if self.in_bounds_z(z + 1) and (z, x, y) in pressure_dict and \
                    (self.tiles["tile_type"][z + 1, x, y] == empty or self.tiles["tile_type"][z + 1, x, y] == empty) and \
                    level_z > consts.UPWARD_PRESSURE_THRESHOLD:
                if (z + 1, x, y) in pressure_dict:
                    if pressure_dict[z + 1, x, y] < pressure_dict[z, x, y]:
                        self.set_water_tile(z, x, y, 1)
                        extra_water[z + 1, x, y] = level_z - 1
                else: # not a water tile
                    self.set_water_tile(z, x, y, 1)
                    self.set_water_tile(z + 1, x, y, level_z - 1)

        for k, v in list(extra_water.items()):
            level_extra = self.water_horizontal(*k, v, True)
            level_extra_z1 = self.get_water_tile(k[0] - 1, k[1], k[2])
            lower_sum = level_extra + level_extra_z1
            if lower_sum > 4:
                self.set_water_tile(k[0] - 1, k[1], k[2], 4)
                lower_sum -= 4
                k_level = lower_sum + self.get_water_tile(*k)
                if k_level > 4:
                    self.set_water_tile(*k, 4)
                    extra_water[*k] = k_level - 4
                else:
                    self.set_water_tile(*k, k_level)
            else:
                self.set_water_tile(k[0] - 1, k[1], k[2], lower_sum)
                del extra_water[*k]

        for k, v in extra_water.items():
            self.set_water_tile(k[0] - 1, k[1], k[2], self.get_water_tile(k[0] - 1, k[1], k[2]) + v)

