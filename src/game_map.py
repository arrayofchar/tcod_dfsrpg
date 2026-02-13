from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

import numpy as np  # type: ignore
from tcod.console import Console

from entity import Actor, Item
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

    def get_actor_at_location(self, z: int, x: int, y: int) -> Optional[Actor]:
        for actor in self.actors:
            if actor.x == x and actor.y == y and actor.z == z:
                return actor

        return None

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
            console.rgb[0 : cam_width, 0 : cam_height] = self.tiles["dark"][z][x : x + cam_width, y : y + cam_height]
        else:
            console.rgb[0 : cam_width, 0 : cam_height] = np.select(
                condlist=[
                    self.visible[z][x : x + cam_width, y : y + cam_height],
                    self.explored[z][x : x + cam_width, y : y + cam_height],
                ],
                choicelist=[
                    self.tiles["light"][z][x : x + cam_width, y : y + cam_height],
                    self.tiles["dark"][z][x : x + cam_width, y : y + cam_height],
                ],
                default=tile_types.SHROUD,
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
