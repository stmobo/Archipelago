.include "macro.inc"
.syntax unified

.section wram_bss, "aw", %nobits
.global Xorshift128_State

.align 4
DATA_START Xorshift128_State
Xorshift128_State:
Salsa20_State:
.rept 6
.word 0
.endr
DATA_END Xorshift128_State
.rept 10
.word 0
.endr

.section .data
DATA_START Salsa20Constants
.align 4
Salsa20Constants:
    .word 0x61707865
    .word 0x3320646E
    .word 0x79622D32
    .word 0x6B206574
    .word 0x6972614D
DATA_END Salsa20Constants

.text
.thumb

.macro XOR_ADD_ROTR d, a, b, rot
    movs r4, \a
    adds r4, r4, \b
    movs r5, #\rot
    rors r4, r4, r5
    eors \d, \d, r4
.endm

.macro SALSA20_QR a, b, c, d
    ldr r0, [r6, #\a]
    ldr r1, [r6, #\b]
    ldr r2, [r6, #\c]
    ldr r3, [r6, #\d]
    XOR_ADD_ROTR r1, r0, r3, 25
    XOR_ADD_ROTR r2, r1, r0, 23
    XOR_ADD_ROTR r3, r2, r1, 19
    XOR_ADD_ROTR r0, r3, r2, 14
    str r0, [r6, #\a]
    str r1, [r6, #\b]
    str r2, [r6, #\c]
    str r3, [r6, #\d]
.endm

.global DoSalsa20Mixing
THUMB_FUNC_START DoSalsa20Mixing
@ r0 is supposed to be u16[3].
@ This actually performs a Salsa20 mixing step.
DoSalsa20Mixing:
    push {r4, r5, r6, r7}

    @ Set up base addresses:
    ldr r1, =Salsa20_State
    ldr r2, =Salsa20Constants
    b 1f
    .ltorg

    1:
    ldr r3, [r2, #0]
    str r3, [r1, #0]
    ldr r3, [r2, #4]
    str r3, [r1, #20]
    ldr r3, [r2, #8]
    str r3, [r1, #40]
    ldr r3, [r2, #12]
    str r3, [r1, #60]

    @ Set key:
    ldr r4, [r2, #16]
    movs r2, 4
    movs r3, 44
    1:
    str r4, [r1, r2]
    str r4, [r1, r3]
    adds r2, r2, #4
    adds r3, r3, #4
    cmp r2, #20
    blt 1b

    @ Apply nonce and position:
    ldrh r2, [r0, #0]
    str r2, [r1, #24]

    ldrh r2, [r0, #2]
    str r2, [r1, #28]

    ldrh r2, [r0, #4]
    str r2, [r1, #32]

    movs r7, #0
    str r7, [r1, #36]
    movs r6, r1

    @ Perform 4 rounds.
    SALSA20_QR 0, 16, 32, 48
    SALSA20_QR 20, 36, 52, 4
    SALSA20_QR 40, 56, 8, 24
    SALSA20_QR 60, 12, 28, 44

    SALSA20_QR 0, 4, 8, 12
    SALSA20_QR 20, 24, 28, 16
    SALSA20_QR 40, 44, 32, 36
    SALSA20_QR 60, 48, 52, 56

    SALSA20_QR 0, 16, 32, 48
    SALSA20_QR 20, 36, 52, 4
    SALSA20_QR 40, 56, 8, 24
    SALSA20_QR 60, 12, 28, 44

    SALSA20_QR 0, 4, 8, 12
    SALSA20_QR 20, 24, 28, 16
    SALSA20_QR 40, 44, 32, 36
    SALSA20_QR 60, 48, 52, 56

    pop {r4, r5, r6, r7}
    bx lr
THUMB_FUNC_END DoSalsa20Mixing

.global XorshiftInit
THUMB_FUNC_START XorshiftInit
XorshiftInit:
    push {r4, r5}

    ldr r5, =Xorshift128_Init
    ldm r5!, {r0, r1, r2, r3, r4}
    ldr r5, =Xorshift128_State
    stm r5!, {r0, r1, r2, r3, r4}

    movs r0, #0
    str r0, [r5]

    movs r0, #1
    pop {r4, r5}
    bx lr
THUMB_FUNC_END XorshiftInit

.global XorshiftGenerateInternal
THUMB_FUNC_START XorshiftGenerateInternal
XorshiftGenerateInternal:
    push {r4, r5, r6}

    @ store new state[1..4] in r1-r4, t in r0, and the counter in r6.
    @ r1 contains s, aka old state[0].
    ldr r0, =Xorshift128_State
    ldm r0!, {r1, r2, r3, r4}
    ldr r6, [r0, #4]
    ldr r0, [r0]

    lsrs r5, r0, #2
    eors r0, r0, r5
    lsls r5, r0, #1
    eors r0, r0, r5

    lsls r5, r1, #4
    eors r0, r0, r5
    eors r0, r0, r1

    ldr r5, =Xorshift128_State
    stm r5!, {r0, r1, r2, r3, r4}

    ldr r1, =362437
    adds r1, r1, r6
    str r1, [r5]

    adds r0, r0, r1
    lsrs r0, r0, #16

    @ return value in r0
    pop {r4, r5, r6}
    bx lr
THUMB_FUNC_END XorshiftGenerateInternal

.global XorshiftGenerate
THUMB_FUNC_START XorshiftGenerate
XorshiftGenerate:
    push {lr}
    bl XorshiftGenerateInternal
    str r0, [sp, #4]
    movs r0, #1
    pop {pc}
THUMB_FUNC_END XorshiftGenerate


.global XorshiftStore
THUMB_FUNC_START XorshiftStore
@ Unfortunately, callers to StoreRNState can only provide 48 out of 192 bits of storage for RNG state.
XorshiftStore:
    push {r4, lr}

    @ Generate 24 random bits to store as "state".
    ldr r4, [r0]
    bl XorshiftGenerateInternal
    strh r0, [r4, #0]
    bl XorshiftGenerateInternal
    strh r0, [r4, #2]
    bl XorshiftGenerateInternal
    strh r0, [r4, #4]

    @ Use those bits as input to Salsa20 mixing.
    movs r0, r4
    bl DoSalsa20Mixing

    @ Since the RNG states overlap in memory, the xorshift generator should now be seeded.
    movs r0, #1
    pop {r4, pc}
THUMB_FUNC_END XorshiftStore

.global XorshiftLoad
THUMB_FUNC_START XorshiftLoad
XorshiftLoad:
    push {lr}

    @ Pass the nonce and position values on to DoSalsa20Mixing.
    ldr r0, [r0]
    bl DoSalsa20Mixing
    
    movs r0, #1
    pop {pc}
THUMB_FUNC_END XorshiftLoad

