from __future__ import annotations

from typing import TYPE_CHECKING

from components.base_component import BaseComponent

if TYPE_CHECKING:
    from entity import Particle


class ParticleEffect(BaseComponent):
    parent: Particle

    def activate(self) -> None:
        raise NotImplementedError()

    def deactivate(self) -> None:
        raise NotImplementedError()


class LowerVisibility(ParticleEffect):
    def __init__(self, per_density_amt: int):
        super().__init__()
        self.per_density_amt = per_density_amt
        self.orig_light_value = self.gamemap.get_light_tile(self.parent.z, self.parent.x, self.parent.y) if self.parent else None

    def activate(self) -> None:
        lower_amt = self.orig_light_value - int(self.parent.density / self.per_density_amt)
        if lower_amt < 0:
            lower_amt = 0
        self.gamemap.set_light_tile(self.parent.z, self.parent.x, self.parent.y, lower_amt)

    def deactivate(self) -> None:
        self.gamemap.set_light_tile(self.parent.z, self.parent.x, self.parent.y, self.orig_light_value)
