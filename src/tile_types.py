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

class Resource(IntEnum):
    WOOD = auto()
    STONE = auto()
    COPPER = auto()
    TIN = auto()
    ZINC = auto()
    IRON = auto()

class Material(IntEnum):
    WOOD = auto()
    STONE = auto()
    METAL = auto()

class TileType(IntEnum):
    EMPTY = auto()
    FLOOR = auto()
    WALL = auto()
    WINDOW = auto()
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
    def __init__(self, walkable: bool, transparent: bool,
                    fire_color: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    material: Material, tile_type: TileType,
                    dark: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    light0: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    light1: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    light2: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    light3: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    light4: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    water0: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    water1: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    water2: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    water3: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    water4: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
                    hp=0, default_wood_hp=0,
                    ):
        self.walkable = walkable
        self.transparent = transparent
        self.fire_color = fire_color
        self.hp = hp
        self.default_wood_hp = default_wood_hp
        self.dark = dark
        self.light0 = light0
        self.light1 = light1
        self.light2 = light2
        self.light3 = light3
        self.light4 = light4
        self.water0 = water0
        self.water1 = water1
        self.water2 = water2
        self.water3 = water3
        self.water4 = water4
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


def get_obj_from_type(tile_type: TileType, material: Material) -> NewTile:
    obj_from_type = {
        TileType.EMPTY: NewTile(
            walkable=False,
            transparent=True,
            fire_color=(ord(" "), (200, 200, 200), (100, 100, 100)),
            material=0,
            tile_type=TileType.EMPTY,
            dark=(ord(" "), (100, 100, 100), (0, 0, 0)),
            light0=(ord(" "), (200, 200, 200), (20, 20, 20)),
            light1=(ord(" "), (200, 200, 200), (40, 40, 40)),
            light2=(ord(" "), (200, 200, 200), (60, 60, 60)),
            light3=(ord(" "), (200, 200, 200), (80, 80, 80)),
            light4=(ord(" "), (200, 200, 200), (100, 100, 100)),
            water0=(ord(" "), (200, 200, 200), (0, 100, 200)),
            water1=(ord("1"), (200, 200, 200), (0, 100, 200)),
            water2=(ord("2"), (200, 200, 200), (0, 100, 200)),
            water3=(ord("3"), (200, 200, 200), (0, 100, 200)),
            water4=(ord("4"), (200, 200, 200), (0, 100, 200)),
        ),
        TileType.FLOOR: NewTile(
            walkable=True,
            transparent=True,
            fire_color=(ord("."), (200, 200, 200), (155, 0, 0)),
            material=material,
            tile_type=TileType.FLOOR,
            default_wood_hp = get_hp_mult(Material.WOOD) * 500,
            hp = get_hp_mult(material) * 500,
            dark=(ord("."), (100, 100, 100), get_color(material)[0]),
            light0=(ord("."), (200, 200, 200), get_color(material)[1]),
            light1=(ord("."), (200, 200, 200), get_color(material)[2]),
            light2=(ord("."), (200, 200, 200), get_color(material)[3]),
            light3=(ord("."), (200, 200, 200), get_color(material)[4]),
            light4=(ord("."), (200, 200, 200), get_color(material)[5]),
            water0=(ord("."), (200, 200, 200), (0, 100, 200)),
            water1=(ord("1"), (200, 200, 200), (0, 100, 200)),
            water2=(ord("2"), (200, 200, 200), (0, 100, 200)),
            water3=(ord("3"), (200, 200, 200), (0, 100, 200)),
            water4=(ord("4"), (200, 200, 200), (0, 100, 200)),
        ),
        TileType.WALL: NewTile(
            walkable=False,
            transparent=False,
            fire_color=(ord("#"), (200, 200, 200), (155, 0, 0)),
            material=material,
            tile_type=TileType.WALL,
            default_wood_hp = get_hp_mult(Material.WOOD) * 1000,
            hp = get_hp_mult(material) * 1000,
            dark=(ord("#"), (100, 100, 100), get_color(material)[0]),
            light0=(ord("#"), (200, 200, 200), get_color(material)[1]),
            light1=(ord("#"), (200, 200, 200), get_color(material)[2]),
            light2=(ord("#"), (200, 200, 200), get_color(material)[3]),
            light3=(ord("#"), (200, 200, 200), get_color(material)[4]),
            light4=(ord("#"), (200, 200, 200), get_color(material)[5]),
            water0=(ord("#"), (200, 200, 200), (0, 100, 200)),
            water1=(ord("1"), (200, 200, 200), (0, 100, 200)),
            water2=(ord("2"), (200, 200, 200), (0, 100, 200)),
            water3=(ord("3"), (200, 200, 200), (0, 100, 200)),
            water4=(ord("4"), (200, 200, 200), (0, 100, 200)),
        ),
        TileType.WINDOW: NewTile(
            walkable=False,
            transparent=True,
            fire_color=(ord("⌂"), (200, 200, 200), (155, 0, 0)),
            material=material,
            tile_type=TileType.WINDOW,
            default_wood_hp = get_hp_mult(Material.WOOD) * 200,
            hp = get_hp_mult(material) * 200,
            dark=(ord("⌂"), (100, 100, 100), get_color(material)[0]),
            light0=(ord("⌂"), (200, 200, 200), get_color(material)[1]),
            light1=(ord("⌂"), (200, 200, 200), get_color(material)[2]),
            light2=(ord("⌂"), (200, 200, 200), get_color(material)[3]),
            light3=(ord("⌂"), (200, 200, 200), get_color(material)[4]),
            light4=(ord("⌂"), (200, 200, 200), get_color(material)[5]),
            water0=(ord("⌂"), (200, 200, 200), (0, 100, 200)),
            water1=(ord("1"), (200, 200, 200), (0, 100, 200)),
            water2=(ord("2"), (200, 200, 200), (0, 100, 200)),
            water3=(ord("3"), (200, 200, 200), (0, 100, 200)),
            water4=(ord("4"), (200, 200, 200), (0, 100, 200)),
        ),
        TileType.DOOR: NewTile(
            walkable=True,
            transparent=False,
            fire_color=(ord("∩"), (200, 200, 200), (155, 0, 0)),
            material=material,
            tile_type=TileType.DOOR,
            default_wood_hp = get_hp_mult(Material.WOOD) * 300,
            hp = get_hp_mult(material) * 300,
            dark=(ord("∩"), (100, 100, 100), get_color(material)[0]),
            light0=(ord("∩"), (200, 200, 200), get_color(material)[1]),
            light1=(ord("∩"), (200, 200, 200), get_color(material)[2]),
            light2=(ord("∩"), (200, 200, 200), get_color(material)[3]),
            light3=(ord("∩"), (200, 200, 200), get_color(material)[4]),
            light4=(ord("∩"), (200, 200, 200), get_color(material)[5]),
            water0=(ord("∩"), (200, 200, 200), (0, 100, 200)),
            water1=(ord("1"), (200, 200, 200), (0, 100, 200)),
            water2=(ord("2"), (200, 200, 200), (0, 100, 200)),
            water3=(ord("3"), (200, 200, 200), (0, 100, 200)),
            water4=(ord("4"), (200, 200, 200), (0, 100, 200)),
        ),
        TileType.DOWN_STAIRS: NewTile(
            walkable=True,
            transparent=True,
            fire_color=(ord(">"), (200, 200, 200), (155, 0, 0)),
            material=material,
            tile_type=TileType.DOWN_STAIRS,
            default_wood_hp = get_hp_mult(Material.WOOD) * 300,
            hp = get_hp_mult(material) * 300,
            dark=(ord(">"), (100, 100, 100), get_color(material)[0]),
            light0=(ord(">"), (200, 200, 200), get_color(material)[1]),
            light1=(ord(">"), (200, 200, 200), get_color(material)[2]),
            light2=(ord(">"), (200, 200, 200), get_color(material)[3]),
            light3=(ord(">"), (200, 200, 200), get_color(material)[4]),
            light4=(ord(">"), (200, 200, 200), get_color(material)[5]),
            water0=(ord(">"), (200, 200, 200), (0, 100, 200)),
            water1=(ord("1"), (200, 200, 200), (0, 100, 200)),
            water2=(ord("2"), (200, 200, 200), (0, 100, 200)),
            water3=(ord("3"), (200, 200, 200), (0, 100, 200)),
            water4=(ord("4"), (200, 200, 200), (0, 100, 200)),
        ),
        TileType.UP_STAIRS: NewTile(
            walkable=True,
            transparent=True,
            fire_color=(ord("<"), (200, 200, 200), (155, 0, 0)),
            material=material,
            tile_type=TileType.UP_STAIRS,
            default_wood_hp = get_hp_mult(Material.WOOD) * 300,
            hp = get_hp_mult(material) * 300,
            dark=(ord("<"), (100, 100, 100), get_color(material)[0]),
            light0=(ord("<"), (200, 200, 200), get_color(material)[1]),
            light1=(ord("<"), (200, 200, 200), get_color(material)[2]),
            light2=(ord("<"), (200, 200, 200), get_color(material)[3]),
            light3=(ord("<"), (200, 200, 200), get_color(material)[4]),
            light4=(ord("<"), (200, 200, 200), get_color(material)[5]),
            water0=(ord("<"), (200, 200, 200), (0, 100, 200)),
            water1=(ord("1"), (200, 200, 200), (0, 100, 200)),
            water2=(ord("2"), (200, 200, 200), (0, 100, 200)),
            water3=(ord("3"), (200, 200, 200), (0, 100, 200)),
            water4=(ord("4"), (200, 200, 200), (0, 100, 200)),
        ),
    }
    return obj_from_type[tile_type].get_arr()


empty = get_obj_from_type(TileType.EMPTY, Material.WOOD)
floor = get_obj_from_type(TileType.FLOOR, Material.WOOD)
wall = get_obj_from_type(TileType.WALL, Material.WOOD)
window = get_obj_from_type(TileType.WINDOW, Material.WOOD)
door = get_obj_from_type(TileType.DOOR, Material.WOOD)
down_stairs = get_obj_from_type(TileType.DOWN_STAIRS, Material.WOOD)
up_stairs = get_obj_from_type(TileType.UP_STAIRS, Material.WOOD)
