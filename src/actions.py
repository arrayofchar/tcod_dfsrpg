from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING
from tcod.map import compute_fov

import color
import exceptions

import consts
import tile_types

if TYPE_CHECKING:
    from engine import Engine
    from entity import Actor, Entity, Item, BuildRemoveTile

class Action:
    def __init__(self, entity: Actor) -> None:
        super().__init__()
        self.entity = entity

    @property
    def engine(self) -> Engine:
        """Return the engine this action belongs to."""
        return self.entity.gamemap.engine

    def perform(self) -> None:
        raise NotImplementedError()

class PickupAction(Action):
    """Pickup an item and add it to the inventory, if there is room for it."""

    def __init__(self, entity: Actor):
        super().__init__(entity)

    def perform(self) -> None:
        actor_location_x = self.entity.x
        actor_location_y = self.entity.y
        inventory = self.entity.inventory

        for item in list(self.engine.game_map.items):
            if actor_location_x == item.x and actor_location_y == item.y:
                if len(inventory.items) >= inventory.capacity:
                    raise exceptions.Impossible("Your inventory is full.")

                self.engine.game_map.entities.remove(item)
                self.engine.game_map.items.remove(item)
                item.parent = self.entity.inventory
                inventory.items.append(item)

                self.engine.message_log.add_message(f"You picked up the {item.name}!")
                return

        raise exceptions.Impossible("There is nothing here to pick up.")

class BuildAction(Action):
    def __init__(
        self, entity: Actor, tile_item: BuildRemoveTile, target_xy: Optional[Tuple[int, int]] = None,
    ):
        super().__init__(entity)
        self.tile_item = tile_item
        if not target_xy:
            target_xy = entity.x, entity.y
        self.target_xy = target_xy

    def perform(self) -> None:
        work_item = None
        for e in self.engine.game_map.work_items:
            if e.z == self.entity.z and (e.x, e.y) == self.target_xy:
                work_item = e
        for e in self.engine.game_map.work_blocking_entities:
            if e.z == self.entity.z and (e.x, e.y) == self.target_xy:
                raise exceptions.Impossible("Can't build here, blocking entity in the way")
                return
        if self.engine.cam_z != self.entity.z:
            raise exceptions.Impossible("Cannot build on different z level")
        elif work_item:
            if work_item.build_task:
                n_tiles = self.engine.game_map.get_neighbor_tiles(self.entity.z, self.entity.x, self.entity.y)
                if (self.entity.z, *self.target_xy) in n_tiles:
                    self.entity.set_build_remove_ai(work_item)
            else:
                raise exceptions.Impossible("Cannot build on existing remove tile work item")
        elif self.engine.game_map.build_tile_check(self.entity.z, *self.target_xy, self.tile_item.build_type):
            if self.tile_item.build_type == tile_types.TileType.UP_STAIRS and \
                not self.engine.game_map.build_tile_check(self.entity.z + 1, *self.target_xy, tile_types.TileType.DOWN_STAIRS):
                raise exceptions.Impossible("z + 1 check for downstairs of upstairs build failed")
                return
            elif self.tile_item.build_type == tile_types.TileType.DOWN_STAIRS and \
                not self.engine.game_map.build_tile_check(self.entity.z - 1, *self.target_xy, tile_types.TileType.UP_STAIRS):
                raise exceptions.Impossible("z - 1 check for upstairs of downstairs build failed")
                return
            n_tiles = self.engine.game_map.get_neighbor_tiles(self.entity.z, self.entity.x, self.entity.y)
            if (self.entity.z, *self.target_xy) in n_tiles:
                spawned = self.tile_item.spawn(self.engine.game_map, self.entity.z, *self.target_xy)
                self.entity.set_build_remove_ai(spawned)
            else:
                raise exceptions.Impossible("Can only build on neighboring tiles")

class RemoveDigAction(Action):
    def __init__(
        self, entity: Actor, tile_item: BuildRemoveTile, target_xy: Optional[Tuple[int, int]] = None, remove: bool = True,
    ):
        super().__init__(entity)
        self.tile_item = tile_item
        if not target_xy:
            target_xy = entity.x, entity.y
        self.target_xy = target_xy
        self.remove = remove

    def perform(self) -> None:
        z_diff = 0 if self.remove else 1 # remove or dig
        work_item = None
        for e in self.engine.game_map.work_items:
            if e.z == self.entity.z - z_diff and (e.x, e.y) == self.target_xy:
                work_item = e
        for e in self.engine.game_map.work_blocking_entities:
            if e.z == self.entity.z - z_diff and (e.x, e.y) == self.target_xy:
                raise exceptions.Impossible("Can't remove tile, blocking entity in the way")
                return
        if self.engine.cam_z != self.entity.z:
            raise exceptions.Impossible("Cannot remove tile on different z level")
        elif work_item:
            if work_item.build_task:
                raise exceptions.Impossible("Cannot remove tile on existing build tile work item")
            else:
                n_tiles = self.engine.game_map.get_neighbor_tiles(self.entity.z - z_diff, self.entity.x, self.entity.y)
                if (self.entity.z - z_diff, *self.target_xy) in n_tiles:
                    self.entity.set_build_remove_ai(work_item)
        elif self.engine.game_map.remove_tile_check(self.entity.z - z_diff, *self.target_xy):
            n_tiles = self.engine.game_map.get_neighbor_tiles(self.entity.z - z_diff, self.entity.x, self.entity.y)
            if (self.entity.z - z_diff, *self.target_xy) in n_tiles:
                spawned = self.tile_item.spawn(self.engine.game_map, self.entity.z - z_diff, *self.target_xy)
                self.entity.set_build_remove_ai(spawned)
            else:
                raise exceptions.Impossible("Can only remove neighboring tiles")

class ItemAction(Action):
    def __init__(
        self, entity: Actor, item: Item, target_xy: Optional[Tuple[int, int]] = None
    ):
        super().__init__(entity)
        self.item = item
        if not target_xy:
            target_xy = entity.x, entity.y
        self.target_xy = target_xy

    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this actions destination."""
        return self.engine.game_map.get_actor_at_location(self.entity.z, *self.target_xy)

    def perform(self) -> None:
        """Invoke the items ability, this action will be given to provide context."""
        if self.item.consumable:
            self.item.consumable.activate(self)

class DropItem(ItemAction):
    def perform(self) -> None:
        if self.entity.equipment.item_is_equipped(self.item):
            self.entity.equipment.toggle_equip(self.item)
        self.entity.inventory.drop(self.item)

class EquipAction(Action):
    def __init__(self, entity: Actor, item: Item):
        super().__init__(entity)

        self.item = item

    def perform(self) -> None:
        self.entity.equipment.toggle_equip(self.item)

class WaitAction(Action):
    def perform(self) -> None:
        pass

class ActionWithDirection(Action):
    def __init__(self, entity: Actor, dx: int, dy: int):
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

    @property
    def target_actor(self) -> Optional[Actor]:
        """Return the actor at this actions destination."""
        return self.engine.game_map.get_actor_at_location(self.entity.z, *self.dest_xy)

    def perform(self) -> None:
        raise NotImplementedError()

class MeleeAction(ActionWithDirection):
    def perform(self) -> None:
        target = self.target_actor
        if not target:
            raise exceptions.Impossible("Nothing to attack.")

        damage = self.entity.fighter.power - target.fighter.defense

        attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
        if self.entity in self.engine.playable_entities:
            attack_color = color.player_atk
        else:
            attack_color = color.enemy_atk

        if damage > 0:
            self.engine.message_log.add_message(
                f"{attack_desc} for {damage} hit points.", attack_color
            )
            target.fighter.hp -= damage
        else:
            self.engine.message_log.add_message(
                f"{attack_desc} but does no damage.", attack_color
            )

class MovementAction(ActionWithDirection):
    def perform(self) -> None:
        dest_x, dest_y = self.dest_xy
        gm = self.engine.game_map

        if not gm.in_bounds(self.entity.z, dest_x, dest_y):
            raise exceptions.Impossible("That way is blocked, not in bounds")
        if not gm.tiles["walkable"][self.entity.z, dest_x, dest_y]:
            if gm.tiles["tile_type"][self.entity.z, dest_x, dest_y] == tile_types.TileType.EMPTY:
                if gm.get_water_tile(self.entity.z, dest_x, dest_y) >= consts.SWIMMABLE_THRESHOLD or \
                        (gm.in_bounds_z(self.entity.z - 1) and gm.get_water_tile(self.entity.z - 1, dest_x, dest_y) >= consts.DROWNING_LEVEL_THRESHOLD):
                    self.entity.move(self.dx, self.dy)
                    return
                else:
                    raise exceptions.Impossible("That way is blocked, z - 1 not enough water")
            else:
                raise exceptions.Impossible("That way is blocked, nonwalkable not empty")
        if gm.get_blocking_entity_at_location(self.entity.z, dest_x, dest_y):
            raise exceptions.Impossible("That way is blocked, blocked by entity")

        self.entity.move(self.dx, self.dy)

class DownZAction(Action):
    def perform(self) -> None:
        z, x, y = self.entity.z, self.entity.x, self.entity.y
        entity_loc_tile_type = self.engine.game_map.tiles["tile_type"][z, x, y]
        if self.engine.game_map.in_bounds_z(z - 1):
            if entity_loc_tile_type == tile_types.TileType.DOWN_STAIRS or \
                    (self.engine.game_map.get_water_tile(z - 1, x, y) >= consts.DROWNING_LEVEL_THRESHOLD and \
                    self.engine.game_map.get_water_tile(z, x, y) > 0):
                self.engine.game_map.visible[z][:] &= False
                self.entity.z -= 1
            else:
                raise exceptions.Impossible("There are no down stairs here.")
        else:
            return  # Destination is out of bounds.

class UpZAction(Action):
    def perform(self) -> None:
        z, x, y = self.entity.z, self.entity.x, self.entity.y
        entity_loc_tile_type = self.engine.game_map.tiles["tile_type"][z, x, y]
        if self.engine.game_map.in_bounds_z(z + 1):
            if entity_loc_tile_type == tile_types.TileType.UP_STAIRS or \
                    (self.engine.game_map.get_water_tile(z, x, y) >= consts.DROWNING_LEVEL_THRESHOLD and \
                    self.engine.game_map.get_water_tile(z + 1, x, y) > 0):
                self.engine.game_map.visible[z][:] &= False
                self.entity.z += 1
            else:
                raise exceptions.Impossible("There are no up stairs here.")
        else:
            return  # Destination is out of bounds.

class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        if self.target_actor:
            return MeleeAction(self.entity, self.dx, self.dy).perform()
        else:
             return MovementAction(self.entity, self.dx, self.dy).perform()
             