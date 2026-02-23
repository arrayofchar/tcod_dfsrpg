from enum import auto, Enum


class RenderOrder(Enum):
    CORPSE = auto()
    FIXTURE = auto()
    ITEM = auto()
    ACTOR = auto()
    PARTICLE = auto()

