from typing import Tuple, List

import numpy as np  # type: ignore
from enum import auto, IntEnum


# Tile graphics structured type compatible with Console.tiles_rgb.
graphic_dt = np.dtype(
    [
        ("ch", np.int32),  # Unicode codepoint.
        ("fg", "3B"),  # 3 unsigned bytes, for RGB colors.
        ("bg", "3B"),
    ]
)

class Material(IntEnum):
    WOOD = auto()
    STONE = auto()
    METAL = auto()

class TileType(IntEnum):
    EMPTY = auto()
    FLOOR = auto()
    WALL = auto()
    DOOR = auto()
    DOWN_STAIRS = auto()
    UP_STAIRS = auto()

material_color = {
    Material.WOOD: (100, 50, 0),
    Material.STONE: (100, 100, 100),
    Material.METAL: (50, 50, 100),
}

# Tile struct used for statically defined tile data.
tile_dt = np.dtype(
    [
        ("walkable", np.bool),  # True if this tile can be walked over.
        ("transparent", np.bool),  # True if this tile doesn't block FOV.
        ("hp", np.int32),
        ("default_wood_hp", np.int32),
        ("fire_color", graphic_dt),
        ("dark", graphic_dt),
        ("light0", graphic_dt),
        ("light1", graphic_dt),
        ("light2", graphic_dt),
        ("light3", graphic_dt),
        ("light4", graphic_dt),
        ("water0", graphic_dt),
        ("water1", graphic_dt),
        ("water2", graphic_dt),
        ("water3", graphic_dt),
        ("water4", graphic_dt),
        ("material", np.uint8),  # Material of the tile
        ("tile_type", np.uint8),
    ]
)


class NewTile:
    def __init__(self, walkable: bool, transparent: bool, \
                    fire_color: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]], \
                    material: Material, tile_type: TileType, hp=0, default_wood_hp=0):
        self.walkable = walkable
        self.transparent = transparent
        self.fire_color = fire_color
        self.hp = hp
        self.default_wood_hp = default_wood_hp
        self.dark = None
        self.light0 = None
        self.light1 = None
        self.light2 = None
        self.light3 = None
        self.light4 = None
        self.water0 = None
        self.water1 = None
        self.water2 = None
        self.water3 = None
        self.water4 = None
        self.material = material
        self.tile_type = tile_type

    def get_arr(self) -> np.ndarray:
        """Helper function for defining individual tile types """
        return np.array((self.walkable, self.transparent, self.hp, self.default_wood_hp, \
            self.fire_color, self.dark, self.light0, self.light1, self.light2, self.light3, self.light4, \
                self.water0, self.water1, self.water2, self.water3, self.water4, \
                self.material, self.tile_type), dtype=tile_dt)

def get_color(material: Material) -> List[Tuple[int, int, int]]:
    if material == Material.WOOD:
        return [
            (0, 0, 0),
            (40, 20, 0),
            (80, 40, 0),
            (120, 60, 0),
            (160, 80, 0),
            (200, 100, 0),
        ]
    if material == Material.STONE:
        return [
            (0, 0, 0),
            (20, 20, 20),
            (40, 40, 40),
            (60, 60, 60),
            (80, 80, 80),
            (100, 100, 100),
        ]
    if material == Material.METAL:
        return [
            (0, 0, 0),
            (20, 20, 40),
            (40, 40, 80),
            (60, 60, 120),
            (80, 80, 160),
            (100, 100, 200),
        ]

def get_hp_mult(material: Material) -> int:
    if material == Material.WOOD:
        return 1
    if material == Material.STONE:
        return 5
    if material == Material.METAL:
        return 20

# SHROUD represents unexplored, unseen tiles
SHROUD = np.array((ord(" "), (255, 255, 255), (0, 0, 0)), dtype=graphic_dt)


empty_orig = NewTile(
    walkable=False,
    transparent=True,
    fire_color=(ord(" "), (200, 200, 200), (100, 100, 100)),
    material=0,
    tile_type=TileType.EMPTY,
)
empty_orig.dark=(ord(" "), (100, 100, 100), (0, 0, 0))
empty_orig.light0=(ord(" "), (200, 200, 200), (20, 20, 20))
empty_orig.light1=(ord(" "), (200, 200, 200), (40, 40, 40))
empty_orig.light2=(ord(" "), (200, 200, 200), (60, 60, 60))
empty_orig.light3=(ord(" "), (200, 200, 200), (80, 80, 80))
empty_orig.light4=(ord(" "), (200, 200, 200), (100, 100, 100))
empty_orig.water0=(ord(" "), (200, 200, 200), (0, 100, 200))
empty_orig.water1=(ord("1"), (200, 200, 200), (0, 100, 200))
empty_orig.water2=(ord("2"), (200, 200, 200), (0, 100, 200))
empty_orig.water3=(ord("3"), (200, 200, 200), (0, 100, 200))
empty_orig.water4=(ord("4"), (200, 200, 200), (0, 100, 200))

floor_orig = NewTile(
    walkable=True,
    transparent=True,
    fire_color=(ord("."), (200, 200, 200), (155, 0, 0)),
    material=Material.WOOD,
    tile_type=TileType.FLOOR,
)
floor_orig.default_wood_hp = get_hp_mult(Material.WOOD) * 500
floor_orig.hp = get_hp_mult(floor_orig.material) * 500
floor_orig.dark=(ord("."), (100, 100, 100), get_color(floor_orig.material)[0])
floor_orig.light0=(ord("."), (200, 200, 200), get_color(floor_orig.material)[1])
floor_orig.light1=(ord("."), (200, 200, 200), get_color(floor_orig.material)[2])
floor_orig.light2=(ord("."), (200, 200, 200), get_color(floor_orig.material)[3])
floor_orig.light3=(ord("."), (200, 200, 200), get_color(floor_orig.material)[4])
floor_orig.light4=(ord("."), (200, 200, 200), get_color(floor_orig.material)[5])
floor_orig.water0=(ord("."), (200, 200, 200), (0, 100, 200))
floor_orig.water1=(ord("1"), (200, 200, 200), (0, 100, 200))
floor_orig.water2=(ord("2"), (200, 200, 200), (0, 100, 200))
floor_orig.water3=(ord("3"), (200, 200, 200), (0, 100, 200))
floor_orig.water4=(ord("4"), (200, 200, 200), (0, 100, 200))

wall_orig = NewTile(
    walkable=False,
    transparent=False,
    fire_color=(ord("#"), (200, 200, 200), (155, 0, 0)),
    material=Material.WOOD,
    tile_type=TileType.WALL,
)
wall_orig.default_wood_hp = get_hp_mult(Material.WOOD) * 1000
wall_orig.hp = get_hp_mult(wall_orig.material) * 1000
wall_orig.dark=(ord("#"), (100, 100, 100), get_color(wall_orig.material)[0])
wall_orig.light0=(ord("#"), (200, 200, 200), get_color(wall_orig.material)[1])
wall_orig.light1=(ord("#"), (200, 200, 200), get_color(wall_orig.material)[2])
wall_orig.light2=(ord("#"), (200, 200, 200), get_color(wall_orig.material)[3])
wall_orig.light3=(ord("#"), (200, 200, 200), get_color(wall_orig.material)[4])
wall_orig.light4=(ord("#"), (200, 200, 200), get_color(wall_orig.material)[5])
wall_orig.water0=(ord("#"), (200, 200, 200), (0, 100, 200))
wall_orig.water1=(ord("1"), (200, 200, 200), (0, 100, 200))
wall_orig.water2=(ord("2"), (200, 200, 200), (0, 100, 200))
wall_orig.water3=(ord("3"), (200, 200, 200), (0, 100, 200))
wall_orig.water4=(ord("4"), (200, 200, 200), (0, 100, 200))

door_orig = NewTile(
    walkable=True,
    transparent=False,
    fire_color=(ord("n"), (200, 200, 200), (155, 0, 0)),
    material=Material.WOOD,
    tile_type=TileType.DOOR,
)
door_orig.default_wood_hp = get_hp_mult(Material.WOOD) * 200
door_orig.hp = get_hp_mult(door_orig.material) * 200
door_orig.dark=(ord("n"), (100, 100, 100), get_color(door_orig.material)[0])
door_orig.light0=(ord("n"), (200, 200, 200), get_color(door_orig.material)[1])
door_orig.light1=(ord("n"), (200, 200, 200), get_color(door_orig.material)[2])
door_orig.light2=(ord("n"), (200, 200, 200), get_color(door_orig.material)[3])
door_orig.light3=(ord("n"), (200, 200, 200), get_color(door_orig.material)[4])
door_orig.light4=(ord("n"), (200, 200, 200), get_color(door_orig.material)[5])
door_orig.water0=(ord("n"), (200, 200, 200), (0, 100, 200))
door_orig.water1=(ord("1"), (200, 200, 200), (0, 100, 200))
door_orig.water2=(ord("2"), (200, 200, 200), (0, 100, 200))
door_orig.water3=(ord("3"), (200, 200, 200), (0, 100, 200))
door_orig.water4=(ord("4"), (200, 200, 200), (0, 100, 200))

down_stairs_orig = NewTile(
    walkable=True,
    transparent=True,
    fire_color=(ord(">"), (200, 200, 200), (155, 0, 0)),
    material=Material.WOOD,
    tile_type=TileType.DOWN_STAIRS,
)
down_stairs_orig.default_wood_hp = get_hp_mult(Material.WOOD) * 300
down_stairs_orig.hp = get_hp_mult(down_stairs_orig.material) * 300
down_stairs_orig.dark=(ord(">"), (100, 100, 100), get_color(down_stairs_orig.material)[0])
down_stairs_orig.light0=(ord(">"), (200, 200, 200), get_color(down_stairs_orig.material)[1])
down_stairs_orig.light1=(ord(">"), (200, 200, 200), get_color(down_stairs_orig.material)[2])
down_stairs_orig.light2=(ord(">"), (200, 200, 200), get_color(down_stairs_orig.material)[3])
down_stairs_orig.light3=(ord(">"), (200, 200, 200), get_color(down_stairs_orig.material)[4])
down_stairs_orig.light4=(ord(">"), (200, 200, 200), get_color(down_stairs_orig.material)[5])
down_stairs_orig.water0=(ord(">"), (200, 200, 200), (0, 100, 200))
down_stairs_orig.water1=(ord("1"), (200, 200, 200), (0, 100, 200))
down_stairs_orig.water2=(ord("2"), (200, 200, 200), (0, 100, 200))
down_stairs_orig.water3=(ord("3"), (200, 200, 200), (0, 100, 200))
down_stairs_orig.water4=(ord("4"), (200, 200, 200), (0, 100, 200))

up_stairs_orig = NewTile(
    walkable=True,
    transparent=True,
    fire_color=(ord("<"), (200, 200, 200), (155, 0, 0)),
    material=Material.WOOD,
    tile_type=TileType.UP_STAIRS,
)
up_stairs_orig.default_wood_hp = get_hp_mult(Material.WOOD) * 300
up_stairs_orig.hp = get_hp_mult(up_stairs_orig.material) * 300
up_stairs_orig.dark=(ord("<"), (100, 100, 100), get_color(up_stairs_orig.material)[0])
up_stairs_orig.light0=(ord("<"), (200, 200, 200), get_color(up_stairs_orig.material)[1])
up_stairs_orig.light1=(ord("<"), (200, 200, 200), get_color(up_stairs_orig.material)[2])
up_stairs_orig.light2=(ord("<"), (200, 200, 200), get_color(up_stairs_orig.material)[3])
up_stairs_orig.light3=(ord("<"), (200, 200, 200), get_color(up_stairs_orig.material)[4])
up_stairs_orig.light4=(ord("<"), (200, 200, 200), get_color(up_stairs_orig.material)[5])
up_stairs_orig.water0=(ord("<"), (200, 200, 200), (0, 100, 200))
up_stairs_orig.water1=(ord("1"), (200, 200, 200), (0, 100, 200))
up_stairs_orig.water2=(ord("2"), (200, 200, 200), (0, 100, 200))
up_stairs_orig.water3=(ord("3"), (200, 200, 200), (0, 100, 200))
up_stairs_orig.water4=(ord("4"), (200, 200, 200), (0, 100, 200))


def get_obj_from_type(tile_type: TileType, material: Material) -> NewTile:
    obj_from_type = {
        TileType.EMPTY: (empty_orig, " "),
        TileType.FLOOR: (floor_orig, "."),
        TileType.WALL: (wall_orig, "#"),
        TileType.DOOR: (door_orig, "n"),
        TileType.DOWN_STAIRS: (down_stairs_orig, ">"),
        TileType.UP_STAIRS: (up_stairs_orig, "<"),
    }
    obj, char = obj_from_type[tile_type]
    obj.material = material
    obj.hp = get_hp_mult(obj.material) * 300
    obj.dark=(ord(char), (100, 100, 100), get_color(obj.material)[0])
    obj.light0=(ord(char), (200, 200, 200), get_color(obj.material)[1])
    obj.light1=(ord(char), (200, 200, 200), get_color(obj.material)[2])
    obj.light2=(ord(char), (200, 200, 200), get_color(obj.material)[3])
    obj.light3=(ord(char), (200, 200, 200), get_color(obj.material)[4])
    obj.light4=(ord(char), (200, 200, 200), get_color(obj.material)[5])
    return obj.get_arr()


empty = empty_orig.get_arr()
floor = floor_orig.get_arr()
wall = wall_orig.get_arr()
door = door_orig.get_arr()    
down_stairs = down_stairs_orig.get_arr()
up_stairs = up_stairs_orig.get_arr()
