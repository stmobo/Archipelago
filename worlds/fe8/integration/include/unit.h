#ifndef UNIT_H
#define UNIT_H

#include "types.h"

struct Unit
{
    /* 00 */ const void* pCharacterData;
    /* 04 */ const void* pClassData;

    /* 08 */ i8 level;
    /* 09 */ u8 exp;

    /* 0A */ u8 aiFlags;

    /* 0B */ i8 index;

    /* 0C */ u32 state;

    /* 10 */ i8 xPos;
    /* 11 */ i8 yPos;

    /* 12 */ i8 maxHP;
    /* 13 */ i8 curHP;
    /* 14 */ i8 pow;
    /* 15 */ i8 skl;
    /* 16 */ i8 spd;
    /* 17 */ i8 def;
    /* 18 */ i8 res;
    /* 19 */ i8 lck;

    /* 1A */ i8 conBonus;
    /* 1B */ u8 rescueOtherUnit;
    /* 1C */ u8 ballistaIndex;
    /* 1D */ i8 movBonus;

    /* 1E */ u16 items[5];
    /* 28 */ u8 ranks[8];

    /* 30 */ u8 statusIndexDuration;

    /* 31 */ u8 torchBarrierDuration;

    /* 32 */ u8 supports[7];
    /* 39 */ i8 supportBits;
    /* 3A */ u8 _u3A;
    /* 3B */ u8 _u3B;

    /* 3C */ void* pMapSpriteHandle;

    /* 40 */ u16 ai3And4;
    /* 42 */ u8 ai1;
    /* 43 */ u8 ai1data;
    /* 44 */ u8 ai2;
    /* 45 */ u8 ai2data;
    /* 46 */ u8 _u46;
    /* 47 */ u8 _u47;
};

extern struct Unit* gUnitLookup[];
extern struct Unit* GetUnitFromCharId(u32 charId);

extern struct Unit* gActiveUnit;
extern u8** gBmMapUnit;
extern u8** gBmMapMovement;
extern u8** gBmMapHidden;
extern u8** gBmMapTerrain;
extern const i8* GetUnitMovementCost(struct Unit* unit);


#endif