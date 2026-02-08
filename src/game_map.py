from __future__ import annotations

from typing import Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

import numpy as np  # type: ignore
from tcod.console import Console

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

    def in_bounds(self, z: int, x: int, y: int) -> bool:
        """Return True if x and y are inside of the bounds of this map."""
        return 0 <= z < self.depth and 0 <= x < self.width and 0 <= y < self.height


    def render(self, console: Console, z: int) -> None:
        """
        Renders the map.

        If a tile is in the "visible" array, then draw it with the "light" colors.
        If it isn't, but it's in the "explored" array, then draw it with the "dark" colors.
        Otherwise, the default is "SHROUD".
        """
        console.tiles_rgb[0 : self.width, 0 : self.height] = np.select(
            condlist=[self.visible[z], self.explored[z]],
            choicelist=[self.tiles["light"][z], self.tiles["dark"][z]],
            default=tile_types.SHROUD,
        )

        for entity in self.entities:
            # Only print entities that are in the FOV
            if entity.z == z and self.visible[z][entity.x, entity.y]:
                console.print(x=entity.x, y=entity.y, string=entity.char, fg=entity.color)
