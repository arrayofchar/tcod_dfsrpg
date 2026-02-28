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
        ("hp", np.uint16),       # max hp around 32,000
        ("default_wood_hp", np.uint16),
        ("fire_color", graphic_dt),  # Graphics for when this tile is on fire in FOV.
        ("dark", graphic_dt),  # Graphics for when this tile is not in FOV.
        ("light0", graphic_dt),  # Graphics for when the tile is in FOV.
        ("light1", graphic_dt),  # Graphics for when the tile is in FOV.
        ("light2", graphic_dt),  # Graphics for when the tile is in FOV.
        ("light3", graphic_dt),  # Graphics for when the tile is in FOV.
        ("light4", graphic_dt),  # Graphics for when the tile is in FOV.
        ("material", np.uint8),  # Material of the tile
        ("tile_type", np.uint8),
    ]
)

FIRE_DMG = 5

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
        self.material = material
        self.tile_type = tile_type

    def get_arr(self) -> np.ndarray:
        """Helper function for defining individual tile types """
        return np.array((self.walkable, self.transparent, self.hp, self.default_wood_hp, \
            self.fire_color, self.dark, self.light0, self.light1, self.light2, self.light3, self.light4, \
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


empty = NewTile(
    walkable=False,
    transparent=True,
    fire_color=(ord(" "), (200, 200, 200), (100, 100, 100)),
    material=0,
    tile_type=TileType.EMPTY,
)
empty.dark=(ord(" "), (100, 100, 100), (0, 0, 0))
empty.light0=(ord(" "), (200, 200, 200), (20, 20, 20))
empty.light1=(ord(" "), (200, 200, 200), (40, 40, 40))
empty.light2=(ord(" "), (200, 200, 200), (60, 60, 60))
empty.light3=(ord(" "), (200, 200, 200), (80, 80, 80))
empty.light4=(ord(" "), (200, 200, 200), (100, 100, 100))
empty = empty.get_arr()

floor = NewTile(
    walkable=True,
    transparent=True,
    fire_color=(ord("."), (200, 200, 200), (155, 0, 0)),
    material=Material.WOOD,
    tile_type=TileType.FLOOR,
)
floor.default_wood_hp = get_hp_mult(Material.WOOD) * 50
floor.hp = get_hp_mult(floor.material) * 50
floor.dark=(ord("."), (100, 100, 100), get_color(floor.material)[0])
floor.light0=(ord("."), (200, 200, 200), get_color(floor.material)[1])
floor.light1=(ord("."), (200, 200, 200), get_color(floor.material)[2])
floor.light2=(ord("."), (200, 200, 200), get_color(floor.material)[3])
floor.light3=(ord("."), (200, 200, 200), get_color(floor.material)[4])
floor.light4=(ord("."), (200, 200, 200), get_color(floor.material)[5])
floor = floor.get_arr()

wall = NewTile(
    walkable=False,
    transparent=False,
    fire_color=(ord("#"), (200, 200, 200), (155, 0, 0)),
    material=Material.WOOD,
    tile_type=TileType.WALL,
)
wall.default_wood_hp = get_hp_mult(Material.WOOD) * 1000
wall.hp = get_hp_mult(wall.material) * 1000
wall.dark=(ord("#"), (100, 100, 100), get_color(wall.material)[0])
wall.light0=(ord("#"), (200, 200, 200), get_color(wall.material)[1])
wall.light1=(ord("#"), (200, 200, 200), get_color(wall.material)[2])
wall.light2=(ord("#"), (200, 200, 200), get_color(wall.material)[3])
wall.light3=(ord("#"), (200, 200, 200), get_color(wall.material)[4])
wall.light4=(ord("#"), (200, 200, 200), get_color(wall.material)[5])
wall = wall.get_arr()

door = NewTile(
    walkable=True,
    transparent=False,
    fire_color=(ord("n"), (200, 200, 200), (155, 0, 0)),
    material=Material.WOOD,
    tile_type=TileType.DOOR,
)
door.default_wood_hp = get_hp_mult(Material.WOOD) * 200
door.hp = get_hp_mult(door.material) * 200
door.dark=(ord("n"), (100, 100, 100), get_color(door.material)[0])
door.light0=(ord("n"), (200, 200, 200), get_color(door.material)[1])
door.light1=(ord("n"), (200, 200, 200), get_color(door.material)[2])
door.light2=(ord("n"), (200, 200, 200), get_color(door.material)[3])
door.light3=(ord("n"), (200, 200, 200), get_color(door.material)[4])
door.light4=(ord("n"), (200, 200, 200), get_color(door.material)[5])
door = door.get_arr()    

down_stairs = NewTile(
    walkable=True,
    transparent=True,
    fire_color=(ord(">"), (200, 200, 200), (155, 0, 0)),
    material=Material.WOOD,
    tile_type=TileType.DOWN_STAIRS,
)
down_stairs.default_wood_hp = get_hp_mult(Material.WOOD) * 300
down_stairs.hp = get_hp_mult(down_stairs.material) * 300
down_stairs.dark=(ord(">"), (100, 100, 100), get_color(down_stairs.material)[0])
down_stairs.light0=(ord(">"), (200, 200, 200), get_color(down_stairs.material)[1])
down_stairs.light1=(ord(">"), (200, 200, 200), get_color(down_stairs.material)[2])
down_stairs.light2=(ord(">"), (200, 200, 200), get_color(down_stairs.material)[3])
down_stairs.light3=(ord(">"), (200, 200, 200), get_color(down_stairs.material)[4])
down_stairs.light4=(ord(">"), (200, 200, 200), get_color(down_stairs.material)[5])
down_stairs = down_stairs.get_arr()

up_stairs = NewTile(
    walkable=True,
    transparent=True,
    fire_color=(ord("<"), (200, 200, 200), (155, 0, 0)),
    material=Material.WOOD,
    tile_type=TileType.UP_STAIRS,
)
up_stairs.default_wood_hp = get_hp_mult(Material.WOOD) * 300
up_stairs.hp = get_hp_mult(up_stairs.material) * 300
up_stairs.dark=(ord("<"), (100, 100, 100), get_color(up_stairs.material)[0])
up_stairs.light0=(ord("<"), (200, 200, 200), get_color(up_stairs.material)[1])
up_stairs.light1=(ord("<"), (200, 200, 200), get_color(up_stairs.material)[2])
up_stairs.light2=(ord("<"), (200, 200, 200), get_color(up_stairs.material)[3])
up_stairs.light3=(ord("<"), (200, 200, 200), get_color(up_stairs.material)[4])
up_stairs.light4=(ord("<"), (200, 200, 200), get_color(up_stairs.material)[5])
up_stairs = up_stairs.get_arr()

get_obj_from_type = {
    TileType.EMPTY: empty,
    TileType.FLOOR: floor,
    TileType.WALL: wall,
    TileType.DOOR: door,
    TileType.DOWN_STAIRS: down_stairs,
    TileType.UP_STAIRS: up_stairs,
}