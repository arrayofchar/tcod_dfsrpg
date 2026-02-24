"""Handle the loading and initialization of game sessions."""
from __future__ import annotations

import copy
import random
import lzma
import pickle
import traceback
from typing import Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from entity import Entity, Fixture

import tcod
from tcod import libtcodpy

import color
from engine import Engine
import entity_factories
import input_handler
import tile_types
from procgen.tutorial_dungeon import generate_dungeon
from procgen.cavein_test import generate_map


# Load the background image and remove the alpha channel.
background_image = tcod.image.load("data/menu_background.png")[:, :, :3]

def get_playable_entities(n: int, depth: int) -> List[Entity]:
    playable_entities = []
    for i in range(n):
        player_copy = copy.deepcopy(entity_factories.player)
        player_copy.z = random.randint(0, depth)
        playable_entities.append(player_copy)
    return playable_entities

def get_init_fixtures() -> Dict(Fixture, int):
    return {
        entity_factories.light_src: 10,
    }

def new_game() -> Engine:
    """Return a brand new game session as an Engine instance."""
    map_depth = 10
    map_width = 160 # default 80
    map_height = 86 # default 43

    room_max_size = 10
    room_min_size = 6
    max_rooms = 30

    playable_entities = get_playable_entities(2, map_depth)

    engine = Engine(playable_entities, get_init_fixtures())

    engine.game_map = generate_dungeon(
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
        map_depth=map_depth,
        map_width=map_width,
        map_height=map_height,
        engine=engine,
    )
    p = playable_entities[0]
    engine.p_index = 0
    engine.center_cam_on(p.z, p.x, p.y)
    engine.update_fov()

    engine.message_log.add_message(
        "Hello and welcome, adventurer, to yet another dungeon!", color.welcome_text
    )

    for player in playable_entities:
        dagger = copy.deepcopy(entity_factories.dagger)
        leather_armor = copy.deepcopy(entity_factories.leather_armor)

        dagger.parent = player.inventory
        leather_armor.parent = player.inventory

        player.inventory.items.append(dagger)
        player.equipment.toggle_equip(dagger, add_message=False)

        player.inventory.items.append(leather_armor)
        player.equipment.toggle_equip(leather_armor, add_message=False)

    return engine


def load_game(filename: str, map_mode = False) -> Engine:
    """Load an Engine instance from a file."""
    with open(filename, "rb") as f:
        engine = pickle.loads(lzma.decompress(f.read()))
    assert isinstance(engine, Engine)
    engine.map_mode = map_mode
    p = engine.playable_entities[0]
    engine.center_cam_on(p.z, p.x, p.y)
    return engine

def cavein_test() -> Engine:
    map_depth = 5
    map_width = 80 # default 80, 10
    map_height = 43 # default 43,  8

    playable_entities = get_playable_entities(1, map_depth)

    engine = Engine(playable_entities, get_init_fixtures())
    engine.map_mode = True
    engine.game_map = generate_map(
        map_depth=map_depth,
        map_width=map_width,
        map_height=map_height,
        engine=engine,
    )
    p = playable_entities[0]
    p.parent = engine.game_map
    engine.p_index = 0

    engine.game_map.all_init()
    
    # engine.game_map.remove_tile(1, 6, 6)
    # engine.game_map.remove_tile(2, 41, 40)
    # engine.game_map.remove_tile(2, 41, 2)
    # engine.game_map.remove_tile(1, 41, 41)

    entity_factories.smoke.spawn(engine.game_map, 1, 46, 25, density=1000)
    l_src = entity_factories.light_src.spawn(engine.game_map, 0, 39, 21)
    l_src.effect.activate()

    engine.center_cam_on(p.z, p.x, p.y)
    engine.update_fov()

    engine.message_log.add_message(
        "Cave-in testing area. Beware of falling debris", color.welcome_text
    )
    return engine


class MainMenu(input_handler.BaseEventHandler):
    """Handle the main menu rendering and input."""

    def on_render(self, console: libtcodpy.Console) -> None:
        """Render the main menu on a background image."""
        console.draw_semigraphics(background_image, 0, 0)

        console.print(
            console.width // 2,
            console.height // 2 - 4,
            "Dusk Fanatics",
            fg=color.menu_title,
            alignment=libtcodpy.CENTER,
        )
        console.print(
            console.width // 2,
            console.height - 2,
            "Strategic Realistic Planning Game",
            fg=color.menu_title,
            alignment=libtcodpy.CENTER,
        )

        menu_width = 24
        for i, text in enumerate(
            ["[N] Play a new game", "[C] Continue last game", "[M] Map Mode", "[T] Cave-in Test", "[Q] Quit"]
        ):
            console.print(
                console.width // 2,
                console.height // 2 - 2 + i,
                text.ljust(menu_width),
                fg=color.menu_text,
                bg=color.black,
                alignment=libtcodpy.CENTER,
                bg_blend=libtcodpy.BKGND_ALPHA(64),
            )

    def ev_keydown(
        self, event: tcod.event.KeyDown
    ) -> Optional[input_handler.BaseEventHandler]:
        if event.sym in (tcod.event.KeySym.Q, tcod.event.KeySym.ESCAPE):
            raise SystemExit()
        elif event.sym == tcod.event.KeySym.C:
            try:
                return input_handler.MainGameEventHandler(load_game("savegame.sav"))
            except FileNotFoundError:
                return input_handler.PopupMessage(self, "No saved game to load.")
            except Exception as exc:
                traceback.print_exc()  # Print to stderr.
                return input_handler.PopupMessage(self, f"Failed to load save:\n{exc}")
        elif event.sym == tcod.event.KeySym.N:
            return input_handler.MainGameEventHandler(new_game())
        elif event.sym == tcod.event.KeySym.M:
            return input_handler.MainGameEventHandler(load_game("savegame.sav", map_mode=True))
        elif event.sym == tcod.event.KeySym.T:
            return input_handler.MainGameEventHandler(cavein_test())

        return None
