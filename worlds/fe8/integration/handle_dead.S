.include "macro.inc"
.syntax unified

.section wram_bss, "aw", %nobits
.global NumEnemiesKilled
.global NumAlliesKilled

DATA_START NumEnemiesKilled
NumEnemiesKilled:
.short 0
DATA_END NumEnemiesKilled

DATA_START NumAlliesKilled
NumAlliesKilled:
.short 0
DATA_END NumAlliesKilled

.section .text
.global OnUnitKilled
.thumb

THUMB_FUNC_START OnUnitKilled
OnUnitKilled:
    @ stored parameter r0 points to a Unit struct representing the unit that has died

    @ load saved r0
    ldr r0, [r0, 0]

    @ load killed->index
    ldrb r1, [r0, #0x0B]

    @ get unit faction
    movs r2, #0xC0
    ands r1, r2

    @ if player unit...
    cmp r1, #0
    beq 1f

    @ if not enemy unit...
    cmp r1, #0x80
    bne 2f

    @ increment enemy kill count
    ldr r1, =NumEnemiesKilled
    ldrh r2, [r1]
    adds r2, r2, #1
    strh r2, [r1]
    b 2f

    1:
    @ bail if killed->pClassData->number == 81
    ldr r1, [r0, #4]
    ldrb r1, [r1, #4]
    cmp r1, #81
    beq 2f

    @ also bail if killed->pCharacterData->number is 1 or 15 (Eirika / Ephraim)
    ldr r1, [r0, #0]
    ldrb r1, [r1, #4]

    cmp r1, #1
    beq 2f

    cmp r1, #15
    beq 2f

    @ unit was not a phantom, not Eirika, and not Ephraim
    @ mark killed->state as "hidden" and "not deployed"
    ldr r1, [r0, #0x0C]
    movs r2, #0x09
    orrs r1, r2
    str r1, [r0, #0x0C]

    @ increment allies killed count
    ldr r1, =NumAlliesKilled
    ldrh r2, [r1]
    adds r2, r2, #1
    strh r2, [r1]

    @ skip original processing
    movs r0, #1
    bx lr

    @ fall through to original function
    2:
    movs r0, #0
    bx lr
THUMB_FUNC_END OnUnitKilled
