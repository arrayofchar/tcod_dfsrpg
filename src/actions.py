from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING

import tile_types

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

class Action:
    def __init__(self, entity: Entity) -> None:
        super().__init__()
        self.entity = entity

    @property
    def engine(self) -> Engine:
        """Return the engine this action belongs to."""
        return self.entity.gamemap.engine

    def perform(self) -> None:
        raise NotImplementedError()

class EscapeAction(Action):
    def perform(self) -> None:
        raise SystemExit()

class ActionWithDirection(Action):
    def __init__(self, entity: Entity, dx: int, dy: int):
        super().__init__(entity)

        self.dx = dx
        self.dy = dy

    @property
    def dest_xy(self) -> Tuple[int, int]:
        """Returns this actions destination."""
        return self.entity.x + self.dx, self.entity.y + self.dy

    @property
    def blocking_entity(self) -> Optional[Entity]:
        """Return the blocking entity at this actions destination.."""
        return self.engine.game_map.get_blocking_entity_at_location(self.entity.z, *self.dest_xy)

    def perform(self) -> None:
        raise NotImplementedError()

class MeleeAction(ActionWithDirection):
    def perform(self) -> None:
        target = self.blocking_entity
        if not target:
            return  # No entity to attack.

        print(f"You kick the {target.name}, much to its annoyance!")

class MovementAction(ActionWithDirection):

    def perform(self) -> None:
        dest_x, dest_y = self.dest_xy

        if not self.engine.game_map.in_bounds(self.entity.z, dest_x, dest_y):
            return  # Destination is out of bounds.
        if not self.engine.game_map.tiles["walkable"][self.entity.z, dest_x, dest_y]:
            return  # Destination is blocked by a tile.
        if self.engine.game_map.get_blocking_entity_at_location(self.entity.z, dest_x, dest_y):
            return  # Destination is blocked by an entity.

        self.entity.move(self.dx, self.dy)

class TakeStairsAction(Action):
    def perform(self) -> None:
        """
        Take the stairs, if any exist at the entity's location.
        """
        entity_loc_tile_type = self.engine.game_map.tiles[(self.entity.z, self.entity.x, self.entity.y)]
        if entity_loc_tile_type== tile_types.down_stairs:
            if not self.engine.game_map.in_bounds(self.entity.z-1, self.entity.x, self.entity.y):
                return  # Destination is out of bounds.
            self.entity.z -= 1
        elif entity_loc_tile_type== tile_types.up_stairs:
            if not self.engine.game_map.in_bounds(self.entity.z+1, self.entity.x, self.entity.y):
                return  # Destination is out of bounds.
            self.entity.z += 1
        else:
            pass
            # TODO:
            # raise exceptions.Impossible("There are no stairs here.")

class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        if self.blocking_entity:
            return MeleeAction(self.entity, self.dx, self.dy).perform()
        else:
             return MovementAction(self.entity, self.dx, self.dy).perform()
             