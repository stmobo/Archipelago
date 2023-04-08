#ifndef TYPES_H
#define TYPES_H

#include <stdint.h>

#ifdef __GNUC__
#define CONST_DATA __attribute__((section(".data")))
#else
#define CONST_DATA
#endif

#define ABS(aValue) ((aValue) >= 0 ? (aValue) : -(aValue))
#define RECT_DISTANCE(aXA, aYA, aXB, aYB) (ABS((aXA) - (aXB)) + ABS((aYA) - (aYB)))

typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t u8;
typedef int32_t i32;
typedef int16_t i16;
typedef int8_t i8;

struct Vec2 { i16 x, y; };

typedef struct ShimRegisters
{
    u32 r0;
    u32 r1;
    u32 r2;
    u32 r3;
} ShimRegisters;

#endif