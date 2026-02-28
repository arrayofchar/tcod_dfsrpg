from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING, List, Tuple, Set, Dict

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

import numpy as np  # type: ignore
from queue import Queue
from tcod.console import Console
import exceptions

from entity import Actor, Item, BuildRemoveTile, Particle, Fire, Fixture
import tile_types
import color

empty = tile_types.empty
wall = tile_types.wall
door = tile_types.door
floor = tile_types.floor
dstairs = tile_types.down_stairs
ustairs = tile_types.up_stairs

cavein_dmg_mult = 10
fall_dmg_mult = 5

class GameMap:
    def __init__(
        self, engine: Engine, depth: int, width: int, height: int, entities: Iterable[Entity] = ()
    ):
        self.engine = engine
        self.depth, self.width, self.height = depth, width, height
        self.tiles = np.full((depth, width, height), fill_value=wall, order="F")
        self.entities = set(entities) # entries deleted
        
        self.light_fov = {} # entries not deleted
        self.fire_orig_light = {}

        self.visible = np.full((depth, width, height), fill_value=False, order="F")
        self.explored = np.full((depth, width, height), fill_value=False, order="F")
        self.cavein = np.full((depth, width, height), fill_value=None, order="F")
        self.outside = np.full((width, height), fill_value=int(depth), order="F")
        self.on_fire = np.full((depth, width, height), fill_value=False, order="F")

        self.light = [np.full((depth, width, height), fill_value=True, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),
                        np.full((depth, width, height), fill_value=False, order="F"),]

        self.cavein_dep_graph = {} # edge cavein=True tiles don't have entries

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

    @property
    def work_entities(self) -> Iterator[BuildRemoveTile]:
        yield from (entity for entity in self.entities if isinstance(entity, BuildRemoveTile))

    @property
    def particles(self) -> Iterator[Particle]:
        yield from (entity for entity in self.entities if isinstance(entity, Particle))

    @property
    def work_blocking_entities(self) -> Iterator[Entity]:
        yield from (entity for entity in self.entities \
            if not isinstance(entity, Particle) and not isinstance(entity, BuildRemoveTile))

    @property
    def fixtures(self) -> Iterator[Fixture]:
        yield from (entity for entity in self.entities if isinstance(entity, Particle))

    @property
    def fires(self) -> Iterator[Fire]:
        yield from (entity for entity in self.entities if isinstance(entity, Fire))


    def set_light_tile(self, z: int, x: int, y:int, level: int) -> None:
        for i, light_matrix in enumerate(self.light):
            if i == level:
                light_matrix[z, x, y] = True
            else:
                light_matrix[z, x, y] = False


    def get_light_tile(self, z: int, x: int, y:int) -> int:
        if self.in_bounds(z, x, y):
            for i, light_matrix in enumerate(self.light):
                if light_matrix[z, x, y]:
                    return i

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

    def get_blocking_entity_at_location(
        self, location_z: int, location_x: int, location_y: int,
    ) -> Optional[Entity]:
        for entity in self.entities:
            if (entity.blocks_movement
                and entity.z == location_z
                and entity.x == location_x
                and entity.y == location_y):
                return entity
        return None

    def get_actor_at_location(self, z: int, x: int, y: int) -> Optional[Actor]:
        for actor in self.actors:
            if actor.z == z and actor.x == x and actor.y == y:
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

    def update_tiles(self) -> None:
        np.place(self.tiles["hp"], self.on_fire, self.tiles["hp"] - 2)
        np.place(self.on_fire, self.tiles["hp"] <= 0, False)

        # for z in range(self.depth):
        #     for x in range(self.width):
        #         for y in range(self.height):
        #             if self.tiles["hp"][z, x, y] <= 0 and self.tiles[z, x, y] != empty:
        #                 self.remove_tile(z, x, y)
        #                 if (z, x, y) in self.fire_orig_light:
        #                     self.set_light_tile(z, x, y, \
        #                         min(self.fire_orig_light[z, x, y], self.get_light_tile(z, x, y)))
        #                     del self.fire_orig_light[z, x, y]
        
        np.place(self.light[4], self.on_fire, True)
        np.place(self.light[3], self.on_fire, False)
        np.place(self.light[2], self.on_fire, False)
        np.place(self.light[1], self.on_fire, False)
        np.place(self.light[0], self.on_fire, False)


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
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.on_fire[z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.light[4][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.light[3][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.light[2][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.light[1][z][x : x + cam_width, y : y + cam_height]),
                (self.visible[z][x : x + cam_width, y : y + cam_height] & self.light[0][z][x : x + cam_width, y : y + cam_height]),
                self.explored[z][x : x + cam_width, y : y + cam_height],
            ],
            choicelist=[
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
        if self.in_bounds(z, x - 1, y) and self.cavein[z, x - 1, y] is not False:
            if self.cavein[z, x - 1, y]:
                if (z, x - 1, y) in self.cavein_dep_graph:
                    if (z, x, y) in self.cavein_dep_graph and \
                        (z, x - 1, y) not in self.cavein_dep_graph[(z, x, y)]:
                        self.cavein_dep_graph[(z, x - 1, y)].add((z, x, y))
                elif not self.is_edge_tile(z, x - 1, y):
                    self.cavein_dep_graph[(z, x - 1, y)] = set([(z, x, y)])
            elif (z, x - 1, y) not in q_set:
                tiles.append((z, x - 1, y))
        if self.in_bounds(z, x + 1, y) and self.cavein[z, x + 1, y] is not False:
            if self.cavein[z, x + 1, y]:
                if (z, x + 1, y) in self.cavein_dep_graph:
                    if (z, x, y) in self.cavein_dep_graph and \
                        (z, x + 1, y) not in self.cavein_dep_graph[(z, x, y)]:
                        self.cavein_dep_graph[(z, x + 1, y)].add((z, x, y))
                elif not self.is_edge_tile(z, x + 1, y):
                    self.cavein_dep_graph[(z, x + 1, y)] = set([(z, x, y)])
            elif (z, x + 1, y) not in q_set:
                tiles.append((z, x + 1, y))
        if self.in_bounds(z, x, y - 1) and self.cavein[z, x, y - 1] is not False:
            if self.cavein[z, x, y - 1]:
                if (z, x, y - 1) in self.cavein_dep_graph:
                    if (z, x, y) in self.cavein_dep_graph and \
                        (z, x, y - 1) not in self.cavein_dep_graph[(z, x, y)]:
                        self.cavein_dep_graph[(z, x, y - 1)].add((z, x, y))
                elif not self.is_edge_tile(z, x, y - 1):
                    self.cavein_dep_graph[(z, x, y - 1)] = set([(z, x, y)])
            elif (z, x, y - 1) not in q_set:
                tiles.append((z, x, y - 1))
        if self.in_bounds(z, x, y + 1) and self.cavein[z, x, y + 1] is not False:
            if self.cavein[z, x, y + 1]:
                if (z, x, y + 1) in self.cavein_dep_graph:
                    if (z, x, y) in self.cavein_dep_graph and \
                        (z, x, y + 1) not in self.cavein_dep_graph[(z, x, y)]:
                        self.cavein_dep_graph[(z, x, y + 1)].add((z, x, y))
                elif not self.is_edge_tile(z, x, y + 1):
                    self.cavein_dep_graph[(z, x, y + 1)] = set([(z, x, y)])
            elif (z, x, y + 1) not in q_set:
                tiles.append((z, x, y + 1))
        if self.in_bounds(z - 1, x, y) and self.cavein[z - 1, x, y] is not False and \
            (self.tiles[z - 1, x, y] == wall or self.tiles[z - 1, x, y] == door):
            if self.cavein[z - 1, x, y]:
                if (z - 1, x, y) in self.cavein_dep_graph:
                    if (z, x, y) in self.cavein_dep_graph and \
                        (z - 1, x, y) not in self.cavein_dep_graph[(z, x, y)]:
                        self.cavein_dep_graph[(z - 1, x, y)].add((z, x, y))
                elif not self.is_edge_tile(z - 1, x, y):
                    self.cavein_dep_graph[(z - 1, x, y)] = set([(z, x, y)])
            elif (z - 1, x, y) not in q_set:
                tiles.append((z - 1, x, y))
        if self.in_bounds(z + 1, x, y) and self.cavein[z + 1, x, y] is not False and \
            (self.tiles[z, x, y] == wall or self.tiles[z, x, y] == door):
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
        q = Queue()
        q_set = set()
        for z in range(self.depth):
            for x in range(self.width):
                for y in range(self.height):
                    if self.tiles[z, x, y] == empty:
                        self.cavein[z, x, y] = False
                    elif z == 0 or z == self.depth - 1 or \
                        x == 0 or x == self.width - 1 or \
                        y == 0 or y == self.height - 1:
                        self.cavein[z, x, y] = True # saves first round of edge neighbor check to put in queue
                        q.put((z, x, y))
                        q_set.add((z, x, y))
        
        while not q.empty():
            z, x, y = q.get()
            q_set.remove((z, x, y))
            self.cavein[z, x, y] = True
            for nz, nx, ny in self.get_cavein_neighbors(q_set, z, x, y):
                q.put((nz, nx, ny))
                q_set.add((nz, nx, ny))
                if (nz, nx, ny) in self.cavein_dep_graph:
                    self.cavein_dep_graph[nz, nx, ny].add((z, x, y))
                elif not self.is_edge_tile(nz, nx, ny):
                    self.cavein_dep_graph[nz, nx, ny] = set([(z, x, y)])
            
        dmg_tiles_d, fall_tiles_d = self.get_cavein_dmg_tiles()
        self.apply_cavein_dmg(dmg_tiles_d, fall_tiles_d)


    # outside updated in remove tile in this function
    # set tile to empty in this method
    def get_cavein_dmg_tiles(self) -> Dict(Tuple(int, int, int), int):
        dmg_tiles_d = {}
        fall_tiles_d = {}
        for z in range(self.depth):
            for x in range(self.width):
                for y in range(self.height):
                    if not self.cavein[z, x, y] and self.tiles[z, x, y] != empty:
                        self.tiles[z, x, y] = empty
                        self.cavein[z, x, y] = False
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
                        fall_tiles_d[(z, x, y)] = cur_z
                        # update outside matrix
                        if self.outside[x, y] == z:
                            self.outside[x, y] = cur_z
                            for k in range(cur_z, z):
                                self.set_light_tile(k, x, y, 4)
        return dmg_tiles_d, fall_tiles_d

    def apply_cavein_dmg(self, dmg_tiles_d: Dict(Tuple(int, int, int), int), \
                            fall_tiles_d: Dict(Tuple(int, int, int), int)) -> None:
        for a in self.actors:
            if (a.z, a.x, a.y) in dmg_tiles_d:
                damage = cavein_dmg_mult * dmg_tiles_d[(a.z, a.x, a.y)] - a.fighter.defense
                if damage > 0:
                    self.engine.message_log.add_message(f"Falling debris for {damage} hit points.")
                    a.fighter.hp -= damage
                else:
                    self.engine.message_log.add_message("Falling debris but does no damage.")
            elif (a.z, a.x, a.y) in fall_tiles_d:
                cur_z = fall_tiles_d[(a.z, a.x, a.y)]
                if cur_z >= 0:
                    damage = fall_dmg_mult * (a.z - cur_z)
                    a.z = cur_z # teleport a after damage calculation
                    if damage > 0:
                        self.engine.message_log.add_message(f"Fallen for {damage} hit points.")
                        a.fighter.hp -= damage
                    else:
                        self.engine.message_log.add_message("Fallen but does no damage.")
                else:
                    # del entity
                    del a

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

    def get_cavein_dfs_neighbors(self, z: int, x: int, y:int) -> List[Tuple(int, int, int)]:
        tiles = []
        if self.in_bounds(z, x - 1, y) and self.cavein[z, x - 1, y]:
            tiles.append((z, x - 1, y))
        if self.in_bounds(z, x + 1, y) and self.cavein[z, x + 1, y]:
            tiles.append((z, x + 1, y))
        if self.in_bounds(z, x, y - 1) and self.cavein[z, x, y - 1]:
            tiles.append((z, x, y - 1))
        if self.in_bounds(z, x, y + 1) and self.cavein[z, x, y + 1]:
            tiles.append((z, x, y + 1))
        if self.in_bounds(z - 1, x, y) and self.cavein[z - 1, x, y]:
            tiles.append((z - 1, x, y))
        if self.in_bounds(z + 1, x, y) and self.cavein[z + 1, x, y]:
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
            for x in range(self.width):
                for y in range(self.height):
                    if z >= self.outside[x, y]:
                        self.set_light_tile(z, x, y, 4) # needs self.outside initialized
                    else: 
                        self.set_light_tile(z, x, y, 1)
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
        dmg_tiles_d, fall_tiles_d = self.get_cavein_dmg_tiles()
        self.apply_cavein_dmg(dmg_tiles_d, fall_tiles_d)

    def build_update_tile(self, z: int, x: int, y: int, build_type: np.ndarray) -> List[Tuple(int, int, int)]:
        self.cavein[z, x, y] = True
        self.tiles[z, x, y] = build_type
        if self.outside[x, y] < z:
            self.outside[x, y] = z
            for k in range(self.outside[x, y], z):
                self.diffuse_tile(k, x, y)

    def build_after_check(self, z: int, x: int, y: int, build_type: np.ndarray) -> None:
        valid_neighbors = []
        if self.in_bounds(z, x - 1, y) and self.cavein[z, x - 1, y]:
            valid_neighbors.append((z, x - 1, y))
        if self.in_bounds(z, x + 1, y) and self.cavein[z, x + 1, y]:
            valid_neighbors.append((z, x + 1, y))
        if self.in_bounds(z, x, y - 1) and self.cavein[z, x, y - 1]:
            valid_neighbors.append((z, x, y - 1))
        if self.in_bounds(z, x, y + 1) and self.cavein[z, x, y + 1]:
            valid_neighbors.append((z, x, y + 1))
        if self.in_bounds(z - 1, x, y) and self.cavein[z - 1, x, y] and \
            (self.tiles[z - 1, x, y] == wall or self.tiles[z - 1, x, y] == door):
            valid_neighbors.append((z - 1, x, y))
        if self.in_bounds(z + 1, x, y) and self.cavein[z + 1, x, y] and \
            (build_type == wall or build_type == door) and self.tiles[z + 1, x, y] != empty:
            valid_neighbors.append((z + 1, x, y))

        if self.is_edge_tile(z, x, y): # build on edge tile, no dep graph entry
            self.build_update_tile(z, x, y, build_type)
            for n in valid_neighbors: # one way dependency
                if n in self.cavein_dep_graph:
                    self.cavein_dep_graph[n].add((z, x, y))
        elif valid_neighbors:
            self.build_update_tile(z, x, y, build_type)
            for i, n in enumerate(valid_neighbors): # two way dependency
                if (z, x, y) in self.cavein_dep_graph:
                    self.cavein_dep_graph[(z, x, y)].add(n)
                else:
                    self.cavein_dep_graph[(z, x, y)] = set([n])
                if i > 0 and n in self.cavein_dep_graph:
                    self.cavein_dep_graph[n].add((z, x, y))
        else:
            raise exceptions.Impossible("Can't build, no supporting tile")

    def build_tile_check(self, z: int, x: int, y: int, build_type: np.ndarray) -> bool:
        if build_type == floor or build_type == dstairs or build_type == ustairs:
            if self.tiles[z, x, y] == empty:
                return True
            else:
                raise exceptions.Impossible("Cannot build floor type on non-empty tile")
                return False
        elif build_type == wall or build_type == door:
            if self.tiles[z, x, y] == empty or self.tiles[z, x, y] == floor:
                return True
            else:
                raise exceptions.Impossible("Cannot build wall type on wall or stair tile")
                return False

    def remove_tile_check(self, z: int, x: int, y: int) -> bool:
        if self.tiles[z, x, y] == empty:
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
        if self.in_bounds(z, x - 1, y) and self.cavein[z, x - 1, y] and not self.on_fire[z, x - 1, y] and \
                self.tiles["material"][z, x - 1, y] == tile_types.Material.WOOD:
            tiles.append((z, x - 1, y))
        if self.in_bounds(z, x + 1, y) and self.cavein[z, x + 1, y] and not self.on_fire[z, x + 1, y] and \
                self.tiles["material"][z, x + 1, y] == tile_types.Material.WOOD:
            tiles.append((z, x + 1, y))
        if self.in_bounds(z, x, y - 1) and self.cavein[z, x, y - 1] and not self.on_fire[z, x, y - 1] and \
                self.tiles["material"][z, x, y - 1] == tile_types.Material.WOOD:
            tiles.append((z, x, y - 1))
        if self.in_bounds(z, x, y + 1) and self.cavein[z, x, y + 1] and not self.on_fire[z, x, y + 1] and \
                self.tiles["material"][z, x, y + 1] == tile_types.Material.WOOD:
            tiles.append((z, x, y + 1))
        if self.in_bounds(z - 1, x, y) and self.cavein[z - 1, x, y] and not self.on_fire[z - 1, x, y] and \
                (self.tiles[z - 1, x, y] == wall or self.tiles[z - 1, x, y] == door) and \
                self.tiles["material"][z - 1, x, y] == tile_types.Material.WOOD:
            tiles.append((z - 1, x, y))
        if self.in_bounds(z + 1, x, y) and self.cavein[z + 1, x, y] and not self.on_fire[z + 1, x, y] and \
                (self.tiles[z, x, y] == wall or self.tiles[z, x, y] == door) and \
                self.tiles["material"][z + 1, x, y] == tile_types.Material.WOOD:
            tiles.append((z + 1, x, y))
        return tiles

    def fire_spread(self) -> None:
        for z in range(self.depth):
            for x in range(self.width):
                for y in range(self.height):
                    if self.on_fire[z, x, y]:
                        if self.tiles["hp"] < int(self.tiles[z, x, y]["default_wood_hp"] / 2):
                            n_tiles = self.get_fire_neighbors(z, x, y)
                            for t in n_tiles:
                                self.on_fire[*t] = True
                                if t in self.fire_orig_light:
                                    raise exceptions.Impossible("TODO: gamemap.fire_orig_light dict entries should be removed")
                                else:
                                    self.gamemap.fire_orig_light[*t] = self.gamemap.get_light_tile(*t)
                

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
