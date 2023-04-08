#include "types.h"

/* Called whenever the player saves a new game from the main menu(?) */
int OnNewGameSave(ShimRegisters *regs)
{
    /* [r0+0x2A] contains the selected difficulty setting
     * (0 = easy, 1 = normal, 2 = difficult)
     * [r0+0x2C] contains to selected save slot
     **/
    u8 *menuData = (u8 *)(regs->r0);
    menuData[0x2A] = 2;
    menuData[0x2C] = 0;
    return 0;
}

/* Shim for SaveGame */
int OnGameSave(ShimRegisters *regs)
{
    regs->r0 = 0; // always save to slot 1
    return 0;
}

/* Shim for LoadGame */
int OnGameLoad(ShimRegisters *regs)
{
    regs->r0 = 0; // always load from slot 1
    return 0;
}

/* Shim for CopyGameSave */
int DisableSaveCopying(ShimRegisters *regs)
{
    /* Don't do anything, just prevent the call from going through */
    return 1;
}
