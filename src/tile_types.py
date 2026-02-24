from typing import Tuple

import numpy as np  # type: ignore

# Tile graphics structured type compatible with Console.tiles_rgb.
graphic_dt = np.dtype(
    [
        ("ch", np.int32),  # Unicode codepoint.
        ("fg", "3B"),  # 3 unsigned bytes, for RGB colors.
        ("bg", "3B"),
    ]
)

# Tile struct used for statically defined tile data.
tile_dt = np.dtype(
    [
        ("walkable", np.bool),  # True if this tile can be walked over.
        ("transparent", np.bool),  # True if this tile doesn't block FOV.
        ("dark", graphic_dt),  # Graphics for when this tile is not in FOV.
        ("light0", graphic_dt),  # Graphics for when the tile is in FOV.
        ("light1", graphic_dt),  # Graphics for when the tile is in FOV.
        ("light2", graphic_dt),  # Graphics for when the tile is in FOV.
        ("light3", graphic_dt),  # Graphics for when the tile is in FOV.
        ("light4", graphic_dt),  # Graphics for when the tile is in FOV.
    ]
)


def new_tile(
    *,  # Enforce the use of keywords, so that parameter order doesn't matter.
    walkable: int,
    transparent: int,
    dark: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
    light0: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
    light1: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
    light2: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
    light3: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
    light4: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
) -> np.ndarray:
    """Helper function for defining individual tile types """
    return np.array((walkable, transparent, dark, light0, light1, light2, light3, light4), dtype=tile_dt)


# SHROUD represents unexplored, unseen tiles
SHROUD = np.array((ord(" "), (255, 255, 255), (0, 0, 0)), dtype=graphic_dt)

empty = new_tile(
    walkable=False,
    transparent=True,
    dark=(ord(" "), (100, 100, 100), (0, 0, 0)),
    light0=(ord(" "), (200, 200, 200), (20, 20, 20)),
    light1=(ord(" "), (200, 200, 200), (40, 40, 40)),
    light2=(ord(" "), (200, 200, 200), (60, 60, 60)),
    light3=(ord(" "), (200, 200, 200), (80, 80, 80)),
    light4=(ord(" "), (200, 200, 200), (100, 100, 100)),
)
floor = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord("."), (100, 100, 100), (0, 0, 0)),
    light0=(ord("."), (200, 200, 200), (20, 20, 20)),
    light1=(ord("."), (200, 200, 200), (40, 40, 40)),
    light2=(ord("."), (200, 200, 200), (60, 60, 60)),
    light3=(ord("."), (200, 200, 200), (80, 80, 80)),
    light4=(ord("."), (200, 200, 200), (100, 100, 100)),
)
wall = new_tile(
    walkable=False,
    transparent=False,
    dark=(ord("#"), (100, 100, 100), (0, 0, 0)),
    light0=(ord("#"), (200, 200, 200), (20, 20, 20)),
    light1=(ord("#"), (200, 200, 200), (40, 40, 40)),
    light2=(ord("#"), (200, 200, 200), (60, 60, 60)),
    light3=(ord("#"), (200, 200, 200), (80, 80, 80)),
    light4=(ord("#"), (200, 200, 200), (100, 100, 100)),
)
door = new_tile(
    walkable=True,
    transparent=False,
    dark=(ord("n"), (100, 100, 100), (0, 0, 0)),
    light0=(ord("n"), (200, 200, 200), (20, 20, 20)),
    light1=(ord("n"), (200, 200, 200), (40, 40, 40)),
    light2=(ord("n"), (200, 200, 200), (60, 60, 60)),
    light3=(ord("n"), (200, 200, 200), (80, 80, 80)),
    light4=(ord("n"), (200, 200, 200), (100, 100, 100)),
)
down_stairs = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord(">"), (100, 100, 100), (0, 0, 0)),
    light0=(ord(">"), (200, 200, 200), (20, 20, 20)),
    light1=(ord(">"), (200, 200, 200), (40, 40, 40)),
    light2=(ord(">"), (200, 200, 200), (60, 60, 60)),
    light3=(ord(">"), (200, 200, 200), (80, 80, 80)),
    light4=(ord(">"), (200, 200, 200), (100, 100, 100)),
)
up_stairs = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord("<"), (100, 100, 100), (0, 0, 0)),
    light0=(ord("<"), (200, 200, 200), (20, 20, 20)),
    light1=(ord("<"), (200, 200, 200), (40, 40, 40)),
    light2=(ord("<"), (200, 200, 200), (60, 60, 60)),
    light3=(ord("<"), (200, 200, 200), (80, 80, 80)),
    light4=(ord("<"), (200, 200, 200), (100, 100, 100)),
)
