#ifndef AP_EVENT_H
#define AP_EVENT_H

#include <stddef.h>
#include "proc.h"
#include "types.h"

struct APQueuedEvent {
    u16 *events;
    u8 execType;
    u8 runInWorldMap;
    struct APQueuedEvent *next;
};

volatile struct APQueuedEvent *PPEventQueue;
extern void* gRAMChapterData;

extern u32 gEventSlots[];

extern void EventEngine_Create(const u16* events, u8 execType);
extern void CallEvent(const u16* events, u8 execType);
extern i8 EventEngineExists();

void EnqueueWaitingAPEvents();
void PlayerPhase_MainIdleShim(ProcPtr);
u8 PPEventsRunning(ProcPtr proc);
u8 RunActiveEventRequest(ProcPtr proc);
ProcPtr RequestActiveEvent(ProcPtr parent, u32 request);
void FinishActiveEvent(ProcPtr parent);


#endif