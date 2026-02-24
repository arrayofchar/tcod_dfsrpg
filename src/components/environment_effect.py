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
        self.orig_value = None

    def activate(self) -> None:
        if self.orig_value is None:
            self.orig_value = self.gamemap.get_light_tile(self.parent.z, self.parent.x, self.parent.y)
        lower_amt = self.orig_value - int(self.parent.density / self.per_density_amt)
        if lower_amt < 0:
            lower_amt = 0
            self.gamemap.tiles["transparent"][self.parent.z, self.parent.x, self.parent.y] = False
        else:
            self.gamemap.tiles["transparent"][self.parent.z, self.parent.x, self.parent.y] = True
        self.gamemap.set_light_tile(self.parent.z, self.parent.x, self.parent.y, lower_amt)

    def deactivate(self) -> None:
        self.gamemap.set_light_tile(self.parent.z, self.parent.x, self.parent.y, self.orig_value)
        if self.gamemap.tiles[self.parent.z, self.parent.x, self.parent.y] != tile_types.wall:
            self.gamemap.tiles["transparent"][self.parent.z, self.parent.x, self.parent.y] = True


class IncreaseVisibility(EnvEffect):
    """ 
    !!! Can only be activated one per tile !!!
    TODO: possible bug
    Don't remove light source when LowerVisibilty entity is present.
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
                    if (z, x, y) in self.gamemap.light_fov1:
                        self.gamemap.light_fov1[z, x, y] += 2
                    else:
                        self.gamemap.light_fov1[z, x, y] = self.gamemap.get_light_tile(z, x, y) + 2
                    self.l1.append((z, x, y))
                    set_value = self.gamemap.light_fov1[z, x, y]
                    if set_value > 3:
                        set_value = 3
                    self.gamemap.set_light_tile(z, x, y, set_value)
                elif f2[x, y]: # !!! Needs elif for logic to work because f2 is not comput ^ f1
                    if (z, x, y) in self.gamemap.light_fov2:
                        self.gamemap.light_fov2[z, x, y] += 1
                    else:
                        self.gamemap.light_fov2[z, x, y] = self.gamemap.get_light_tile(z, x, y) + 1
                    self.l2.append((z, x, y))
                    set_value = self.gamemap.light_fov2[z, x, y]
                    if set_value > 3:
                        set_value = 3
                    self.gamemap.set_light_tile(z, x, y, set_value)

    def deactivate(self) -> None:
        for tile in self.l1:
            self.gamemap.light_fov1[*tile] -= 2
            self.gamemap.set_light_tile(*tile, \
                min(self.gamemap.get_light_tile(*tile), self.gamemap.light_fov1[*tile]))
        for tile in self.l2:
            self.gamemap.light_fov2[*tile] -= 1
            self.gamemap.set_light_tile(*tile, \
                min(self.gamemap.get_light_tile(*tile), self.gamemap.light_fov2[*tile]))
