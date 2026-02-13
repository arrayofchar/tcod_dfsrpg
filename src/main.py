#!/usr/bin/env python3
import traceback

import tcod

import color
import exceptions
import input_handler

import setup_game


def save_game(handler: input_handler.BaseEventHandler, filename: str) -> None:
    """If the current event handler has an active Engine then save it."""
    if isinstance(handler, input_handler.EventHandler):
        handler.engine.save_as(filename)
        print("Game saved.")

def main() -> None:
    screen_width = 80
    screen_height = 50

    tileset = tcod.tileset.load_tilesheet(
        "data/dejavu10x10_gs_tc.png", 32, 8, tcod.tileset.CHARMAP_TCOD
    )

    handler: input_handler.BaseEventHandler = setup_game.MainMenu()

    with tcod.context.new_terminal(
        screen_width,
        screen_height,
        tileset=tileset,
        title="dusk fanatics srpg in python-tcod",
        vsync=True,
    ) as context:
        root_console = tcod.console.Console(screen_width, screen_height, order="F")
        try:
            while True:
                root_console.clear()
                handler.on_render(console=root_console)
                context.present(root_console)

                try:
                    for event in tcod.event.wait():
                        context.convert_event(event)
                        handler = handler.handle_events(event)
                    ########################################
                    # for event in tcod.event.get():
                    #     context.convert_event(event)
                    #     handler = handler.handle_events(event)
                    # idle_event = tcod.event.KeyDown
                    # idle_event.sym = tcod.event.K_SPACE
                    # idle_event.type = "KEYDOWN"
                    # idle_event.mod = tcod.event.Modifier.NONE
                    # context.convert_event(idle_event)
                    # handler = handler.handle_events(idle_event)
                    # time.sleep(1)
                    ########################################
                except Exception:  # Handle exceptions in game.
                    traceback.print_exc()  # Print error to stderr.
                    # Then print the error to the message log.
                    if isinstance(handler, input_handler.EventHandler):
                        handler.engine.message_log.add_message(
                            traceback.format_exc(), color.error
                        )
        except exceptions.QuitWithoutSaving:
            raise
        except SystemExit:  # Save and quit.
            save_game(handler, "savegame.sav")
            raise
        except BaseException:  # Save on any other unexpected exception.
            save_game(handler, "savegame.sav")
            raise

if __name__ == "__main__":
    main()
