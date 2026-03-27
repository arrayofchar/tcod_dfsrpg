from components.ai import HostileEnemy, CritterAI, PredatorAI
from components import consumable, equippable, environment_effect
from components.equipment import Equipment
from components.fighter import Fighter
from components.inventory import Inventory
from components.level import Level
from entity import ParticleType, \
    Actor, Item, BuildRemoveTile, Particle, Fire, Aquifer, Fixture, Plant, Animal
import tile_types

player = Actor(
    char="☺",
    color=(255, 255, 255),
    name="Player",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=200, breath=50, base_defense=5, base_power=5),
    inventory=Inventory(capacity=26),
    level=Level(level_up_base=200),
)
orc = Actor(
    char="o",
    color=(63, 127, 63),
    name="Orc",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=30, breath=50, base_defense=3, base_power=7),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=35),
)
troll = Actor(
    char="Ö",
    color=(0, 127, 0),
    name="Troll",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=60, breath=50, base_defense=8, base_power=10),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=100),
)
critter = Animal(
    char="°",
    color=(100, 127, 0),
    name="Critter",
    ai_cls=CritterAI,
    equipment=Equipment(),
    fighter=Fighter(hp=20, breath=500, base_defense=1, base_power=1),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=5),
)
predator = Animal(
    char="ô",
    color=(120, 80, 0),
    name="Predator",
    ai_cls=PredatorAI,
    equipment=Equipment(),
    fighter=Fighter(hp=60, breath=500, base_defense=2, base_power=1),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=100),
)

dust = Particle(
    name="Dust",
    char="░",
    color=(200, 150, 100),
    particle_type=ParticleType.DUST,
    spread_rate=0,
    density=10,
    density_decay=5,
)
smoke = Particle(
    name="Smoke",
    char="░",
    color=(150, 150, 200),
    particle_type=ParticleType.SMOKE,
    spread_decay=0.4,
    spread_rate=2,
    density=100,
    density_decay=20,
    effect=environment_effect.LowerVisibility(per_density_amt=30),
)
fire = Fire(
    duration=15,
)
aquifer = Aquifer(
    duration=100,
)

light_src = Fixture(
    name="Light Source",
    char="*",
    blocks_movement=False,
    effect=environment_effect.IncreaseVisibility(),
)

tall_grass = Plant(
    name="Tall Grass",
    char="=",
    effect=environment_effect.PlantVisReduce(2),
)

shrub = Plant(
    name="Shrub",
    char="≡",
    effect=environment_effect.PlantVisReduce(1),
)

confusion_scroll = Item(
    char="~",
    color=(207, 63, 255),
    name="Confusion Scroll",
    consumable=consumable.ConfusionConsumable(number_of_turns=10),
)
fireball_scroll = Item(
    char="~",
    color=(255, 0, 0),
    name="Fireball Scroll",
    consumable=consumable.FireballDamageConsumable(damage=12, radius=3),
)
health_potion = Item(
    char="!",
    color=(127, 0, 255),
    name="Health Potion",
    consumable=consumable.HealingConsumable(amount=4),
)
lightning_scroll = Item(
    char="~",
    color=(255, 255, 0),
    name="Lightning Scroll",
    consumable=consumable.LightningDamageConsumable(damage=20, maximum_range=5),
)

dagger = Item(
    char="/", color=(0, 191, 255), name="Dagger", equippable=equippable.Dagger()
)
sword = Item(char="/", color=(0, 191, 255), name="Sword", equippable=equippable.Sword())

leather_armor = Item(
    char="[",
    color=(139, 69, 19),
    name="Leather Armor",
    equippable=equippable.LeatherArmor(),
)
chain_mail = Item(
    char="[", color=(139, 69, 19), name="Chain Mail", equippable=equippable.ChainMail()
)