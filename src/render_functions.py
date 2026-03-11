from __future__ import annotations

from typing import Tuple, TYPE_CHECKING

import color
import libtcodpy

if TYPE_CHECKING:
    from entity import Actor
    from tcod import Console
    from engine import Engine
    from game_map import GameMap

RENDER_X_SHIFT = 60
RENDER_Y_HEIGHT = 50

def get_names_at_location(x: int, y: int, game_map: GameMap) -> str:
    x += game_map.engine.cam_x
    y += game_map.engine.cam_y

    if not game_map.in_bounds_no_z(x, y):
        return ""
    else:
        vis = False
        for p in game_map.engine.playable_entities:
            if game_map.visible[p.z, x, y]:
                vis = True
        if not vis:
            return ""

    player = game_map.engine.playable_entities[game_map.engine.p_index]
    names = ", ".join(
        entity.name for entity in game_map.entities if entity.z == player.z and entity.x == x and entity.y == y
    )
    return names.capitalize()


def render_bar(console: Console, current_value: int, maximum_value: int, total_width: int) -> None:
    bar_width = int(float(current_value) / maximum_value * total_width)
    console.draw_rect(x=RENDER_X_SHIFT + 0, y=RENDER_Y_HEIGHT + 5, width=total_width, height=1, ch=1, bg=color.bar_empty)
    if bar_width > 0:
        console.draw_rect(
            x=RENDER_X_SHIFT + 0, y=RENDER_Y_HEIGHT + 5, width=bar_width, height=1, ch=1, bg=color.bar_filled
        )
    console.print(
        x=RENDER_X_SHIFT + 1, y=RENDER_Y_HEIGHT + 5, string=f"HP: {current_value}/{maximum_value}", fg=color.bar_text
    )


def render_names_at_mouse_location(console: Console, x: int, y: int, engine: Engine) -> None:
    mouse_x, mouse_y = engine.mouse_location
    names_at_mouse_location = get_names_at_location(
        x=mouse_x, y=mouse_y, game_map=engine.game_map
    )
    console.print(x=RENDER_X_SHIFT + x, y=y, string=names_at_mouse_location)


def render_z_level(console: Console, z_level: int, location: Tuple[int, int]) -> None:
    x, y = location
    console.print(x=RENDER_X_SHIFT + x, y=y, string=f"z level: {z_level}")


def render_commands(console: Console, player: Actor) -> None:
    console.hline(RENDER_X_SHIFT, RENDER_Y_HEIGHT, RENDER_X_SHIFT)
    console.hline(RENDER_X_SHIFT, 0, RENDER_X_SHIFT)
    console.print_box(RENDER_X_SHIFT, 0, RENDER_X_SHIFT, 1, "┤Commands├", alignment=libtcodpy.CENTER)
    console.print_box(RENDER_X_SHIFT, 1, RENDER_X_SHIFT, 1, "[B] Build", alignment=libtcodpy.LEFT)
    console.print_box(RENDER_X_SHIFT, 2, RENDER_X_SHIFT, 1, "[I] Inventory", alignment=libtcodpy.LEFT)
    console.print_box(RENDER_X_SHIFT, 3, RENDER_X_SHIFT, 1, "[T] Character", alignment=libtcodpy.LEFT)
    console.print_box(RENDER_X_SHIFT, 4, RENDER_X_SHIFT, 1, "[M] Move To", alignment=libtcodpy.LEFT)
    if hasattr(player.ai, "work_item"):
        console.print_box(RENDER_X_SHIFT, 5, RENDER_X_SHIFT, 1, "[W] Work Mode is On", alignment=libtcodpy.LEFT)
    else:
        console.print_box(RENDER_X_SHIFT, 5, RENDER_X_SHIFT, 1, "[W] Work Mode is Off", alignment=libtcodpy.LEFT)
