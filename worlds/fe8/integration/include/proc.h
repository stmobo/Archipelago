/* Taken from fireemblem8u decompilation project */

#ifndef PROC_H
#define PROC_H

struct Proc;

typedef void* ProcPtr;
typedef void(*ProcFunc)(ProcPtr proc);

struct ProcCmd
{
    short opcode;
    short dataImm;
    const void* dataPtr;
};

extern ProcPtr Proc_StartBlocking(const struct ProcCmd *script, ProcPtr parent);
extern void Proc_Goto(ProcPtr proc, int label);
extern ProcPtr Proc_Find(const struct ProcCmd* script);

#define PROC_END                                     { 0x00, 0x0000, 0 }
#define PROC_NAME(aName)                             { 0x01, 0x0000, aName }
#define PROC_CALL(apRoutine)                         { 0x02, 0x0000, (apRoutine) }
#define PROC_REPEAT(apRoutine)                       { 0x03, 0x0000, (apRoutine) }
#define PROC_SET_END_CB(apRoutine)                   { 0x04, 0x0000, (apRoutine) }
#define PROC_START_CHILD(ap6CChild)                  { 0x05, 0x0000, (ap6CChild) }
#define PROC_START_CHILD_BLOCKING(ap6CChild)         { 0x06, 0x0001, (ap6CChild) }
#define PROC_START_MAIN_BUGGED(ap6CMain)             { 0x07, 0x0000, (ap6CMain) }
#define PROC_WHILE_EXISTS(ap6CToCheck)               { 0x08, 0x0000, (ap6CToCheck) }
#define PROC_END_EACH(ap6CToCheck)                   { 0x09, 0x0000, (ap6CToCheck) }
#define PROC_BREAK_EACH(ap6CToCheck)                 { 0x0A, 0x0000, (ap6CToCheck) }
#define PROC_LABEL(aLabelId)                         { 0x0B, aLabelId, 0 }
#define PROC_GOTO(aLabelId)                          { 0x0C, aLabelId, 0 }
#define PROC_JUMP(ap6CCode)                          { 0x0D, 0x0000, (ap6CCode) }
#define PROC_SLEEP(aTime)                            { 0x0E, aTime,  0 }
#define PROC_MARK(aMark)                             { 0x0F, aMark,  0 }
#define PROC_BLOCK                                   { 0x10, 0x0000, 0 }
#define PROC_END_IF_DUPLICATE                        { 0x11, 0x0000, 0 }
#define PROC_SET_BIT4                                { 0x12, 0x0000, 0 }
#define PROC_13                                      { 0x13, 0x0000, 0 }
#define PROC_WHILE(aprRoutine)                       { 0x14, 0x0000, (aprRoutine) }
#define PROC_15                                      { 0x15, 0x0000, 0 }
#define PROC_CALL_2(aprRoutine)                      { 0x16, 0x0000, (aprRoutine) }
#define PROC_END_DUPLICATES                          { 0x17, 0x0000, 0 }
#define PROC_CALL_ARG(aprRoutine, aArgument)         { 0x18, (aArgument), (aprRoutine) }
#define PROC_19                                      { 0x19, 0x0000, 0 }
#define PROC_YIELD                                   PROC_SLEEP(0)


#endif