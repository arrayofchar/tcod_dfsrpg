from __future__ import annotations

import lzma
import pickle

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

    def __init__(self, p_index: int, playable_entities: List[Actor]):
        self.message_log = MessageLog()
        self.mouse_location = (0, 0)
        self.p_index = p_index
        self.playable_entities = playable_entities
        self.cam_z = playable_entities[p_index].z
        self.map_mode = False

    def handle_enemy_turns(self) -> None:
        for entity in set(self.game_map.actors) - set(self.playable_entities):
            if entity.ai:
                try:
                    entity.ai.perform()
                except exceptions.Impossible:
                    pass  # Ignore impossible action exceptions from AI.

    def update_fov(self) -> None:
        """Recompute the visible area based on the players point of view."""
        for entity in self.playable_entities:
            self.game_map.visible[entity.z][:] = compute_fov(
                self.game_map.tiles["transparent"][entity.z],
                (entity.x, entity.y),
                radius=8,
            )
            # If a tile is "visible" it should be added to "explored".
            self.game_map.explored[entity.z] |= self.game_map.visible[entity.z]

    def render(self, console: Console) -> None:
        self.game_map.render(console, self.cam_z, self.map_mode)

        self.message_log.render(console=console, x=21, y=45, width=40, height=5)

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
