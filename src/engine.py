from __future__ import annotations

import lzma
import pickle
import tile_types

from tcod.console import Console
from tcod.map import compute_fov

import exceptions
from message_log import MessageLog
import render_functions

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from entity import Actor
    from game_map import GameMap

class Engine:
    game_map: GameMap

    def __init__(self, playable_entities: List[Actor]):
        self.message_log = MessageLog()
        self.mouse_location = (0, 0)
        self.p_index = 0
        self.playable_entities = playable_entities
        self.cam_width = 80
        self.cam_height = 43
        self.cam_x: int = 0
        self.cam_y: int = 0
        self.cam_z: int = 0
        self.map_mode = False

    def center_cam_on(self, z: int, x: int, y: int):
        if self.game_map.in_bounds_z(z):
            self.cam_z = z
            self.cam_x = x - int(self.cam_width / 2)
            if self.cam_x < 0:
                self.cam_x = 0
            self.cam_y = y - int(self.cam_height / 2)
            if self.cam_y < 0:
                self.cam_y = 0
            opposite_corner_x = self.cam_x + self.cam_width
            opposite_corner_y = self.cam_y + self.cam_height
            if not self.game_map.in_bounds_x(opposite_corner_x):
                self.cam_x -= opposite_corner_x - self.game_map.width
            if not self.game_map.in_bounds_y(opposite_corner_y):
                self.cam_y -= opposite_corner_y - self.game_map.height
        

    def handle_turns(self) -> None:
        for entity in set(self.game_map.actors):
            if entity.ai:
                try:
                    entity.ai.perform()
                except exceptions.Impossible:
                    pass  # Ignore impossible action exceptions from AI.

    def update_fov(self) -> None:
        """Recompute the visible area based on the players point of view."""
        for entity in self.playable_entities:
            if entity.is_alive:
                self.game_map.visible[entity.z][:] = compute_fov(
                    self.game_map.tiles["transparent"][entity.z],
                    (entity.x, entity.y),
                    radius=8,
                )
                # if empty tile, visible one tile down
                z_1 = entity.z - 1
                if z_1 >= 0:
                    empty = tile_types.empty
                    n_tiles = self.game_map.get_neighbor_tiles(entity.z, entity.x, entity.y)
                    for tile_coord in n_tiles:
                        if self.game_map.tiles[tile_coord] == empty:
                            self.game_map.visible[z_1, tile_coord[1], tile_coord[2]] = True
                # If a tile is "visible" it should be added to "explored".
        self.game_map.explored |= self.game_map.visible

    def render(self, console: Console) -> None:
        self.game_map.render(console, self.cam_z, self.cam_x, self.cam_y, self.map_mode)

        self.message_log.render(console=console, x=21, y=45, width=40, height=5)

        if self.playable_entities and self.p_index < len(self.playable_entities):
            player = self.playable_entities[self.p_index]

            render_functions.render_bar(
                console=console,
                current_value=player.fighter.hp,
                maximum_value=player.fighter.max_hp,
                total_width=20,
            )

        render_functions.render_z_level(
            console=console,
            z_level=self.cam_z,
            location=(0, 47),
        )

        render_functions.render_names_at_mouse_location(
            console=console, x=21, y=44, engine=self
        )


    def save_as(self, filename: str) -> None:
        """Save this Engine instance as a compressed file."""
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)
