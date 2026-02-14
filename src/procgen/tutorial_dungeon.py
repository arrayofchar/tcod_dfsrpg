from __future__ import annotations

import random
from typing import Dict, Iterator, List, Tuple, TYPE_CHECKING

import tcod
import entity_factories
from game_map import GameMap
import tile_types

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

max_items_by_floor = [
    (2, 2),
    (4, 1),
]

max_monsters_by_floor = [
    (2, 5),
    (4, 3),
    (6, 2),
]


item_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(entity_factories.health_potion, 35)],
    2: [(entity_factories.confusion_scroll, 10)],
    4: [(entity_factories.lightning_scroll, 25), (entity_factories.sword, 5)],
    6: [(entity_factories.fireball_scroll, 25), (entity_factories.chain_mail, 15)],
}

enemy_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(entity_factories.orc, 80)],
    3: [(entity_factories.troll, 15)],
    5: [(entity_factories.troll, 30)],
    7: [(entity_factories.troll, 60)],
}

def get_max_value_for_floor(
    max_value_by_floor: List[Tuple[int, int]], floor: int
) -> int:
    current_value = 0

    for floor_minimum, value in max_value_by_floor:
        if floor_minimum > floor:
            break
        else:
            current_value = value

    return current_value

def get_entities_at_random(
    weighted_chances_by_floor: Dict[int, List[Tuple[Entity, int]]],
    number_of_entities: int,
    z: int,
) -> List[Entity]:
    entity_weighted_chances = {}

    for key, values in weighted_chances_by_floor.items():
        if key > z:
            break
        else:
            for value in values:
                entity = value[0]
                weighted_chance = value[1]

                entity_weighted_chances[entity] = weighted_chance

    entities = list(entity_weighted_chances.keys())
    entity_weighted_chance_values = list(entity_weighted_chances.values())

    chosen_entities = random.choices(
        entities, weights=entity_weighted_chance_values, k=number_of_entities
    )

    return chosen_entities


class RectangularRoom:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    @property
    def center(self) -> Tuple[int, int]:
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)

        return center_x, center_y

    @property
    def inner(self) -> Tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    def intersects(self, other: RectangularRoom) -> bool:
        """Return True if this room overlaps with another RectangularRoom."""
        return (
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )
    
def place_entities(room: RectangularRoom, dungeon: GameMap, z: int,) -> None:
    number_of_monsters = random.randint(
        0, get_max_value_for_floor(max_monsters_by_floor, z)
    )
    number_of_items = random.randint(
        0, get_max_value_for_floor(max_items_by_floor, z)
    )

    monsters: List[Entity] = get_entities_at_random(
        enemy_chances, number_of_monsters, z
    )
    items: List[Entity] = get_entities_at_random(
        item_chances, number_of_items, z
    )

    for entity in monsters + items:
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)

        if not any(entity.x == x and entity.y == y for entity in dungeon.entities):
            entity.spawn(dungeon, z, x, y)
                
def tunnel_between(
    start: Tuple[int, int], end: Tuple[int, int]
) -> Iterator[Tuple[int, int]]:
    """Return an L-shaped tunnel between these two points."""
    x1, y1 = start
    x2, y2 = end
    if random.random() < 0.5:  # 50% chance.
        # Move horizontally, then vertically.
        corner_x, corner_y = x2, y1
    else:
        # Move vertically, then horizontally.
        corner_x, corner_y = x1, y2

    # Generate the coordinates for this tunnel.
    for x, y in tcod.los.bresenham((x1, y1), (corner_x, corner_y)).tolist():
        yield x, y
    for x, y in tcod.los.bresenham((corner_x, corner_y), (x2, y2)).tolist():
        yield x, y

def generate_dungeon(
    max_rooms: int,
    room_min_size: int,
    room_max_size: int,
    map_depth: int,
    map_width: int,
    map_height: int,
    engine: Engine,
) -> GameMap:
    """Generate a new dungeon map."""
    p_entities = engine.playable_entities
    plist_index = 0

    dungeon = GameMap(engine, map_depth, map_width, map_height, entities=[*p_entities])

    last_stairs_room = None

    for d in range(map_depth - 1, 0, -1):
        rooms: List[RectangularRoom] = []

        if last_stairs_room:
            dungeon.tiles[d][last_stairs_room.inner] = tile_types.floor
            dungeon.tiles[d][last_stairs_room.center[0]+1, last_stairs_room.center[1]+1] = tile_types.up_stairs
                
            rooms.append(last_stairs_room)

        for r in range(max_rooms):
            room_width = random.randint(room_min_size, room_max_size)
            room_height = random.randint(room_min_size, room_max_size)

            x = random.randint(0, dungeon.width - room_width - 1)
            y = random.randint(0, dungeon.height - room_height - 1)

            # "RectangularRoom" class makes rectangles easier to work with
            new_room = RectangularRoom(x, y, room_width, room_height)

            # Run through the other rooms and see if they intersect with this one.
            if any(new_room.intersects(other_room) for other_room in rooms):
                continue  # This room intersects, so go to the next attempt.
            # If there are no intersections then the room is valid.

            # Dig out this rooms inner area.
            dungeon.tiles[d][new_room.inner] = tile_types.floor
            for i in range(5):
                empty_x = random.randint(x, x + room_width)
                empty_y = random.randint(y, y + room_height)
                dungeon.tiles[d, empty_x, empty_y] = tile_types.empty

            if len(rooms) > 0:
                if len(rooms) == 2:
                    if plist_index < len(p_entities):
                        p_entities[plist_index].place(d, *new_room.center, dungeon)
                        plist_index += 1
                # elif len(rooms) == 1:
                    dungeon.tiles[d][new_room.center[0]+1, new_room.center[1]+1] = tile_types.down_stairs
                    last_stairs_room = new_room
                # Dig out a tunnel between this room and the previous one.
                for x, y in tunnel_between(rooms[-1].center, new_room.center):
                    dungeon.tiles[d][x, y] = tile_types.floor

            place_entities(new_room, dungeon, d)

            # Finally, append the new room to the list.
            rooms.append(new_room)

    if last_stairs_room:
            dungeon.tiles[0][last_stairs_room.inner] = tile_types.floor
            dungeon.tiles[0][last_stairs_room.center[0]+1, last_stairs_room.center[1]+1] = tile_types.up_stairs

    return dungeon