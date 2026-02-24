from __future__ import annotations

from typing import TYPE_CHECKING
from tcod.map import compute_fov

from components.base_component import BaseComponent
import tile_types

if TYPE_CHECKING:
    from entity import Particle


class EnvEffect(BaseComponent):
    parent: Particle

    def activate(self) -> None:
        raise NotImplementedError()

    def deactivate(self) -> None:
        raise NotImplementedError()


class LowerVisibility(EnvEffect):
    """ !!! Can only be activated one per tile !!! """

    def __init__(self, per_density_amt: int):
        self.per_density_amt = per_density_amt
        self.base_value = None

    def activate(self) -> None:
        z, x, y = self.parent.z, self.parent.x, self.parent.y
        if (z, x, y) in self.gamemap.light_fov:
            self.base_value = self.gamemap.light_fov[z, x, y]
        elif self.base_value is None:
            self.base_value = self.gamemap.get_light_tile(z, x, y)

        base_value = self.base_value
        if self.gamemap.outside[x, y] > z:
            if base_value > 3:
                base_value = 3
        else:
            if base_value > 4:
                base_value = 4
        lower_amt = base_value - int(self.parent.density / self.per_density_amt)
        if lower_amt < 0:
            lower_amt = 0
            self.gamemap.tiles["transparent"][z, x, y] = False
        else:
            self.gamemap.tiles["transparent"][z, x, y] = True
        self.gamemap.set_light_tile(z, x, y, lower_amt)

    def deactivate(self) -> None:
        z, x, y = self.parent.z, self.parent.x, self.parent.y
        if (z, x, y) in self.gamemap.light_fov:
            set_value = self.gamemap.light_fov[z, x, y]
        else:
            set_value = self.base_value
        if self.gamemap.outside[x, y] > z:
            if set_value > 3:
                set_value = 3
        else:
            if set_value > 4:
                set_value = 4
        self.gamemap.set_light_tile(z, x, y, set_value)
        tile_type = self.gamemap.tiles[z, x, y]
        if tile_type != tile_types.wall or tile_type != tile_types.door:
            self.gamemap.tiles["transparent"][z, x, y] = True


class IncreaseVisibility(EnvEffect):
    """ 
    !!! Can only be activated one per tile !!!
    TODO: possible bug
    Don't build light source when LowerVisibilty entity is present.
    Else light tile value will be restored incorrectly
    """
    
    def __init__(self):
        self.l1 = []
        self.l2 = []

    def activate(self) -> None:
        """ !!! Called only once !!! """

        z = self.parent.z
        f1 = compute_fov(self.gamemap.tiles["transparent"][z],
                    (self.parent.x, self.parent.y),
                    radius=2,)
        f2 = compute_fov(self.gamemap.tiles["transparent"][z],
                    (self.parent.x, self.parent.y),
                    radius=4,)
        
        for x in range(self.gamemap.width):
            for y in range(self.gamemap.height):
                if f1[x, y]:
                    if (z, x, y) in self.gamemap.light_fov:
                        self.gamemap.light_fov[z, x, y] += 2
                    else:
                        self.gamemap.light_fov[z, x, y] = self.gamemap.get_light_tile(z, x, y) + 2
                    self.l1.append((z, x, y))
                    set_value = self.gamemap.light_fov[z, x, y]
                    if set_value > 3:
                        set_value = 3
                    self.gamemap.set_light_tile(z, x, y, set_value)
                elif f2[x, y]: # !!! Needs elif for logic to work because f2 is not comput ^ f1
                    if (z, x, y) in self.gamemap.light_fov:
                        self.gamemap.light_fov[z, x, y] += 1
                    else:
                        self.gamemap.light_fov[z, x, y] = self.gamemap.get_light_tile(z, x, y) + 1
                    self.l2.append((z, x, y))
                    set_value = self.gamemap.light_fov[z, x, y]
                    if set_value > 3:
                        set_value = 3
                    self.gamemap.set_light_tile(z, x, y, set_value)

    def deactivate(self) -> None:
        for tile in self.l1:
            self.gamemap.light_fov[*tile] -= 2
            self.gamemap.set_light_tile(*tile, \
                min(self.gamemap.get_light_tile(*tile), self.gamemap.light_fov[*tile]))
        for tile in self.l2:
            self.gamemap.light_fov[*tile] -= 1
            self.gamemap.set_light_tile(*tile, \
                min(self.gamemap.get_light_tile(*tile), self.gamemap.light_fov[*tile]))
