.include "macro.inc"
.syntax unified

.data

@ Event used for cleaning up after actively requested events
.global ActiveEventCleanup
.align 4
DATA_START ActiveEventCleanup
ActiveEventCleanup:
.short 0x0D40, 0         @ ASMC FinishActiveEvent
.word FinishActiveEvent  @ ...
.short 0x0120, 0         @ ENDA
DATA_END ActiveEventCleanup

.global DisplayMessageEvent
.align 4
DATA_START DisplayMessageEvent
DisplayMessageEvent:
.short 0x0540, 0xB    @ SETVAL 0xB 0xFFFFFFFF
.word 0xFFFFFFFF      @ ...
.short 0x1A23, 0      @ TUTORIALTEXTBOXSTART
.short 0x1B20, 0x0D4B @ TEXTSHOW 3404
.short 0x1D20, 0      @ TEXTEND
.short 0x1B22, 0      @ REMA
.short 0x0120, 0      @ ENDA
DATA_END DisplayMessageEvent

.global UnitDisappearEvent
.align 4
DATA_START UnitDisappearEvent
UnitDisappearEvent:
.short 0x0D40, 0            @ ASMC PrepareUnitDisappear
.word PrepareUnitDisappear  @ ...
.short 0x0C40, 1, 1, 0      @ BEQ 1 s1 s0
.short 0x4120, 0xFFFE       @ WARPOUT sB
.short 0x412F, 0            @ WARPEND
.short 0x0A40, 0            @ CALL UnitDisappearEvent
.word UnitDisappearEvent    @ ...
.short 0x0820, 1            @ LABEL 1
.short 0x0120, 0            @ ENDA
DATA_END UnitDisappearEvent
