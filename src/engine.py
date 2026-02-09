from __future__ import annotations

from typing import TYPE_CHECKING

from tcod.context import Context
from tcod.console import Console
from tcod.map import compute_fov

from input_handler import EventHandler

if TYPE_CHECKING:
    from entity import Entity
    from game_map import GameMap


class Engine:
    game_map: GameMap

    def __init__(self, player: Entity):
        self.event_handler: EventHandler = EventHandler(self)
        self.player = player

    def handle_enemy_turns(self) -> None:
        for entity in self.game_map.entities - {self.player}:
            pass
            # print(f'The {entity.name} wonders when it will get to take a real turn.')

    def update_fov(self) -> None:
        """Recompute the visible area based on the players point of view."""
        self.game_map.visible[self.player.z][:] = compute_fov(
            self.game_map.tiles["transparent"][self.player.z],
            (self.player.x, self.player.y),
            radius=8,
        )
        # If a tile is "visible" it should be added to "explored".
        self.game_map.explored[self.player.z] |= self.game_map.visible[self.player.z]

    def render(self, console: Console, context: Context) -> None:
        self.game_map.render(console, self.player.z)

        context.present(console)

        console.clear()
