from __future__ import annotations

import copy
import math
import exceptions
from typing import Optional, Tuple, Type, TypeVar, TYPE_CHECKING, Union, Dict
import tile_types
import numpy as np
from enum import auto, Enum, IntEnum

from render_order import RenderOrder
from components.ai import BuildRemoveAI

if TYPE_CHECKING:
    from components.ai import BaseAI
    from components.consumable import Consumable
    from components.equipment import Equipment
    from components.equippable import Equippable
    from components.fighter import Fighter
    from components.inventory import Inventory
    from components.level import Level
    from components.environment_effect import EnvEffect
    from game_map import GameMap

T = TypeVar("T", bound="Entity")

class ParticleType(Enum):
    DUST = auto()
    SMOKE = auto()

BURNING_POINT = 10 # in turns

class Entity:
    """
    A generic object to represent players, enemies, items, etc.
    """
    parent: Union[GameMap, Inventory]

    def __init__(
        self,
        parent: Optional[GameMap] = None,
        z: int = 0,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        blocks_movement: bool = False,
        render_order: RenderOrder = RenderOrder.CORPSE,
    ):
        self.z = z
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.name = name
        self.blocks_movement = blocks_movement
        self.render_order = render_order
        self.busy = False
        if parent:
            # If parent isn't provided now then it will be set later.
            self.parent = parent
            parent.entities.add(self)

    @property
    def gamemap(self) -> GameMap:
        return self.parent.gamemap

    def spawn(self: T, gamemap: GameMap, z: int, x: int, y: int) -> T:
        """Spawn a copy of this instance at the given location."""
        clone = copy.deepcopy(self)
        clone.z, clone.x, clone.y = z, x, y
        clone.parent = gamemap
        gamemap.entities.add(clone)
        return clone

    def place(self, z: int, x: int, y: int, gamemap: Optional[GameMap] = None) -> None:
        """Place this entity at a new location.  Handles moving across GameMaps."""
        self.z = z
        self.x = x
        self.y = y
        if gamemap:
            if hasattr(self, "parent"):  # Possibly uninitialized.
                if self.parent is self.gamemap:
                    self.gamemap.entities.remove(self)
            self.parent = gamemap
            gamemap.entities.add(self)

    def distance(self, x: int, y: int) -> float:
        """
        Return the distance between the current entity and the given (x, y) coordinate.
        """
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def move(self, dx: int, dy: int) -> None:
        # Move the entity by a given amount
        self.x += dx
        self.y += dy

class Actor(Entity):
    def __init__(
        self,
        *,
        z: int = 0,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        ai_cls: Type[BaseAI],
        equipment: Equipment,
        fighter: Fighter,
        inventory: Inventory,
        level: Level,
    ):
        super().__init__(
            z=z,
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=True,
            render_order=RenderOrder.ACTOR,
        )

        self.ai: Optional[BaseAI] = ai_cls(self)

        self.equipment: Equipment = equipment
        self.equipment.parent = self

        self.fighter = fighter
        self.fighter.parent = self

        self.inventory = inventory
        self.inventory.parent = self

        self.level = level
        self.level.parent = self

    @property
    def is_alive(self) -> bool:
        """Returns True as long as this actor can perform actions."""
        return bool(self.ai)

    def set_build_remove_ai(self, tile_item: BuildRemoveTile) -> None:
        self.ai = BuildRemoveAI(entity=self,
                    previous_ai=self.ai,
                    turns_remaining=tile_item.turns_remaining,
                    work_item=tile_item,)


class Item(Entity):
    def __init__(
        self,
        *,
        z: int = 0,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        consumable: Optional[Consumable] = None,
        equippable: Optional[Equippable] = None,
    ):
        super().__init__(
            z=z,
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=False,
            render_order=RenderOrder.ITEM,
        )
        self.consumable = consumable
        if self.consumable:
            self.consumable.parent = self
        self.equippable = equippable
        if self.equippable:
            self.equippable.parent = self


class BuildRemoveTile(Entity):
    def __init__(
        self,
        *,
        z: int = 0,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        build_task: bool = True,
        build_type: IntEnum = 0,
        turns_remaining: int = 0,
    ):
        if build_task:
            color = (100, 255, 255)
            name = "Building tile"
            blocks_movement = True
        else:
            char = "X"
            color = (255, 100, 255)
            name = "Removing tile"
            blocks_movement = False

        if build_type and build_type == tile_types.TileType.FLOOR:
            blocks_movement = False

        super().__init__(
            z=z,
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=blocks_movement,
            render_order=RenderOrder.ITEM,
        )
        self.build_task = build_task
        self.build_type = build_type
        self.turns_remaining = turns_remaining     

    def done(self) -> None:
        if self.build_task:
            self.parent.build_after_check(self.z, self.x, self.y, self.build_type)
        else:
            self.parent.remove_tile(self.z, self.x, self.y)


class Particle(Entity):
    def __init__(
        self,
        *,
        z: int = 0,
        x: int = 0,
        y: int = 0,
        char: str = "░",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        particle_type: ParticleType = ParticleType.DUST,
        spread_decay: float = 0.0, # percent of density lost per turn to spread
        spread_rate: int = 1, # number of turns per spread
        density: int = 0,
        density_decay: int = 0,
        effect: Optional[EnvEffect] = None,
    ):
        super().__init__(
            z=z,
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=False,
            render_order=RenderOrder.PARTICLE,
        )
        self.particle_type = particle_type
        self.spread_decay = spread_decay
        self.spread_rate = spread_rate
        self.spread_value = 0 # current spread value, mod spread_rate
        self.density = density
        self.density_decay = density_decay
        self.effect = effect
        if self.effect:
            self.effect.parent = self

    def spawn(self: T, gamemap: GameMap, z: int, x: int, y: int, density: int=0) -> T:
        clone = super().spawn(gamemap, z, x, y)
        if clone.effect:
            clone.effect.parent = clone
            if hasattr(clone.effect, "base_value"):
                clone.effect.base_value = None # else light value restored to original obj base_value
        if density:
            clone.density = density
        return clone

    def spread(self, p_coord_dict: Dict[Tuple[int, int, int], Particle]) -> None:
        self.density -= self.density_decay
        if self.density <= 0:
            self.effect.deactivate()
            self.gamemap.entities.remove(self)
            return

        if self.spread_rate == 0:
            return
        self.spread_value += 1
        if self.spread_value >= self.spread_rate:
            self.spread_value = 0
        else:
            return

        neighbors = self.gamemap.get_neighbor_tiles(self.z, self.x, self.y)
        available_tiles = []
        for n in neighbors:
            if self.gamemap.tiles["tile_type"][*n] != tile_types.TileType.WALL and self.gamemap.tiles["tile_type"][*n] != tile_types.TileType.DOOR:
                available_tiles.append(n)
        # special treatment for z - 1 and z + 1
        if self.gamemap.in_bounds_z(self.z - 1) and \
            (self.gamemap.tiles["tile_type"][self.z - 1, self.x, self.y] != tile_types.TileType.WALL and self.gamemap.tiles["tile_type"][self.z - 1, self.x, self.y] != tile_types.TileType.DOOR) and \
            (self.gamemap.tiles["tile_type"][self.z, self.x, self.y] == tile_types.TileType.EMPTY or self.gamemap.tiles["tile_type"][self.z, self.x, self.y] == tile_types.TileType.DOWN_STAIRS):
            available_tiles.append((self.z - 1, self.x, self.y))
        elif self.gamemap.in_bounds_z(self.z + 1) and (self.gamemap.tiles["tile_type"][self.z, self.x, self.y] != tile_types.TileType.WALL and self.gamemap.tiles["tile_type"][self.z, self.x, self.y] != tile_types.TileType.DOOR) and \
            (self.gamemap.tiles["tile_type"][self.z + 1, self.x, self.y] == tile_types.TileType.EMPTY or self.gamemap.tiles["tile_type"][self.z + 1, self.x, self.y] == tile_types.TileType.DOWN_STAIRS):
            available_tiles.append((self.z + 1, self.x, self.y))

        spread_density_total = int(self.density * self.spread_decay)
        self.density = int(self.density * (1 - self.spread_decay))
        per_spread_density = int(spread_density_total / len(available_tiles))
        
        if per_spread_density > 0:
            for t in available_tiles:
                if t in p_coord_dict:
                    p_at_t_list = p_coord_dict[*t]
                    found = False
                    for p_at_t in p_at_t_list:
                        if p_at_t.particle_type == self.particle_type:
                            found = True
                            if (p_at_t.density + per_spread_density) < self.density:
                                p_at_t.density += per_spread_density
                            break
                    if not found:
                        clone = self.spawn(self.gamemap, *t, per_spread_density)
                        p_at_t_list.append(clone)
                else:
                    clone = self.spawn(self.gamemap, *t, per_spread_density)
                    p_coord_dict[*t] = [clone]


class Fire(Entity):
    def __init__(
        self,
        *,
        z: int = 0,
        x: int = 0,
        y: int = 0,
        duration: int = 15,
        turn_count: int = 0,
    ):
        super().__init__(
            z=z,
            x=x,
            y=y,
            char="▲",
            color=(255, 0, 0),
            name="Fire",
            blocks_movement=False,
            render_order=RenderOrder.PARTICLE,
        )
        self.duration = duration
        self.turn_count = turn_count

    def handle_turn(self) -> None:
        z, x, y = self.z, self.x, self.y
        if self.turn_count >= BURNING_POINT:
            self.gamemap.on_fire[z, x, y] = True
            if (z, x, y) in self.gamemap.fire_orig_light:
                raise exceptions.Impossible("TODO: gamemap.fire_orig_light dict entries should be removed")
            else:
                self.gamemap.fire_orig_light[z, x, y] = self.gamemap.get_light_tile(z, x, y)
        self.turn_count += 1


class Fixture(Entity):
    def __init__(
        self,
        *,
        z: int = 0,
        x: int = 0,
        y: int = 0,
        char: str = "+",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed> fixture",
        blocks_movement: bool = False,
        effect: Optional[EnvEffect] = None,
    ):
        super().__init__(
            z=z,
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=blocks_movement,
            render_order=RenderOrder.FIXTURE,
        )
        self.effect = effect
        if self.effect:
            self.effect.parent = self

    def spawn(self: T, gamemap: GameMap, z: int, x: int, y: int) -> T:
        clone = super().spawn(gamemap, z, x, y)
        if clone.effect:
            clone.effect.parent = clone
        return clone
    