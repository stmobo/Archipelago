TRAINEE = 0x3D
TRAINEE_2 = 0x7E
SUPER_TRAINEE = 0x38

PUPIL = 0x3E
PUPIL_2 = 0x7F
SUPER_PUPIL = 0x39

RECRUIT = 0x47
RECRUIT_2 = 0x37
SUPER_RECRUIT = 0x3A

EPHRAIM_LORD = 0x01
EIRIKA_LORD = 0x02

EPHRAIM_MASTER_LORD = 0x03
EIRIKA_MASTER_LORD = 0x04

FIGHTER = 0x3F
PIRATE = 0x42
ROGUE = 0x33
WARRIOR = 0x40
BERSERKER = 0x43
MONK = 0x44
PRIEST = 0x45
PEGASUS_KNIGHT = 0x48
CLERIC = 0x4A
TROUBADOUR = 0x4B
VALKYRIE = 0x4C
DANCER = 0x4D

CAVALIER = 0x05
CAVALIER_F = 0x06

KNIGHT = 0x09
KNIGHT_F = 0x0A

MYRMIDON = 0x13
MYRMIDON_F = 0x14

ARCHER = 0x19
ARCHER_F = 0x1A

MAGE = 0x25
MAGE_F = 0x26

MERCENARY = 0x0F
MERCENARY_F = 0x10

WYVERN_RIDER = 0x1F
WYVERN_RIDER_F = 0x20

SHAMAN = 0x2D
SHAMAN_F = 0x2E

SUMMONER = 0x31
SUMMONER_F = 0x32

PALADIN = 0x07
PALADIN_F = 0x08

GENERAL = 0x0B
GENERAL_F = 0x0C

SWORDMASTER = 0x15
SWORDMASTER_F = 0x16

ASSASSIN = 0x17
ASSASSIN_F = 0x18

SNIPER = 0x1B
SNIPER_F = 0x1C

HERO = 0x11
HERO_F = 0x12

WYVERN_LORD = 0x21
WYVERN_LORD_F = 0x22

RANGER = 0x1D
RANGER_F = 0x1E

WYVERN_KNIGHT = 0x23
WYVERN_KNIGHT_F = 0x24

SAGE = 0x27
SAGE_F = 0x28

MAGE_KNIGHT = 0x29
MAGE_KNIGHT_F = 0x2A

BISHOP = 0x2B
BISHOP_F = 0x2C

DRUID = 0x2F
DRUID_F = 0x30

GREAT_KNIGHT = 0x35
GREAT_KNIGHT_F = 0x36

THIEF = 0x0D
BARD = 0x46

MANAKETE = 0x3C

FALCON_KNIGHT = 0x49

PLAYABLE_CLASSES = [
    TRAINEE,
    TRAINEE_2,
    SUPER_TRAINEE,
    PUPIL,
    PUPIL_2,
    SUPER_PUPIL,
    RECRUIT,
    RECRUIT_2,
    SUPER_RECRUIT,
    EPHRAIM_LORD,
    EIRIKA_LORD,
    EPHRAIM_MASTER_LORD,
    EIRIKA_MASTER_LORD,
    FIGHTER,
    PIRATE,
    ROGUE,
    WARRIOR,
    BERSERKER,
    MONK,
    PRIEST,
    PEGASUS_KNIGHT,
    CLERIC,
    TROUBADOUR,
    VALKYRIE,
    DANCER,
    CAVALIER,
    CAVALIER_F,
    KNIGHT,
    KNIGHT_F,
    MYRMIDON,
    MYRMIDON_F,
    ARCHER,
    ARCHER_F,
    MAGE,
    MAGE_F,
    MERCENARY,
    MERCENARY_F,
    WYVERN_RIDER,
    WYVERN_RIDER_F,
    SHAMAN,
    SHAMAN_F,
    SUMMONER,
    SUMMONER_F,
    PALADIN,
    PALADIN_F,
    GENERAL,
    GENERAL_F,
    SWORDMASTER,
    SWORDMASTER_F,
    ASSASSIN,
    ASSASSIN_F,
    SNIPER,
    SNIPER_F,
    HERO,
    HERO_F,
    WYVERN_LORD,
    WYVERN_LORD_F,
    RANGER,
    RANGER_F,
    WYVERN_KNIGHT,
    WYVERN_KNIGHT_F,
    SAGE,
    SAGE_F,
    MAGE_KNIGHT,
    MAGE_KNIGHT_F,
    BISHOP,
    BISHOP_F,
    DRUID,
    DRUID_F,
    GREAT_KNIGHT,
    GREAT_KNIGHT_F,
    THIEF,
    BARD,
    MANAKETE,
    FALCON_KNIGHT,
]

FLIERS = [
    PEGASUS_KNIGHT,
    WYVERN_RIDER,
    WYVERN_RIDER_F,
    WYVERN_LORD,
    WYVERN_LORD_F,
    WYVERN_KNIGHT,
    WYVERN_KNIGHT_F,
    FALCON_KNIGHT,
]

TRAINEE_CLASSES = [TRAINEE, PUPIL, RECRUIT]

BASE_CLASSES = [
    EPHRAIM_LORD,
    EIRIKA_LORD,
    TRAINEE_2,
    PUPIL_2,
    RECRUIT_2,
    KNIGHT,
    KNIGHT_F,
    CAVALIER,
    CAVALIER_F,
    ARCHER,
    ARCHER_F,
    MERCENARY,
    MERCENARY_F,
    FIGHTER,
    PIRATE,
    MYRMIDON,
    MYRMIDON_F,
    THIEF,
    PEGASUS_KNIGHT,
    WYVERN_RIDER,
    WYVERN_RIDER_F,
    TROUBADOUR,
    CLERIC,
    PRIEST,
    MONK,
    MAGE,
    MAGE_F,
    SHAMAN,
    SHAMAN_F,
]

PROMOTED_CLASSES = [
    EPHRAIM_MASTER_LORD,
    EIRIKA_MASTER_LORD,
    GENERAL,
    GENERAL_F,
    GREAT_KNIGHT,
    GREAT_KNIGHT_F,
    PALADIN,
    PALADIN_F,
    SNIPER,
    SNIPER_F,
    RANGER,
    RANGER_F,
    HERO,
    HERO_F,
    WARRIOR,
    BERSERKER,
    SWORDMASTER,
    SWORDMASTER_F,
    ASSASSIN,
    ASSASSIN_F,
    ROGUE,
    FALCON_KNIGHT,
    WYVERN_KNIGHT,
    WYVERN_KNIGHT_F,
    WYVERN_LORD,
    WYVERN_LORD_F,
    MAGE_KNIGHT,
    MAGE_KNIGHT_F,
    VALKYRIE,
    BISHOP,
    BISHOP_F,
    SAGE,
    SAGE_F,
    DRUID,
    DRUID_F,
    SUMMONER,
    SUMMONER_F,
    SUPER_TRAINEE,
    SUPER_PUPIL,
    SUPER_RECRUIT,
]

# Mapping from class IDs to the classes they promote to
PROMOTIONS = {
    0x01: [0x03],
    0x02: [0x04],
    0x05: [0x35, 0x07],
    0x06: [0x08, 0x36],
    0x09: [0x0B, 0x35],
    0x0A: [0x0C, 0x36],
    0x0D: [0x33, 0x17],
    0x0F: [0x11, 0x1D],
    0x10: [0x12, 0x1E],
    0x13: [0x15, 0x17],
    0x14: [0x18, 0x16],
    0x19: [0x1B, 0x1D],
    0x1A: [0x1C, 0x1E],
    0x1F: [0x21, 0x23],
    0x20: [0x22, 0x24],
    0x25: [0x29, 0x27],
    0x26: [0x28, 0x2A],
    0x2D: [0x31, 0x2F],
    0x2E: [0x31, 0x2F],
    0x37: [0x08, 0x3A],
    0x3D: [0x42, 0x3F],
    0x3E: [0x2D, 0x25],
    0x3F: [0x40, 0x11],
    0x42: [0x40, 0x43],
    0x44: [0x2B, 0x27],
    0x45: [0x2B, 0x27],
    0x47: [0x0A, 0x06],
    0x48: [0x49, 0x24],
    0x4A: [0x2C, 0x4C],
    0x4B: [0x2A, 0x4C],
    0x7E: [0x38, 0x11],
    0x7F: [0x39, 0x27],
}

# Mapping from class IDs to the classes they can demote to
DEMOTIONS = {
    0x03: [0x01],
    0x04: [0x02],
    0x06: [0x47],
    0x07: [0x05],
    0x08: [0x06, 0x37],
    0x0A: [0x47],
    0x0B: [0x09],
    0x0C: [0x0A],
    0x11: [0x0F, 0x7E, 0x3F],
    0x12: [0x10],
    0x15: [0x13],
    0x16: [0x14],
    0x17: [0x13, 0x0D],
    0x18: [0x14],
    0x1B: [0x19],
    0x1C: [0x1A],
    0x1D: [0x19, 0x0F],
    0x1E: [0x10, 0x1A],
    0x21: [0x1F],
    0x22: [0x20],
    0x23: [0x1F],
    0x24: [0x48, 0x20],
    0x25: [0x3E],
    0x27: [0x25, 0x44, 0x45, 0x7F],
    0x28: [0x26],
    0x29: [0x25],
    0x2A: [0x4B, 0x26],
    0x2B: [0x44, 0x45],
    0x2C: [0x4A],
    0x2D: [0x3E],
    0x2F: [0x2D, 0x2E],
    0x31: [0x2D, 0x2E],
    0x33: [0x0D],
    0x35: [0x09, 0x05],
    0x36: [0x0A, 0x06],
    0x38: [0x7E],
    0x39: [0x7F],
    0x3A: [0x37],
    0x3F: [0x3D],
    0x40: [0x42, 0x3F],
    0x42: [0x3D],
    0x43: [0x42],
    0x49: [0x48],
    0x4C: [0x4A, 0x4B],
}

# raw data for building a more useful table
# pairs are listed as (male, female)
_class_gender_pairs = [
    [
        EPHRAIM_LORD,
        EIRIKA_LORD,
    ],
    [
        EPHRAIM_MASTER_LORD,
        EIRIKA_MASTER_LORD,
    ],
    [
        CAVALIER,
        CAVALIER_F,
    ],
    [
        KNIGHT,
        KNIGHT_F,
    ],
    [
        MYRMIDON,
        MYRMIDON_F,
    ],
    [
        ARCHER,
        ARCHER_F,
    ],
    [
        MAGE,
        MAGE_F,
    ],
    [
        MERCENARY,
        MERCENARY_F,
    ],
    [
        WYVERN_RIDER,
        WYVERN_RIDER_F,
    ],
    [
        SHAMAN,
        SHAMAN_F,
    ],
    [
        SUMMONER,
        SUMMONER_F,
    ],
    [
        PALADIN,
        PALADIN_F,
    ],
    [
        GENERAL,
        GENERAL_F,
    ],
    [
        SWORDMASTER,
        SWORDMASTER_F,
    ],
    [
        ASSASSIN,
        ASSASSIN_F,
    ],
    [
        SNIPER,
        SNIPER_F,
    ],
    [
        HERO,
        HERO_F,
    ],
    [
        WYVERN_LORD,
        WYVERN_LORD_F,
    ],
    [
        RANGER,
        RANGER_F,
    ],
    [
        WYVERN_KNIGHT,
        WYVERN_KNIGHT_F,
    ],
    [
        SAGE,
        SAGE_F,
    ],
    [
        MAGE_KNIGHT,
        MAGE_KNIGHT_F,
    ],
    [
        BISHOP,
        BISHOP_F,
    ],
    [
        DRUID,
        DRUID_F,
    ],
    [
        GREAT_KNIGHT,
        GREAT_KNIGHT_F,
    ],
]

CLASS_GENDER_SWAPS = {}
for (male, female) in _class_gender_pairs:
    CLASS_GENDER_SWAPS[male] = (male, female)
    CLASS_GENDER_SWAPS[female] = (male, female)
