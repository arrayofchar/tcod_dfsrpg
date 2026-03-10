from __future__ import annotations

import os

from typing import Callable, Optional, Tuple, TYPE_CHECKING, Union, List

import tcod
from tcod import libtcodpy

import actions
from components import ai
import color
from render_functions import RENDER_X_SHIFT, RENDER_Y_HEIGHT, render_names_at_mouse_location
import exceptions
from entity import BuildRemoveTile
import tile_types

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity, Item

MOVE_KEYS = {
    # Arrow keys.
    tcod.event.KeySym.W: (0, -1),
    tcod.event.KeySym.X: (0, 1),
    tcod.event.KeySym.A: (-1, 0),
    tcod.event.KeySym.D: (1, 0),
    tcod.event.KeySym.Q: (-1, -1),
    tcod.event.KeySym.Z: (-1, 1),
    tcod.event.KeySym.E: (1, -1),
    tcod.event.KeySym.C: (1, 1),
    # Numpad keys.
    # tcod.event.KeySym.KP_1: (-1, 1),
    # tcod.event.KeySym.KP_2: (0, 1),
    # tcod.event.KeySym.KP_3: (1, 1),
    # tcod.event.KeySym.KP_4: (-1, 0),
    # tcod.event.KeySym.KP_6: (1, 0),
    # tcod.event.KeySym.KP_7: (-1, -1),
    # tcod.event.KeySym.KP_8: (0, -1),
    # tcod.event.KeySym.KP_9: (1, -1),
    # Vi keys.
    # tcod.event.KeySym.h: (-1, 0),
    # tcod.event.KeySym.j: (0, 1),
    # tcod.event.KeySym.k: (0, -1),
    # tcod.event.KeySym.l: (1, 0),
    # tcod.event.KeySym.y: (-1, -1),
    # tcod.event.KeySym.u: (1, -1),
    # tcod.event.KeySym.b: (-1, 1),
    # tcod.event.KeySym.n: (1, 1),
}

WAIT_KEYS = {
    tcod.event.KeySym.S,
    tcod.event.KeySym.KP_5,
    tcod.event.KeySym.CLEAR,
}

CONFIRM_KEYS = {
    tcod.event.KeySym.RETURN,
    tcod.event.KeySym.KP_ENTER,
}

CURSOR_Y_KEYS = {
    tcod.event.KeySym.UP: -1,
    tcod.event.KeySym.DOWN: 1,
    tcod.event.KeySym.PAGEUP: -10,
    tcod.event.KeySym.PAGEDOWN: 10,
}

CAM_KEYS = {
    tcod.event.KeySym.UP: (0, -1),
    tcod.event.KeySym.DOWN: (0, 1),
    tcod.event.KeySym.LEFT: (-1, 0),
    tcod.event.KeySym.RIGHT: (1, 0),
}

ActionOrHandler = Union[actions.Action, "BaseEventHandler"]
"""An event handler return value which can trigger an action or switch active handlers.

If a handler is returned then it will become the active handler for future events.
If an action is returned it will be attempted and if it's valid then
MainGameEventHandler will become the active handler.
"""

class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle an event and return the next active event handler."""
        state = self.dispatch(event)
        if isinstance(state, BaseEventHandler):
            return state
        assert not isinstance(state, actions.Action), f"{self!r} can not handle actions."
        return self

    def on_render(self, console: tcod.Console) -> None:
        raise NotImplementedError()

    def ev_quit(self, event: tcod.event.Quit) -> Optional[actions.Action]:
        raise SystemExit()

class PopupMessage(BaseEventHandler):
    """Display a popup text window."""

    def __init__(self, parent_handler: BaseEventHandler, text: str):
        self.parent = parent_handler
        self.text = text

    def on_render(self, console: tcod.Console) -> None:
        """Render the parent and dim the result, then print the message on top."""
        self.parent.on_render(console)
        console.tiles_rgb["fg"] //= 8
        console.tiles_rgb["bg"] //= 8

        console.print(
            console.width // 2,
            console.height // 2,
            self.text,
            fg=color.white,
            bg=color.black,
            alignment=libtcodpy.CENTER,
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        """Any key returns to the parent handler."""
        return self.parent

class EventHandler(BaseEventHandler):
    def __init__(self, engine: Engine):
        self.engine = engine

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle events for input handlers with an engine."""
        action_or_state = self.dispatch(event)
        if isinstance(action_or_state, BaseEventHandler):
            return action_or_state
        if self.handle_action(action_or_state):
            # A valid action was performed.
            if not self.engine.playable_entities:
                # The player was killed sometime during or after the action.
                return GameOverEventHandler(self.engine)
            for i, p in enumerate(self.engine.playable_entities):
                if p.level.requires_level_up:
                    return LevelUpEventHandler(self.engine, i)
            return MainGameEventHandler(self.engine)  # Return to the main handler.
        return self

    def handle_action(self, action: Optional[actions.Action]) -> bool:
        """Handle actions returned from event methods.

        Returns True if the action will advance a turn.
        """
        if action is None:
            return False

        # try:
        #     action.perform()
        # except exceptions.Impossible as exc:
        #     self.engine.message_log.add_message(exc.args[0], color.impossible)
        #     return False  # Skip enemy turn on exceptions.

        self.engine.handle_turns()

        self.engine.update_fov()
        return True

    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        # pass
        if self.engine.game_map.in_bounds_no_z(event.tile.x, event.tile.y):
            self.engine.mouse_location = int(event.tile.x), int(event.tile.y)

    def on_render(self, console: tcod.Console) -> None:
        self.engine.render(console)
    
class TimeStepHandler(EventHandler):
    """ Handles time step increments """
    def __init__(self, engine: Engine, steps: int):
        super().__init__(engine)
        self.steps = steps

    def handle_action(self, action: Optional[actions.Action]) -> bool:
        for i in range(self.steps):
            self.engine.handle_turns()

        self.engine.update_fov()
        return True

class AskUserEventHandler(EventHandler):
    """Handles user input for actions which require special input."""

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """By default any key exits this input handler."""
        if event.sym in {  # Ignore modifier keys.
            tcod.event.KeySym.LSHIFT,
            tcod.event.KeySym.RSHIFT,
            tcod.event.KeySym.LCTRL,
            tcod.event.KeySym.RCTRL,
            tcod.event.KeySym.LALT,
            tcod.event.KeySym.RALT,
        }:
            return None
        return self.on_exit()

    def ev_mousebuttondown(
        self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """By default any mouse click exits this input handler."""
        return self.on_exit()

    def on_exit(self) -> Optional[ActionOrHandler]:
        """Called when the user is trying to exit or cancel an action."""
        return MainGameEventHandler(self.engine)

class BuildSelectionEventHandler(EventHandler):
    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.cursor = 0
        self.m_cur = 0
        self.materials = [
            ("Wood", tile_types.Material.WOOD, (250, 130, 0)),
            ("Stone", tile_types.Material.STONE, (250, 250, 250)),
            ("Metal", tile_types.Material.METAL, (130, 130, 250)),
        ]
        self.items = [
            ("[F] Floor", BuildRemoveTile(
                        name="Building Floor",
                        char = "•",
                        color=(0, 0, 200),
                        build_task=True,
                        build_type=tile_types.TileType.FLOOR,
                        turns_remaining=15,
                    )),
            ("[W] Wall", BuildRemoveTile(
                        name="Building Wall",
                        char = "#",
                        color=(0, 0, 200),
                        build_task=True,
                        build_type=tile_types.TileType.WALL,
                        turns_remaining=20,
                    )),
            ("[O] Window", BuildRemoveTile(
                        name="Building Window",
                        char = "⌂",
                        color=(0, 0, 200),
                        build_task=True,
                        build_type=tile_types.TileType.WINDOW,
                        turns_remaining=20,
                    )),
            ("[N] Door", BuildRemoveTile(
                        name="Building Door",
                        char = "n",
                        color=(0, 0, 200),
                        build_task=True,
                        build_type=tile_types.TileType.DOOR,
                        turns_remaining=20,
                    )),
            ("[.] Down Stairs", BuildRemoveTile(
                        name="Building Down Stairs",
                        char = ">",
                        color=(0, 0, 200),
                        build_task=True,
                        build_type=tile_types.TileType.DOWN_STAIRS,
                        turns_remaining=20,
                    )),
            ("[,] Up Stairs", BuildRemoveTile(
                        name="Building Up Stairs",
                        char = "<",
                        color=(0, 0, 200),
                        build_task=True,
                        build_type=tile_types.TileType.UP_STAIRS,
                        turns_remaining=20,
                    )),
            ("[C] Cancel Work Item", None),
            ("[R] Remove Tile", BuildRemoveTile(
                        build_task=False,
                        turns_remaining=10,
                    )),
            ("[D] Dig Tile", BuildRemoveTile(
                        build_task=False,
                        turns_remaining=10,
                    )),
        ]

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            if adjust < 0:
                self.cursor = (self.cursor - 1) % len(self.items)
            elif adjust > 0:
                self.cursor = (self.cursor + 1) % len(self.items)
        elif event.sym == tcod.event.KeySym.TAB:
            self.m_cur = (self.m_cur + 1) % len(self.materials)
        elif event.sym == tcod.event.KeySym.HOME:
            self.cursor = 0
        elif event.sym == tcod.event.KeySym.END:
            self.cursor = len(self.items) - 1
        elif event.sym == tcod.event.KeySym.ESCAPE:
            return MainGameEventHandler(self.engine)
        else:
            p = self.engine.playable_entities[self.engine.p_index]
            if event.sym in CONFIRM_KEYS:
                obj = self.items[self.cursor][1]
            elif event.sym == tcod.event.KeySym.F:
                obj = self.items[0][1]
            elif event.sym == tcod.event.KeySym.W:
                obj = self.items[1][1]
            elif event.sym == tcod.event.KeySym.O:
                obj = self.items[2][1]
            elif event.sym == tcod.event.KeySym.N:
                obj = self.items[3][1]
            elif event.sym == tcod.event.KeySym.PERIOD:
                obj = self.items[4][1]
            elif event.sym == tcod.event.KeySym.COMMA:
                obj = self.items[5][1]
            elif event.sym == tcod.event.KeySym.C:
                obj = self.items[6][1]
            elif event.sym == tcod.event.KeySym.R:
                obj = self.items[7][1]
            elif event.sym == tcod.event.KeySym.D:
                obj = self.items[8][1]
            else:
                return None
            
            if self.cursor == len(self.items) - 3 or event.sym == tcod.event.KeySym.C:
                return SingleRangedAttackHandler(self.engine,
                    callback=lambda xy: actions.BuildAction(p, obj, \
                        (xy[0] + self.engine.cam_x, xy[1] + self.engine.cam_y), cancel = True))
            elif self.cursor == len(self.items) - 2 or event.sym == tcod.event.KeySym.R:
                return SingleRangedAttackHandler(self.engine,
                    callback=lambda xy: actions.RemoveDigAction(p, obj, \
                        (xy[0] + self.engine.cam_x, xy[1] + self.engine.cam_y), remove = True))
            elif self.cursor == len(self.items) - 1 or event.sym == tcod.event.KeySym.D:
                return SingleRangedAttackHandler(self.engine,
                    callback=lambda xy: actions.RemoveDigAction(p, obj, \
                        (xy[0] + self.engine.cam_x, xy[1] + self.engine.cam_y), remove = False))
            else:
                obj.material = self.materials[self.m_cur][1]
                return SingleRangedAttackHandler(self.engine,
                        callback=lambda xy: actions.BuildAction(p, obj, \
                            (xy[0] + self.engine.cam_x, xy[1] + self.engine.cam_y)))
        
    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        console.rect(RENDER_X_SHIFT, 0, RENDER_X_SHIFT, RENDER_Y_HEIGHT, clear=True)
        console.hline(RENDER_X_SHIFT, 0, RENDER_X_SHIFT)
        console.print_box(RENDER_X_SHIFT, 0, RENDER_X_SHIFT, 1, "┤Building Selection├", alignment=libtcodpy.CENTER)
        for i, tup in enumerate(self.materials):
            if i == self.m_cur:
                bg = (100, 100, 100)
            else:
                bg = (0, 0, 0)
            console.print(x=RENDER_X_SHIFT + (i * 10) + 10, y=2, string=tup[0], fg=tup[2], bg=bg)
        for i, tup in enumerate(self.items):
            if i == self.cursor:
                bg = (150, 150, 150)
            else:
                bg = (0, 0, 0)
            console.print(x=RENDER_X_SHIFT, y=i+4, string=tup[0], bg=bg)


class CharacterScreenEventHandler(AskUserEventHandler):

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        player = self.engine.playable_entities[self.engine.p_index]

        console.rect(RENDER_X_SHIFT, 0, RENDER_X_SHIFT, RENDER_Y_HEIGHT, clear=True)
        console.hline(RENDER_X_SHIFT, 0, RENDER_X_SHIFT)
        console.print_box(RENDER_X_SHIFT, 0, RENDER_X_SHIFT, 1, "┤Character Information├", alignment=libtcodpy.CENTER)
        console.print(x=RENDER_X_SHIFT, y=1, string=f"Level: {player.level.current_level}")
        console.print(x=RENDER_X_SHIFT, y=2, string=f"XP: {player.level.current_xp}")
        console.print(x=RENDER_X_SHIFT, y=3, string=f"XP for next Level: {player.level.experience_to_next_level}")
        console.print(x=RENDER_X_SHIFT, y=4, string=f"Attack: {player.fighter.power}")
        console.print(x=RENDER_X_SHIFT, y=5, string=f"Defense: {player.fighter.defense}")


class LevelUpEventHandler(AskUserEventHandler):
    TITLE = "Level Up"

    def __init__(self, engine: Engine, index: int):
        super().__init__(engine)
        self.player = engine.playable_entities[index]

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)

        if self.player.x <= 30:
            x = 40
        else:
            x = 0

        console.draw_frame(
            x=x,
            y=0,
            width=35,
            height=8,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(x=x + 1, y=1, string="Congratulations! You level up!")
        console.print(x=x + 1, y=2, string="Select an attribute to increase.")

        console.print(
            x=x + 1,
            y=4,
            string=f"a) Constitution (+20 HP, from {self.player.fighter.max_hp})",
        )
        console.print(
            x=x + 1,
            y=5,
            string=f"b) Strength (+1 attack, from {self.player.fighter.power})",
        )
        console.print(
            x=x + 1,
            y=6,
            string=f"c) Agility (+1 defense, from {self.player.fighter.defense})",
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        key = event.sym
        index = key - tcod.event.KeySym.A

        if 0 <= index <= 2:
            if index == 0:
                self.player.level.increase_max_hp()
            elif index == 1:
                self.player.level.increase_power()
            else:
                self.player.level.increase_defense()
        else:
            self.engine.message_log.add_message("Invalid entry.", color.invalid)

            return None

        return super().ev_keydown(event)

    def ev_mousebuttondown(
        self, event: tcod.event.MouseButtonDown
    ) -> Optional[ActionOrHandler]:
        """
        Don't allow the player to click to exit the menu, like normal.
        """
        return None

class InventoryEventHandler(EventHandler):
    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.cursor = 0
        self.m_cur = 0
        self.actions = [
            "Equip",
            "Drop",
        ]

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        console.rect(RENDER_X_SHIFT, 0, RENDER_X_SHIFT, RENDER_Y_HEIGHT, clear=True)
        console.hline(RENDER_X_SHIFT, 0, RENDER_X_SHIFT)
        console.print_box(RENDER_X_SHIFT, 0, RENDER_X_SHIFT, 1, "┤Inventory├", alignment=libtcodpy.CENTER)
        for i, s in enumerate(self.actions):
            if i == self.m_cur:
                bg = (100, 100, 100)
            else:
                bg = (0, 0, 0)
            console.print(x=RENDER_X_SHIFT + (i * 10) + 10, y=2, string=s, bg=bg)
        player = self.engine.playable_entities[self.engine.p_index]
        if len(player.inventory.items) > 0:
            for i, item in enumerate(player.inventory.items):
                item_key = chr(ord("a") + i)
                is_equipped = player.equipment.item_is_equipped(item)

                item_string = f"({item_key}) {item.name}"

                if is_equipped:
                    item_string = f"{item_string} (E)"
                if i == self.cursor:
                    bg = (150, 150, 150)
                else:
                    bg = (0, 0, 0)
                console.print(RENDER_X_SHIFT, i + 4, item_string, bg=bg)
        else:
            console.print(RENDER_X_SHIFT, 3, "(Empty)")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        player = self.engine.playable_entities[self.engine.p_index]
        items = list(player.inventory.items)
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            if adjust < 0:
                self.cursor = (self.cursor - 1) % len(items)
            elif adjust > 0:
                self.cursor = (self.cursor + 1) % len(items)
        elif event.sym == tcod.event.KeySym.TAB:
            self.m_cur = (self.m_cur + 1) % len(self.actions)
        elif event.sym == tcod.event.KeySym.HOME:
            self.cursor = 0
        elif event.sym == tcod.event.KeySym.END:
            self.cursor = len(items) - 1
        elif event.sym == tcod.event.KeySym.ESCAPE:
            return MainGameEventHandler(self.engine)
        else:
            selected_item = None
            if event.sym in CONFIRM_KEYS:
                selected_item = items[self.cursor]
            else:
                index = event.sym - tcod.event.KeySym.A
                if 0 <= index <= 26:
                    try:
                        selected_item = items[index]
                    except IndexError:
                        self.engine.message_log.add_message("Invalid entry.", color.invalid)
                        return None
            return self.on_item_selected(selected_item)
        return super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        player = self.engine.playable_entities[self.engine.p_index]
        if self.actions[self.m_cur] == "Equip":
            if item.consumable:
                return item.consumable.get_action(player)
            elif item.equippable:
                return actions.EquipAction(player, item)
            else:
                return None
        elif self.actions[self.m_cur] == "Drop":
            return actions.DropItem(player, item)

class HistoryViewer(EventHandler):
    """Print the history on a larger window which can be navigated."""

    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.log_length = len(engine.message_log.messages)
        self.cursor = self.log_length - 1

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)  # Draw the main state as the background.
        log_console = tcod.Console(console.width - RENDER_X_SHIFT, console.height - 10)

        # Draw a frame with a custom banner title.
        # log_console.draw_frame(0, 0, RENDER_X_SHIFT, 40)
        log_console.hline(0, 0, RENDER_X_SHIFT)
        log_console.print_box(0, 0, RENDER_X_SHIFT, 1, "┤Message History├", alignment=libtcodpy.CENTER)

        # Render the message log using the cursor parameter.
        self.engine.message_log.render_messages(
            log_console,
            0,
            0,
            RENDER_X_SHIFT,
            RENDER_Y_HEIGHT,
            self.engine.message_log.messages[: self.cursor + 1],
        )
        log_console.blit(console, RENDER_X_SHIFT, 0)

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[MainGameEventHandler]:
        # Fancy conditional movement to make it feel right.
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            if adjust < 0 and self.cursor == 0:
                # Only move from the top to the bottom when you're on the edge.
                self.cursor = self.log_length - 1
            elif adjust > 0 and self.cursor == self.log_length - 1:
                # Same with bottom to top movement.
                self.cursor = 0
            else:
                # Otherwise move while staying clamped to the bounds of the history log.
                self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
        elif event.sym == tcod.event.KeySym.HOME:
            self.cursor = 0  # Move directly to the top message.
        elif event.sym == tcod.event.KeySym.END:
            self.cursor = self.log_length - 1  # Move directly to the last message.
        else:  # Any other key moves back to the main game state.
            return MainGameEventHandler(self.engine)
        return None

class SelectIndexHandler(AskUserEventHandler):
    """Handles asking the user for an index on the map."""

    def __init__(self, engine: Engine):
        """Sets the cursor to the player when this handler is constructed."""
        super().__init__(engine)
        player = self.engine.playable_entities[self.engine.p_index]
        engine.mouse_location = player.x - self.engine.cam_x, player.y - self.engine.cam_y

    def on_render(self, console: tcod.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)
        x, y = self.engine.mouse_location
        console.tiles_rgb["bg"][x, y] = color.white
        console.tiles_rgb["fg"][x, y] = color.black

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        """Check for key movement or confirmation keys."""
        key = event.sym
        if key in MOVE_KEYS:
            modifier = 1  # Holding modifier keys will speed up key movement.
            if event.mod & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
                modifier *= 5
            if event.mod & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
                modifier *= 10
            if event.mod & (tcod.event.KMOD_LALT | tcod.event.KMOD_RALT):
                modifier *= 20

            x, y = self.engine.mouse_location
            dx, dy = MOVE_KEYS[key]
            x += dx * modifier
            y += dy * modifier
            # Clamp the cursor index to the map size.
            x = max(0, min(x, self.engine.game_map.width - 1))
            y = max(0, min(y, self.engine.game_map.height - 1))
            self.engine.mouse_location = x, y
            return None
        elif key in CONFIRM_KEYS:
            return self.on_index_selected(*self.engine.mouse_location)
        return super().ev_keydown(event)

    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        """Left click confirms a selection."""
        if self.engine.game_map.in_bounds_no_z(*event.tile):
            if event.button == 1:
                return self.on_index_selected(*event.tile)
        return super().ev_mousebuttondown(event)

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        """Called when an index is selected."""
        raise NotImplementedError()


class LookHandler(SelectIndexHandler):
    """Lets the player look around using the keyboard."""

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        x, y = self.engine.mouse_location
        render_names_at_mouse_location(console, x=0, y=RENDER_Y_HEIGHT + 1, engine=self.engine)

    def on_index_selected(self, x: int, y: int) -> MainGameEventHandler:
        return MainGameEventHandler(self.engine)


class SingleRangedAttackHandler(SelectIndexHandler):
    """Handles targeting a single enemy. Only the enemy selected will be affected."""

    def __init__(
        self, engine: Engine, callback: Callable[[Tuple[int, int]], Optional[actions.Action]]
    ):
        super().__init__(engine)

        self.callback = callback

    def on_index_selected(self, x: int, y: int) -> Optional[actions.Action]:
        return self.callback((x, y))


class AreaRangedAttackHandler(SelectIndexHandler):
    """Handles targeting an area within a given radius. Any entity within the area will be affected."""

    def __init__(
        self,
        engine: Engine,
        radius: int,
        callback: Callable[[Tuple[int, int]], Optional[actions.Action]],
    ):
        super().__init__(engine)

        self.radius = radius
        self.callback = callback

    def on_render(self, console: tcod.Console) -> None:
        """Highlight the tile under the cursor."""
        super().on_render(console)

        x, y = self.engine.mouse_location

        # Draw a rectangle around the targeted area, so the player can see the affected tiles.
        console.draw_frame(
            x=x - self.radius - 1,
            y=y - self.radius - 1,
            width=self.radius ** 2,
            height=self.radius ** 2,
            fg=color.red,
            clear=False,
        )

    def on_index_selected(self, x: int, y: int) -> Optional[actions.Action]:
        return self.callback((x, y))


class MainGameEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        action: Optional[actions.Action] = None

        key = event.sym
        modifier = event.mod

        if not self.engine.playable_entities:
            return GameOverEventHandler(self.engine)
            
        player = self.engine.playable_entities[self.engine.p_index]
            
        if key in WAIT_KEYS:
            action = actions.WaitAction(player)
        elif key in CAM_KEYS:
            dx, dy = CAM_KEYS[key]
            new_x = self.engine.cam_x + dx
            new_y = self.engine.cam_y + dy
            if self.engine.game_map.in_bounds_x(new_x) and \
                self.engine.game_map.in_bounds_x(new_x + self.engine.cam_width):
                self.engine.cam_x = new_x
            if self.engine.game_map.in_bounds_x(new_y) and \
                self.engine.game_map.in_bounds_y(new_y + self.engine.cam_height):
                self.engine.cam_y = new_y
        elif key == tcod.event.KeySym.ESCAPE:
            raise SystemExit()
        elif key == tcod.event.KeySym.V:
            return HistoryViewer(self.engine)
        elif key == tcod.event.KeySym.F:
            action = actions.PickupAction(player)
        elif key == tcod.event.KeySym.I:
            return InventoryEventHandler(self.engine)
        elif key == tcod.event.KeySym.T:
            return CharacterScreenEventHandler(self.engine)
        elif key == tcod.event.KeySym.PERIOD:
            if self.engine.cam_z - 1 >= 0:
                self.engine.cam_z -= 1
            return self
        elif key == tcod.event.KeySym.COMMA:
            if self.engine.cam_z + 1 < self.engine.game_map.depth:
                self.engine.cam_z += 1
            return self
        elif key == tcod.event.KeySym.LEFTBRACKET:
            self.engine.p_index = (self.engine.p_index - 1) % len(self.engine.playable_entities)
            player = self.engine.playable_entities[self.engine.p_index]
            self.engine.center_cam_on(player.z, player.x, player.y)
            return self
        elif key == tcod.event.KeySym.RIGHTBRACKET:
            self.engine.p_index = (self.engine.p_index + 1) % len(self.engine.playable_entities)
            player = self.engine.playable_entities[self.engine.p_index]
            self.engine.center_cam_on(player.z, player.x, player.y)
            return self
        elif key == tcod.event.KeySym.SLASH:
            return LookHandler(self.engine)
        elif key == tcod.event.KeySym.BACKSLASH:
            return TimeStepHandler(self.engine, 10)
        elif key == tcod.event.KeySym.B:
            return BuildSelectionEventHandler(self.engine)
        elif key == tcod.event.KeySym.M:
            if not player.busy:
                return SingleRangedAttackHandler(self.engine,
                        callback=lambda xy: ai.MoveAI(
                        entity=player,
                        target_zxy=(self.engine.cam_z, xy[0] + self.engine.cam_x, xy[1] + self.engine.cam_y),
                        previous_ai=player.ai))
        elif key == tcod.event.KeySym.H:
            if player.busy:
                player.ai.halt = True
            return self
        elif key == tcod.event.KeySym.SPACE:
            return self

        # No valid key was pressed
        return action

class GameOverEventHandler(EventHandler):
    def on_quit(self) -> None:
        """Handle exiting out of a finished game."""
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav")  # Deletes the active save file.
        raise exceptions.QuitWithoutSaving()  # Avoid saving a finished game.

    def ev_quit(self, event: tcod.event.Quit) -> None:
        self.on_quit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.on_quit()
