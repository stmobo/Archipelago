
.macro THUMB_FUNC_START label
.align 2, 0
.thumb
.thumb_func
.type \label, function
.endm

.macro THUMB_FUNC_END label
.size \label, .-\label
.endm

.macro DATA_START label
.type \label, object
.endm

.macro DATA_END label
.size \label, .-\label
.endm


