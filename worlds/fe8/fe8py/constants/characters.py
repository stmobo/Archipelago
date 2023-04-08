from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional

AP_ID_OFFSET = 91000
AP_CHARACTER_ID_START = AP_ID_OFFSET + 50

EIRIKA = 0x01
SETH = 0x02
GILLIAM = 0x03
FRANZ = 0x04
MOULDER = 0x05
VANESSA = 0x06
ROSS = 0x07
NEIMI = 0x08
COLM = 0x09
GARCIA = 0x0A
INNES = 0x0B
LUTE = 0x0C
NATASHA = 0x0D
CORMAG = 0x0E
EPHRAIM = 0x0F
FORDE = 0x10
KYLE = 0x11
AMELIA = 0x12
ARTUR = 0x13
GERIK = 0x14
TETHYS = 0x15
MARISA = 0x16
SALEH = 0x17
EWAN = 0x18
LARACHEL = 0x19
DOZLA = 0x1A
# 0x1B is unassigned
RENNAC = 0x1C
DUESSEL = 0x1D
MYRRH = 0x1E
KNOLL = 0x1F
JOSHUA = 0x20
SYRENE = 0x21
TANA = 0x22

LYON = 0x40
MORVA = 0x41
ORSON_CH5X = 0x42
VALTER = 0x43
SELENA = 0x44
VALTER_PROLOGUE = 0x45
BREGUET = 0x46
BONE = 0x47
BAZBA = 0x48
ENTOUMBED_CH4 = 0x49
SAAR = 0x4A
NOVALA = 0x4B
MURRAY = 0x4C
TIRADO = 0x4D
BINKS = 0x4E
PABLO = 0x4F
MAELDUIN = 0x50
AIAS = 0x51
CARLYLE = 0x52
CAELLACH = 0x53
PABLO_2 = 0x54
GORGON = 0x56
RIEV = 0x57
GHEB = 0x5A
BERAN = 0x5B
CYCLOPS = 0x5C
WIGHT = 0x5D
DEATHGOYLE = 0x5E
BANDIT_CH5 = 0x66
ONEILL = 0x68
GLEN = 0x69
ZONTA = 0x6A
VIGARDE = 0x6B
LYON_FINAL = 0x6C
ORSON = 0x6D
FOMORTIIS = 0xBE

PLAYABLE_CHARACTERS = [
    EIRIKA,
    SETH,
    GILLIAM,
    FRANZ,
    MOULDER,
    VANESSA,
    ROSS,
    NEIMI,
    COLM,
    GARCIA,
    INNES,
    LUTE,
    NATASHA,
    CORMAG,
    EPHRAIM,
    FORDE,
    KYLE,
    AMELIA,
    ARTUR,
    GERIK,
    TETHYS,
    MARISA,
    SALEH,
    EWAN,
    LARACHEL,
    DOZLA,
    RENNAC,
    DUESSEL,
    MYRRH,
    KNOLL,
    JOSHUA,
    SYRENE,
    TANA,
]

LORDS = [EIRIKA, EPHRAIM]
THIEVES = [COLM, RENNAC]
SPECIAL_CHARACTERS = [TETHYS, MYRRH]
FEMALES = [
    EIRIKA,
    VANESSA,
    NEIMI,
    LUTE,
    NATASHA,
    AMELIA,
    TETHYS,
    MARISA,
    LARACHEL,
    MYRRH,
    SYRENE,
    TANA,
]
REQUIRES_RANGE = [ARTUR]
REQUIRES_MELEE = [SETH]
REQUIRES_FLYING = [VANESSA, CORMAG]
REQUIRES_ATTACKING = [EIRIKA, EPHRAIM, SETH, ARTUR, GARCIA]

FLIERS = [
    VANESSA,
    CORMAG,
    SYRENE,
    TANA,
]

MELEE_ATTACKERS = [
    EIRIKA,
    SETH,
    GILLIAM,
    FRANZ,
    VANESSA,
    ROSS,
    COLM,
    GARCIA,
    CORMAG,
    EPHRAIM,
    FORDE,
    KYLE,
    AMELIA,
    GERIK,
    MARISA,
    DOZLA,
    RENNAC,
    DUESSEL,
    JOSHUA,
    SYRENE,
    TANA,
]

RANGED_ATTACKERS = [
    NEIMI,
    INNES,
    LUTE,
    ARTUR,
    SALEH,
    EWAN,
    KNOLL,
]

NAMES = {
    EIRIKA: "Eirika",
    SETH: "Seth",
    GILLIAM: "Gilliam",
    FRANZ: "Franz",
    MOULDER: "Moulder",
    VANESSA: "Vanessa",
    ROSS: "Ross",
    NEIMI: "Neimi",
    COLM: "Colm",
    GARCIA: "Garcia",
    INNES: "Innes",
    LUTE: "Lute",
    NATASHA: "Natasha",
    CORMAG: "Cormag",
    EPHRAIM: "Ephraim",
    FORDE: "Forde",
    KYLE: "Kyle",
    AMELIA: "Amelia",
    ARTUR: "Artur",
    GERIK: "Gerik",
    TETHYS: "Tethys",
    MARISA: "Marisa",
    SALEH: "Saleh",
    EWAN: "Ewan",
    LARACHEL: "L'Arachel",
    DOZLA: "Dozla",
    RENNAC: "Rennac",
    DUESSEL: "Duessel",
    MYRRH: "Myrrh",
    KNOLL: "Knoll",
    JOSHUA: "Joshua",
    SYRENE: "Syrene",
    TANA: "Tana",
}

PORTRAIT_IDS = {
    EIRIKA: [0x02, 0x03],
    SETH: [0x04],
    GILLIAM: [0x05],
    FRANZ: [0x06],
    MOULDER: [0x07],
    VANESSA: [0x08],
    ROSS: [0x09],
    NEIMI: [0x0A, 0x0B],
    COLM: [0x0C, 0x0D],
    GARCIA: [0x0E],
    INNES: [0x0F],
    LUTE: [0x10],
    NATASHA: [0x11, 0x12],
    CORMAG: [0x13],
    EPHRAIM: [0x14, 0x15],
    FORDE: [0x16, 0x17],
    KYLE: [0x18],
    AMELIA: [0x19],
    ARTUR: [0x1A],
    GERIK: [0x1B],
    TETHYS: [0x1C, 0x1D],
    MARISA: [0x1E, 0x1F],
    SALEH: [0x20],
    EWAN: [0x21],
    LARACHEL: [0x22],
    DOZLA: [0x23],
    RENNAC: [0x24],
    DUESSEL: [0x25],
    MYRRH: [0x26, 0x27, 0x28],
    KNOLL: [0x29],
    JOSHUA: [0x2A],
    SYRENE: [0x2B],
    TANA: [0x2C],
}

BOSS_CHARACTERS = [
    LYON,
    MORVA,
    ORSON_CH5X,
    VALTER,
    SELENA,
    VALTER_PROLOGUE,
    BREGUET,
    BONE,
    BAZBA,
    ENTOUMBED_CH4,
    SAAR,
    NOVALA,
    MURRAY,
    TIRADO,
    BINKS,
    PABLO,
    MAELDUIN,
    AIAS,
    CARLYLE,
    CAELLACH,
    PABLO_2,
    GORGON,
    RIEV,
    GHEB,
    BERAN,
    CYCLOPS,
    WIGHT,
    DEATHGOYLE,
    BANDIT_CH5,
    ONEILL,
    GLEN,
    ZONTA,
    VIGARDE,
    LYON_FINAL,
    ORSON,
    FOMORTIIS,
]

ALL_CHARACTERS = PLAYABLE_CHARACTERS + BOSS_CHARACTERS


# fmt: off

# Mapping from chapter IDs to characters that are required to clear the level with no deaths.
# Generally, this means characters that are required to recruit other characters in each chapter.
#
# NOTE: a lot of these recruitments can also be done with the route lord, so maybe we can drop some characters from these lists?
CHAPTER_EXIT_REQUIREMENTS = {
    0x02: [VANESSA, ROSS],        # C2 (Vanessa rescues Ross, Ross recruits Garcia; Vanessa isn't strictly required, but Ross is probably screwed otherwise.)
    0x03: [NEIMI],                # C3 (Neimi => Colm)
    0x06: [NATASHA],              # C5 (Natasha => Joshua)
    0x0B: [TANA, INNES, GERIK],   # C10A (Tana/Eirika => Innes, Innes => Gerik and Tethys, Gerik => Marisa)
    0x3D: [LARACHEL],             # C11A (L'Arachel => Dozla) 
    0x0D: [FRANZ],                # C13A (Franz/Eirika => Amelia)
    0x0E: [LARACHEL],             # C14A (L'Arachel/Eirika => Rennac)
    0x17: [FRANZ],                # C9B (Franz/Ephraim => Amelia)
    0x18: [DUESSEL, TANA],        # C10B (Duessel/Tana => Cormag)
    0x3E: [LARACHEL],             # C11B (L'Arachel => Dozla)
    0x19: [EWAN],                 # C12B (Ewan => Marisa)
    0x1B: [LARACHEL],             # C14B (L'Arachel/Ephraim => Rennac),
    0x11: [TANA, VANESSA, INNES], # C17A (Tana/Vanessa/Innes => Syrene)
    0x1E: [TANA, VANESSA, INNES], # C17B (Tana/Vanessa/Innes => Syrene)
}

# Mapping from chapter index => next chapter index.
# This could probably be stored in a more concise way.
# Also, this should probably go into a different file.
CHAPTER_LINKS = {
    # Common route:
    0x00: 0x01, # Prologue => C1
    0x01: 0x38, # C1 => Castle Frelia
    0x38: 0x02, # Castle Frelia => C2
    0x02: 0x03, # C2 => C3
    0x03: 0x04, # C3 => C4
    0x04: 0x06, # C4 => C5 (yes, C5 is chapter ID 0x06 and C5x is ID 0x05)
    0x06: 0x05, # C5 => C5x
    0x05: 0x07, # C5x => C6
    0x07: 0x08, # C6 => C7
    0x08: 0x09, # C7 => C8

    # route split happens at chapter 0x09 (C8)--handle that specially in logic

    # Eirika route:
    0x0A: 0x0B, # C9A => C10A
    0x0B: 0x3D, # C10A => C11A,
    0x3D: 0x0C, # C11A => C12A,
    0x0C: 0x0D, # C12A => C13A
    0x0D: 0x0E, # C13A => C14A
    0x0E: 0x0F, # C14A => C15A
    0x0F: 0x10, # C15A => C16A
    0x10: 0x11, # C16A => C17A
    0x11: 0x12, # C17A => C18A
    0x12: 0x13, # C18A => C19A
    0x13: 0x14, # C19A => C20A
    0x14: 0x15, # C20A => C21A
    0x15: 0x16, # C21A => C21xA
    0x16: None, # C21xA => end

    # Ephraim route:
    0x17: 0x18, # C9B => C10B
    0x18: 0x3E, # C10B => C11B
    0x3E: 0x19, # C11B => C12B
    0x19: 0x1A, # C12B => C13B
    0x1A: 0x1B, # C13B => C14B
    0x1B: 0x1C, # C14B => C15B
    0x1C: 0x1D, # C15B => C16B
    0x1D: 0x1E, # C16B => C17B
    0x1E: 0x1F, # C17B => C18B
    0x1F: 0x20, # C18B => C19B
    0x20: 0x21, # C19B => C20B
    0x21: 0x22, # C20B => C21B
    0x22: 0x23, # C21B => C21xB
    0x23: None, # C21xB => end
}

COMMON_CHAPTERS = [
    0x00,
    0x01,
    0x38,
    0x02,
    0x03,
    0x04,
    0x06,
    0x05,
    0x07,
    0x08,
    0x09
]

EIRIKA_CHAPTERS = [
    0x0A,
    0x0B,
    0x3D,
    0x0C,
    0x0D,
    0x0E,
    0x0F,
    0x10,
    0x11,
    0x12,
    0x13,
    0x14,
    0x15,
    0x16
]

EPHRAIM_CHAPTERS = [
    0x17,
    0x18,
    0x3E,
    0x19,
    0x1A,
    0x1B,
    0x1C,
    0x1D,
    0x1E,
    0x1F,
    0x20,
    0x21,
    0x22,
    0x23
]

CHAPTER_SHORT_NAMES = {
    # Common route:
    0x00: "Prologue",
    0x01: "C1",
    0x38: "Castle Frelia",
    0x02: "C2",
    0x03: "C3",
    0x04: "C4",
    0x05: "C5x",
    0x06: "C5",
    0x07: "C6",
    0x08: "C7",
    0x09: "C8",

    # Eirika route:
    0x0A: "C9A", 
    0x0B: "C10A",
    0x3D: "C11A",
    0x0C: "C12A",
    0x0D: "C13A",
    0x0E: "C14A",
    0x0F: "C15",
    0x10: "C16",
    0x11: "C17",
    0x12: "C18",
    0x13: "C19",
    0x14: "C20",
    0x15: "C21",
    0x16: "C21x",

    # Ephraim route:
    0x17: "C9B", 
    0x18: "C10B",
    0x3E: "C11B",
    0x19: "C12B",
    0x1A: "C13B",
    0x1B: "C14B",
    0x1C: "C15",
    0x1D: "C16",
    0x1E: "C17",
    0x1F: "C18",
    0x20: "C19",
    0x21: "C20",
    0x22: "C21",
    0x23: "C21x",
}

CHAPTER_NAMES = {
    # Common route:
    0x00: "The Fall of Renais",
    0x01: "Escape!",
    0x38: "Castle Frelia",
    0x02: "The Protected",
    0x03: "The Bandits of Borgo",
    0x04: "Ancient Horrors",
    0x05: "Unbroken Heart",
    0x06: "The Empire's Reach",
    0x07: "Victims of War",
    0x08: "Waterside Renvall",
    0x09: "It's a Trap!",

    # Eirika route:
    0x0A: "Distant Blade", 
    0x0B: "Revolt at Carcino",
    0x3D: "Creeping Darkness",
    0x0C: "Village of Silence",
    0x0D: "Hamill Canyon",
    0x0E: "Queen of White Dunes",
    0x0F: "Scorched Sand",
    0x10: "Ruled by Madness",
    0x11: "River of Regrets",
    0x12: "Two Faces of Evil",
    0x13: "Last Hope",
    0x14: "Darkling Woods",
    0x15: "Sacred Stone (Part 1)",
    0x16: "Sacred Stone (Part 2)",

    # Ephraim route:
    0x17: "Fort Rigwald",
    0x18: "Turning Traitor",
    0x3E: "Phantom Ship",
    0x19: "Landing at Taizel",
    0x1A: "Fluorspar's Oath",
    0x1B: "Father and Son",
    0x1C: "Scorched Sand",
    0x1D: "Ruled by Madness",
    0x1E: "River of Regrets",
    0x1F: "Two Faces of Evil",
    0x20: "Last Hope",
    0x21: "Darkling Woods",
    0x22: "Sacred Stone (Part 1)",
    0x23: "Sacred Stone (Part 2)",
}

class Recruitment(NamedTuple):
    character_id: int
    chapter_id: int
    requirements: Optional[List[int]]

    @property
    def eirika_route(self) -> bool:
        return self.chapter_id in EIRIKA_CHAPTERS
    
    @property
    def ephraim_route(self) -> bool:
        return self.chapter_id in EPHRAIM_CHAPTERS
    
    @property
    def common_route(self) -> bool:
        return (not self.eirika_route) and (not self.ephraim_route)


# Map of character IDs to the chapters where they're recruited and the characters required to recruit them.
# None values indicate characters that are automatically recruited.
#
# Characters with one list element are recruited in the common route.
# Characters recruited after the route split have a two-item list, where the first element is for Eirika's route and the second is for Ephraim's.
RECRUITMENT_LOCATIONS = {
    EIRIKA:  [ Recruitment(EIRIKA, 0x00, None), ],         # Prologue
    SETH:    [ Recruitment(SETH, 0x00, None), ],           # Prologue
    FRANZ:   [ Recruitment(FRANZ, 0x01, None), ],          # C1
    GILLIAM: [ Recruitment(GILLIAM, 0x01, None), ],        # C1
    VANESSA: [ Recruitment(VANESSA, 0x38, None), ],        # Castle Frelia
    MOULDER: [ Recruitment(MOULDER, 0x38, None), ],        # Castle Frelia
    ROSS:    [ Recruitment(ROSS, 0x02, [EIRIKA]), ],       # C2
    GARCIA:  [ Recruitment(GARCIA, 0x02, [ROSS]), ],       # C2
    NEIMI:   [ Recruitment(NEIMI, 0x03, None), ],          # C3
    COLM:    [ Recruitment(COLM, 0x03, [NEIMI]), ],        # C3
    ARTUR:   [ Recruitment(ARTUR, 0x04, None), ],          # C4
    LUTE:    [ Recruitment(LUTE, 0x04, None), ],           # C4
    NATASHA: [ Recruitment(NATASHA, 0x06, None), ],        # C5
    JOSHUA:  [ Recruitment(JOSHUA, 0x06, None), ],         # C5
    EPHRAIM: [ Recruitment(EPHRAIM, 0x09, None), ],        # C8
    FORDE:   [ Recruitment(FORDE, 0x09, None), ],          # C8
    KYLE:    [ Recruitment(KYLE, 0x09, None), ],           # C8
    TANA: [
        Recruitment(TANA, 0x0A, None),                     # C9A
        Recruitment(TANA, 0x17, None),                     # C9B
    ],
    AMELIA: [
        Recruitment(AMELIA, 0x0D, [EIRIKA, FRANZ]),        # C13A
        Recruitment(AMELIA, 0x17, [EPHRAIM, FRANZ]),       # C9B
        # Recruitment(0x0A, [EIRIKA, FRANZ]),              # technically C9A, but for the purposes of AP logic we'll treat her as being recruited in C13A in Eirika's route.
    ],
    INNES: [
        Recruitment(INNES, 0x0B, [TANA, EIRIKA]),          # C10A
        Recruitment(INNES, 0x1C, None),                    # C15B (auto recruited)
    ],
    GERIK: [
        Recruitment(GERIK, 0x0B, [INNES]),                 # C10A (note: Tethys should be here, but adding her causes a circular dependency)
        Recruitment(GERIK, 0x1A, None),                    # C13B (auto)
    ],
    TETHYS: [
        Recruitment(TETHYS, 0x0B, [INNES]),                # C10A (note: Gerik should be here, but adding him causes a circular dependency)
        Recruitment(TETHYS, 0x1A, None),                   # C13B (auto)
    ],
    MARISA: [
        Recruitment(MARISA, 0x0B, [GERIK]),                # C10A
        Recruitment(MARISA, 0x19, [EWAN]),                 # C12B
    ],
    LARACHEL: [
        Recruitment(LARACHEL, 0x3D, [EIRIKA]),             # C11A
        Recruitment(LARACHEL, 0x3E, [EPHRAIM]),            # C11B
    ],
    DOZLA: [
        Recruitment(DOZLA, 0x3D, [LARACHEL]),              # C11A
        Recruitment(DOZLA, 0x3E, [LARACHEL]),              # C11B
    ],
    SALEH: [
        Recruitment(SALEH, 0x0C, None),                    # C12A (auto)
        Recruitment(SALEH, 0x1C, None),                    # C15B (auto)
    ],
    EWAN: [
        Recruitment(EWAN, 0x0C, None),                     # C12A (village)
        Recruitment(EWAN, 0x19, None),                     # C12B (village)
    ],
    CORMAG: [
        Recruitment(CORMAG, 0x0D, [EIRIKA]),               # C13A
        Recruitment(CORMAG, 0x18, [DUESSEL, TANA]),        # C10B
    ],
    RENNAC: [
        Recruitment(RENNAC, 0x0E, [EIRIKA, LARACHEL]),     # C14A
        Recruitment(RENNAC, 0x1B, [EPHRAIM, LARACHEL]),    # C14B
    ],
    DUESSEL: [
        Recruitment(DUESSEL, 0x0F, None),                  # C15A
        Recruitment(DUESSEL, 0x18, [EPHRAIM]),             # C10B
    ],
    KNOLL: [
        Recruitment(KNOLL, 0x0F, None),                    # C15A
        Recruitment(KNOLL, 0x1C, None),                    # C15B
    ],
    MYRRH: [
        Recruitment(MYRRH, 0x10, None),                    # C16A
        Recruitment(MYRRH, 0x1D, None),                    # C16B
    ],
    SYRENE: [
        Recruitment(SYRENE, 0x11, [TANA, VANESSA, INNES]), # C17A
        Recruitment(SYRENE, 0x1E, [TANA, VANESSA, INNES]), # C17B
    ]
}

RECRUITMENTS_BY_CHAPTER: Dict[int, List[Recruitment]] = {}

for char_id, recruit_locs in RECRUITMENT_LOCATIONS.items():
    for location in recruit_locs:
        RECRUITMENTS_BY_CHAPTER.setdefault(location.chapter_id, []).append(location)

# Mapping from recruitment event memory locations to characters added by those events
RECRUITMENT_EVENTS = {
    0x089EFA68: [FRANZ, GILLIAM],               # C1 turn 2
    0x089FF354: [MOULDER, VANESSA],             # Castle Frelia event
    0x089F05FC: [ROSS],                         # C2 talk w/ Eirika
    0x089F0628: [GARCIA],                       # C2 talk w/ Ross
    0x089F04B4: [ROSS, GARCIA],                 # C2 end
    0x089F1200: [NEIMI],                        # C3 start
    0x089F1568: [COLM],                         # C3 talk w/ Neimi
    0x089F13CC: [COLM],                         # C3 end
    0x089F17A4: [ARTUR],                        # C4 start
    0x089F1B38: [LUTE],                         # C4 village
    0x089F19F8: [LUTE],                         # C4 end
    0x089F23FC: [FORDE, KYLE],                  # C5x start (not including Ephraim here since he's a lord)
    0x089F1D28: [NATASHA],                      # C5 start
    0x089F2270: [JOSHUA],                       # C5 talk w/ Natasha
    0x089F2090: [JOSHUA],                       # C5 end, need to account for chapter ending before Joshua's recruitment
    0x089F3124: [EPHRAIM, FORDE, KYLE],         # C8 turn 2 - need to account for route choice for C9A/B
    0x089F396C: [TANA],                         # C9A start
    0x089F3F4C: [AMELIA],                       # C9A talk w/ Eirika
    0x089F3F74: [AMELIA],                       # C9A talk w/ Franz
    0x089F4634: [INNES],                        # C10A talk w/ Eirika
    0x089F465C: [INNES],                        # C10A talk w/ Tana
    0x089F4684: [GERIK],                        # C10A talk w/ Innes
    0x089F46AC: [GERIK],                        # C10A talk w/ Tethys
    0x089F46D4: [TETHYS],                       # C10A talk w/ Innes
    0x089F46FC: [TETHYS],                       # C10A talk w/ Gerik
    0x089F4724: [MARISA],                       # C10A talk w/ Gerik
    0x089F43F8: [INNES, GERIK, TETHYS, MARISA], # C10A end (account for chapter ending before Marisa's recruitment)
    0x089F4E54: [LARACHEL],                     # C11A talk w/ Eirika
    0x089F4E7C: [DOZLA],                        # C11A talk w/ L'Arachel
    0x089F4A7C: [DOZLA, LARACHEL],              # C11A end
    0x089F4F88: [SALEH],                        # C12A start
    0x089F53AC: [EWAN],                         # C12A village
    0x089F51B0: [EWAN],                         # C12A end
    0x089F59CC: [AMELIA],                       # C13A talk w/ Eirika
    0x089F59F8: [AMELIA],                       # C13A talk w/ Franz
    0x089F5A20: [CORMAG],                       # C13A talk w/ Eirika
    0x089F5798: [AMELIA, CORMAG],               # C13A end - need to account for chapter ending before these characters can be recruited
    0x089F619C: [RENNAC],                       # C14A talk w/ L'Arachel
    0x089F61C4: [RENNAC],                       # C14A talk w/ Eirika -- might need to account for player not having enough money?
    0x089F5DB8: [RENNAC],                       # C14A end - account for chapter ending before recruitment
    0x089F6404: [DUESSEL, KNOLL, EPHRAIM],      # C15A turn 2
    0x089FA138: [TANA],                         # C9B start
    0x089FA634: [AMELIA],                       # C9B talk w/ Ephraim
    0x089FA65C: [AMELIA],                       # C9B talk w/ Franz
    0x089FA4E0: [AMELIA],                       # C9B end -- account for chapter ending before recruitment
    0x089FAEDC: [DUESSEL],                      # C10B talk w/ Ephraim
    0x089FAF04: [CORMAG],                       # C10B talk w/ Duessel
    0x089FAF2C: [CORMAG],                       # C10B talk w/ Tana
    0x089FAC20: [CORMAG, DUESSEL],              # C10B end -- account for chapter ending before recruitment for Cormag
    0x089FB394: [LARACHEL],                     # C11B talk w/ Ephraim
    0x089FB3BC: [DOZLA],                        # C11B talk w/ L'Arachel
    0x089FB318: [LARACHEL, DOZLA],              # C11B end
    0x089FB934: [EWAN],                         # C12B house
    0x089FB90C: [MARISA],                       # C12B talk w/ Ewan
    0x089FB770: [EWAN, MARISA],                 # C12B end
    0x089FB9F8: [GERIK, TETHYS],                # C13B start
    0x089FC520: [RENNAC],                       # C14B talk w/ L'Arachel
    0x089FC52C: [RENNAC],                       # C14B talk w/ Ephraim -- need to account for player not having enough money?
    0x089FC06C: [RENNAC],                       # C14B end - account for chapter ending before Rennac's recruitment
    0x089FC740: [EIRIKA, INNES, SALEH, KNOLL],  # C15B start -- Knoll is recruited pre-deploy screen
    0x089F6A34: [MYRRH],                        # C16A start -- Myrrh is recruited pre-deploy screen
    0x089FCD40: [MYRRH],                        # C16B start -- Myrrh is recruited pre-deploy screen
    0x089F7CD4: [SYRENE],                       # C17A talk w/ Tana
    0x089F7CAC: [SYRENE],                       # C17A talk w/ Innes
    0x089F7CFC: [SYRENE],                       # C17A talk w/ Vanessa
    0x089FCEF8: [SYRENE],                       # C17B talk w/ Tana
    0x089FCEEC: [SYRENE],                       # C17B talk w/ Innes
    0x089FCF04: [SYRENE],                       # C17B talk w/ Vanessa
    0x089F79D4: [SYRENE],                       # C17 end (common)
}

# Events for which we should skip displaying warp effects for unavailable units.
# These are chapter end events + the post-C1 Castle Frelia event.
SKIP_WARP_EVENTS = [
    0x089FF354,
    0x089F04B4,
    0x089F13CC,
    0x089F19F8,
    0x089F2090,
    0x089F43F8,
    0x089F4A7C,
    0x089F51B0,
    0x089F5798,
    0x089F5DB8,
    0x089FA4E0,
    0x089FAC20,
    0x089FB318,
    0x089FB770,
    0x089FC06C,
    0x089F79D4
]

# List of chapter end events where we may need to account for missed enemy recruitments.
# In some cases, this may require loading a unit from a definition.
MISSABLE_RECRUIT_CATCHUPS = {
    0x089F2090: [JOSHUA],         # C5
    0x089F43F8: [MARISA],         # C10A
    0x089F5798: [AMELIA, CORMAG], # C13A
    0x089F5DB8: [RENNAC],         # C14A
    0x089FA4E0: [AMELIA],         # C9B
    0x089FAC20: [CORMAG],         # C10B
    0x089FB770: [EWAN, MARISA],   # C12B
    0x089FC06C: [RENNAC],         # C14B
}

# Memory locations of village thief target conditions (LOCA type 0x20)
# These need to be set to have completion flag ID 0x65 so that they trigger an instant game over when destroyed
REQUIRED_VILLAGE_DESTROYED_EVENTS = [
    0x089E8AC0, # Lute, C4
    0x089EA690, # Ewan, C12B
]

# Characters available upon entry to each chapter.
AVAIL_MAP = {
    0x00: {EIRIKA, SETH},
    0x01: {EIRIKA, SETH},
    0x02: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA},
    0x03: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, GARCIA},
    0x04: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA},
    0x05: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, ARTUR, JOSHUA},
    0x06: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, ARTUR},
    0x07: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, ARTUR, JOSHUA},
    0x08: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, ARTUR, JOSHUA},
    0x09: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, ARTUR, JOSHUA},
    0x0A: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, EPHRAIM, FORDE, KYLE, ARTUR, JOSHUA},
    0x0B: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, EPHRAIM, FORDE, KYLE, ARTUR, JOSHUA, TANA},
    0x0C: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, EPHRAIM, FORDE, KYLE, ARTUR, GERIK, TETHYS, MARISA, LARACHEL, DOZLA, JOSHUA, TANA},
    0x0D: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, EPHRAIM, FORDE, KYLE, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, JOSHUA, TANA},
    0x0E: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, JOSHUA, TANA},
    0x0F: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, JOSHUA, TANA},
    0x10: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, KNOLL, JOSHUA, TANA},
    0x11: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, TANA},
    0x12: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, SYRENE, TANA},
    0x13: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, SYRENE, TANA},
    0x14: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, SYRENE, TANA},
    0x15: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, SYRENE, TANA},
    0x16: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, SYRENE, TANA},
    0x17: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, EPHRAIM, FORDE, KYLE, ARTUR, JOSHUA},
    0x18: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, JOSHUA, TANA},
    0x19: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, LARACHEL, DOZLA, DUESSEL, JOSHUA, TANA},
    0x1A: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, MARISA, EWAN, LARACHEL, DOZLA, DUESSEL, JOSHUA, TANA},
    0x1B: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, EWAN, LARACHEL, DOZLA, DUESSEL, JOSHUA, TANA},
    0x1C: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, JOSHUA, TANA},
    0x1D: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, KNOLL, JOSHUA, TANA},
    0x1E: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, TANA},
    0x1F: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, SYRENE, TANA},
    0x20: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, SYRENE, TANA},
    0x21: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, SYRENE, TANA},
    0x22: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, SYRENE, TANA},
    0x23: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, GERIK, TETHYS, MARISA, SALEH, EWAN, LARACHEL, DOZLA, RENNAC, DUESSEL, MYRRH, KNOLL, JOSHUA, SYRENE, TANA},
    0x38: {EIRIKA, SETH, GILLIAM, FRANZ},
    0x3D: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, INNES, LUTE, NATASHA, EPHRAIM, FORDE, KYLE, ARTUR, GERIK, TETHYS, MARISA, JOSHUA, TANA},
    0x3E: {EIRIKA, SETH, GILLIAM, FRANZ, MOULDER, VANESSA, ROSS, NEIMI, COLM, GARCIA, LUTE, NATASHA, CORMAG, EPHRAIM, FORDE, KYLE, AMELIA, ARTUR, DUESSEL, JOSHUA, TANA},
}

# fmt: on


class CharacterSlot(NamedTuple):
    id: int
    name: str
    ap_id: int
    is_female: bool
    requires_melee: bool
    requires_range: bool
    requires_attack: bool
    requires_flying: bool
    randomizable: bool
    recruit_data: Dict[int, List[int]]

    @classmethod
    def from_ap_id(cls, ap_id: int) -> CharacterSlot:
        return cls.from_id(ap_id - AP_CHARACTER_ID_START)

    @classmethod
    def from_id(cls, id: int) -> CharacterSlot:
        return cls(
            id,
            NAMES[id],
            AP_CHARACTER_ID_START + id,
            id in FEMALES,
            id in REQUIRES_MELEE,
            id in REQUIRES_RANGE,
            id in REQUIRES_ATTACKING,
            id in REQUIRES_FLYING,
            (id not in LORDS)
            and (id not in SPECIAL_CHARACTERS)
            and (id not in THIEVES),
            RECRUITMENT_LOCATIONS[id],
        )


class CharacterFill(NamedTuple):
    id: int
    name: str
    ap_id: int
    is_female: bool
    melee_capable: bool
    ranged_capable: bool
    flying: bool
    randomizable: bool

    @property
    def attack_capable(self) -> bool:
        return self.melee_capable or self.ranged_capable

    @classmethod
    def from_ap_id(cls, ap_id: int) -> CharacterFill:
        return cls.from_id(ap_id - AP_CHARACTER_ID_START)

    @classmethod
    def from_id(cls, id: int) -> CharacterFill:
        return cls(
            id,
            NAMES[id],
            AP_CHARACTER_ID_START + id,
            id in FEMALES,
            id in MELEE_ATTACKERS,
            id in RANGED_ATTACKERS,
            id in FLIERS,
            (id not in LORDS)
            and (id not in SPECIAL_CHARACTERS)
            and (id not in THIEVES),
        )
