.include "macro.inc"
.syntax unified


.section wram_bss, "aw", %nobits
DATA_START UnitDisappearQueue
UnitDisappearQueue:
.short 0
.short 0
.short 0
.short 0
.short 0
.short 0
DATA_END UnitDisappearQueue

DATA_START UnitDisappearQueueLen
UnitDisappearQueueLen:
.byte 0
DATA_END UnitDisappearQueueLen

.data
.global IsCharacterAvailable

DATA_START IsCharacterAvailable
IsCharacterAvailable:
.byte 0
.byte 1
.byte 1
.rept 12
.byte 0
.endr
.byte 1
.rept 19
.byte 0
.endr
DATA_END IsCharacterAvailable

.section .text
.thumb

.global OnTickActiveFactionTurn

.global PrepareUnitDisappear
THUMB_FUNC_START PrepareUnitDisappear
PrepareUnitDisappear:
    push {r4, r5, lr}

    @ Get queue length
    ldr r2, =UnitDisappearQueueLen
    ldrb r3, [r2, #0]

    @ Save queue length to s1
    ldr r4, =gEventSlots
    str r3, [r4, #4]

    @ if queue is empty, return immediately
    cmp r3, #0
    beq 1f

    @ Decrement stored queue length
    subs r3, r3, #1
    strb r3, [r2, #0]

    @ Load unit index from queue
    ldr r1, =UnitDisappearQueue
    lsls r3, r3, #1
    ldrh r0, [r1, r3]

    @ Get unit at gUnitLookup[r1]
    ldr r1, =gUnitLookup
    lsls r0, r0, #2
    ldr r1, [r1, r0]

    @ mark as hidden, undeployed, and out of party
    @ (bits 0, 3, 16, 21, and 26)
    ldr r3, =0x04210009
    ldr r2, [r1, #0x0C]
    orrs r2, r2, r3
    str r2, [r1, #0x0C]

    @ Get unit X/Y as halfword
    ldrh r0, [r1, #0x10]

    @ put unit coords in sB
    ldr r5, =0x2C
    strb r0, [r4, r5]

    ldr r5, =0x2E
    lsrs r0, r0, #8
    strb r0, [r4, r5]

    1:
    pop {r4, r5, pc}
THUMB_FUNC_END PrepareUnitDisappear

THUMB_FUNC_START ForceHideAll
ForceHideAll:
    push {r4, r5, r6, lr}

    ldr r0, =gUnitLookup

    movs r1, #0
    movs r6, #0

    1:
    @ get unit at gUnitLookup[r1]
    lsls r2, r1, #2
    ldr r2, [r0, r2]

    @ check if unit pointer is null
    cmp r2, #0
    beq 2f

    @ get character data pointer and check if null
    ldr r3, [r2, #0]
    cmp r3, #0
    beq 2f

    @ get character number
    ldrb r4, [r3, #0x04]

    @ check if character is playable (characters 0x01 - 0x22 inclusive, excluding 0x1B)
    cmp r4, #0
    beq 2f

    cmp r4, #0x1B
    beq 2f

    cmp r4, #0x22
    bhi 2f

    @ Check if player is capable of using unit in-game
    @ (uses US_UNAVAILABLE helper bitflag set from fe8u decompilation)
    ldr r5, [r2, #0x0C]
    ldr r6, =0x0001000C
    ands r5, r5, r6
    cmp r5, #0
    bne 2f

    @ check if character is available according to AP inventory
    ldr r5, =IsCharacterAvailable
    ldrb r5, [r5, r4]
    cmp r5, #0
    bne 2f

    @ Increment queue length
    ldr r5, =UnitDisappearQueueLen
    ldrb r3, [r5, #0]
    lsls r4, r3, #1
    adds r3, r3, #1
    strb r3, [r5, #0]

    @ Store to queue
    ldr r5, =UnitDisappearQueue
    strh r1, [r5, r4]

    movs r6, #1

    @ loop over blue units only
    2:
    adds r1, r1, #1
    cmp r1, #65
    blo 1b

    @ loop over blue, green, and red units
    @ 2:
    @ adds r1, r1, #1
    @ cmp r1, #193
    @ blo 1b

    @ if we enqueued any unit disappearances, call the disappear event
    cmp r6, #0
    beq 3f

    ldr r0, =UnitDisappearEvent
    ldr r1, =3
    bl CallEvent
    
    3:
    pop {r4, r5, r6, pc}
    bx lr
THUMB_FUNC_END ForceHideAll

THUMB_FUNC_START OnTickActiveFactionTurn
OnTickActiveFactionTurn:
    push {lr}

    @ skip if not player phase
    ldr r0, =gRAMChapterData
    ldrb r0, [r0, #0x0F]
    cmp r0, #0x00
    bne 1f

    bl ForceHideAll

    1:
    movs r0, #0
    pop {pc}
THUMB_FUNC_END OnTickActiveFactionTurn
