from enum import auto, Enum


class RenderOrder(Enum):
    CORPSE = auto()
    PLANT = auto()
    FIXTURE = auto()
    ITEM = auto()
    ACTOR = auto()
    PARTICLE = auto()

