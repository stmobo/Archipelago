local net = require("net")
local messages = require("messages")
local game_data = require("game_data")
local rm = require("romalloc")

local playerPhaseEventAllocs = {};
local queuedAppearEvents = {};
local queuedDisappearEvents = {};
local activeEventAllocs = {};
local awaitingActiveEvent = false;

local function readU32Symbol(symbol, offset)
    local addr = game_data.getSymbolAddress(symbol)
    if offset ~= nil then
        addr = addr + offset
    end
    return memory.read_u32_le(addr)
end

local function readU16Symbol(symbol, offset)
    local addr = game_data.getSymbolAddress(symbol)
    if offset ~= nil then
        addr = addr + offset
    end
    return memory.read_u16_le(addr)
end

local function readU8Symbol(symbol, offset)
    local addr = game_data.getSymbolAddress(symbol)
    if offset ~= nil then
        addr = addr + offset
    end
    return memory.read_u8(addr)
end

local function writeU32Symbol(symbol, value, offset)
    local addr = game_data.getSymbolAddress(symbol)
    if offset ~= nil then
        addr = addr + offset
    end
    return memory.write_u32_le(addr, value)
end

local function writeU16Symbol(symbol, value, offset)
    local addr = game_data.getSymbolAddress(symbol)
    if offset ~= nil then
        addr = addr + offset
    end
    return memory.write_u16_le(addr, value)
end

local function writeU8Symbol(symbol, value, offset)
    local addr = game_data.getSymbolAddress(symbol)
    if offset ~= nil then
        addr = addr + offset
    end
    return memory.write_u8(addr, value)
end

local function cleanupEventAllocs()
    if (readU32Symbol("PPEventQueue") == 0) and (readU8Symbol("PPEventActiveFlag") == 0) and (#playerPhaseEventAllocs > 0) then
        console.write("All player-phase events cleared.\n")
        for i=1, #playerPhaseEventAllocs do
            rm.free(playerPhaseEventAllocs[i])
        end
        playerPhaseEventAllocs = {}
        queuedAppearEvents = {}
    end

    if (readU32Symbol("ActiveEventRequest") == 0) and (readU32Symbol("ActiveEventType") == 0) and (readU32Symbol("ActiveEventResponse") == 0) and (#activeEventAllocs > 0) then
        console.write("All active request events cleared.\n")
        for i=1, #activeEventAllocs do
            rm.free(activeEventAllocs[i])
        end
        activeEventAllocs = {}
        queuedDisappearEvents = {}
    end
end

local function setupEventQueueEntry(eventAddr, execType, runInWorldMap)
    local entryAddr = rm.romalloc(12)
    if entryAddr == nil then
        return
    end
    
    memory.write_u32_le(entryAddr, eventAddr)
    memory.write_u8(entryAddr+4, bit.band(execType, 0xFF))
    if runInWorldMap then
        memory.write_u8(entryAddr+5, 1)
    else
        memory.write_u8(entryAddr+5, 0)
    end
    memory.write_u8(entryAddr+6, 0)
    memory.write_u8(entryAddr+7, 0)
    memory.write_u32_le(entryAddr+8, 0)

    return entryAddr
end

local function enqueuePlayerPhaseEvent(eventAddr, execType, runInWorldMap)
    local entryAddr = setupEventQueueEntry(eventAddr, execType, runInWorldMap)
    table.insert(playerPhaseEventAllocs, entryAddr)
    if eventAddr ~= 0 then
        table.insert(playerPhaseEventAllocs, eventAddr)
    end

    local curAddr = game_data.getSymbolAddress("PPEventQueue")
    while true do
        local nextAddr = memory.read_u32_le(curAddr)
        if nextAddr == 0 then
            memory.write_u32_le(curAddr, entryAddr)
            console.write(string.format("enqueued new event entry at %08x (in ptr %08x)\n", entryAddr, curAddr))
            return
        else
            curAddr = nextAddr + 8
        end
    end
end

local function enqueueActiveResponseEvent(eventAddr, execType, runInWorldMap)
    local entryAddr = setupEventQueueEntry(eventAddr, execType, runInWorldMap)
    table.insert(activeEventAllocs, entryAddr)
    if eventAddr ~= 0 then
        table.insert(activeEventAllocs, eventAddr)
    end

    local curAddr = game_data.getSymbolAddress("ActiveEventResponse")
    while true do
        local nextAddr = memory.read_u32_le(curAddr)
        if nextAddr == 0 then
            memory.write_u32_le(curAddr, entryAddr)
            console.write(string.format("enqueued new active event entry at %08x (in ptr %08x)\n", entryAddr, curAddr))
            return
        else
            curAddr = nextAddr + 8
        end
    end
end


local function setupTextboxEvent(textId)
    local builder = game_data.EventBuilder:new()

    -- EVBIT_MODIFY 3
    builder:push_u16(0x1020, 3)
    -- SETVAL sB 0xFFFFFFFF
    builder:push_u16(0x0540, 0xB)
    builder:push_u32(0xFFFFFFFF)
    -- TUTORIALTEXTBOXSTART
    builder:push_u16(0x1A23, 0)
    -- TEXTSHOW textId
    builder:push_u16(0x1B20, textId)
    -- TEXTEND
    builder:push_u16(0x1D20, 0)
    -- REMA
    builder:push_u16(0x1B22, 0)
    -- EVBIT_T 7
    builder:push_u16(0x0228, 7)
    -- ENDA
    builder:push_u16(0x0120, 0)

    local eventAddr = rm.romalloc(builder:size())
    if eventAddr == nil then
        return
    end

    builder:write(eventAddr)

    return eventAddr
end

local function setupAppearEvent(charId)
    local asmcAddr = game_data.getSymbolAddress("ASMCPrepareUnitAppearEffect")
    local builder = game_data.EventBuilder:new()

    -- EVBIT_MODIFY 3
    builder:push_u16(0x1020, 3)
    -- SETVAL s1 charId
    builder:push_u16(0x0540, 1)
    builder:push_u32(charId)
    -- ASMC ...
    builder:push_u16(0x0D40, 0)
    builder:push_u32(bit.bor(asmcAddr, 1))
    -- SETVAL s3 2
    builder:push_u16(0x0540, 3)
    builder:push_u32(2)
    -- BEQ 1 s1 s0
    builder:push_u16(0x0C40, 1, 1, 0)
    -- BEQ 2 s1 s3
    builder:push_u16(0x0C40, 2, 1, 3)
    -- WARPIN sB
    builder:push_u16(0x4121, 0xFFFE)
    -- WARPEND
    builder:push_u16(0x412F, 0)
    -- GOTO 1
    builder:push_u16(0x0920, 1)
    
    -- LABEL 2
    builder:push_u16(0x0820, 2)
    -- SETVAL sB 0xFFFFFFFF
    builder:push_u16(0x0540, 0xB)
    builder:push_u32(0xFFFFFFFF)
    -- TUTORIALTEXTBOXSTART
    builder:push_u16(0x1A23, 0)
    -- TEXTSHOW s2
    builder:push_u16(0x1B20, 0xFFFF)
    -- TEXTEND
    builder:push_u16(0x1D20, 0)
    -- REMA
    builder:push_u16(0x1B22, 0)

    -- LABEL 1
    builder:push_u16(0x0820, 1)
    -- EVBIT_T 7
    builder:push_u16(0x0228, 7)
    -- ENDA
    builder:push_u16(0x0120, 0)

    local eventAddr = rm.romalloc(builder:size())
    if eventAddr == nil then
        return
    end

    builder:write(eventAddr)

    return eventAddr
end

local function setupUnitDisappearEvent(charId)
    local asmcAddr = game_data.getSymbolAddress("ASMCPrepareUnitDisappearEffect")
    local builder = game_data.EventBuilder:new()

    -- EVBIT_MODIFY 3
    builder:push_u16(0x1020, 3)
    -- SETVAL s1 charId
    builder:push_u16(0x0540, 1)
    builder:push_u32(charId)
    -- ASMC ...
    builder:push_u16(0x0D40, 0)
    builder:push_u32(bit.bor(asmcAddr, 1))
    -- EVBIT_T 7
    builder:push_u16(0x0228, 7)
    -- ENDA
    builder:push_u16(0x0120, 0)

    local eventAddr = rm.romalloc(builder:size())
    if eventAddr == nil then
        return
    end

    builder:write(eventAddr)

    return eventAddr
end

local function setupGameOverEvent()
    local asmcAddr = game_data.getSymbolAddress("ASMCTriggerGameOver")
    local builder = game_data.EventBuilder:new()

    -- EVBIT_MODIFY 3
    builder:push_u16(0x1020, 3)
    -- ASMC ...
    builder:push_u16(0x0D40, 0)
    builder:push_u32(bit.bor(asmcAddr, 1))
    -- EVBIT_T 7
    builder:push_u16(0x0228, 7)
    -- ENDA
    builder:push_u16(0x0120, 0)

    local eventAddr = rm.romalloc(builder:size())
    if eventAddr == nil then
        return
    end

    builder:write(eventAddr)

    return eventAddr
end


local function handleClient(client)
    while true do
        local packetType, payload, err = client:readPacket()

        if err then
            return err
        end

        if packetType == 1 then
            local curChapter = readU8Symbol("gRAMChapterData", 0x0E)
            local id = net.unpackBinaryString("4", payload)
            local unitPointers = {}


            -- Make sure we're in a context where enqueuing events makes sense.
            if game_data.canEnqueueEvents() then
                for _, unitPtr in pairs(game_data.unitLookup) do
                    local charPtr = memory.read_u32_le(unitPtr)
                    if charPtr ~= 0 then
                        local charNum = memory.read_u8(charPtr + 4)
                        if unitPointers[charNum] == nil then
                            unitPointers[charNum] = {}
                        end
                        table.insert(unitPointers[charNum], unitPtr)
                    end
                end

                local availSymAddr = game_data.getSymbolAddress("IsCharacterAvailable")
                local prevAvailStatus = memory.read_bytes_as_array(availSymAddr + 1, 0x22)
                local newAvailStatus = {string.byte(payload, 5, 0x26)}
                local eventsActive = game_data.eventEngineRunning()
                memory.write_bytes_as_array(availSymAddr + 1, newAvailStatus)

                -- Sync unlocked characters
                for i=1, 0x22 do
                    -- Skip sync for characters who already have an appearance event queued
                    if queuedAppearEvents[i] == nil then
                        local unitPtrList = unitPointers[i]
                        if unitPtrList ~= nil and #unitPtrList > 0 then
                            for j=1,#unitPtrList do
                                local unitPtr = unitPtrList[j]
                                if newAvailStatus[i] ~= 0 then
                                    -- Check if unit was previously REMU'd.
                                    local unitStatus = memory.read_u32_le(unitPtr + 0x0C)
                                    local unitRemoved = (bit.band(unitStatus, 0x04010000) ~= 0)
                                    
                                    if unitRemoved and not (
                                        ((i == 0x01) and (curChapter == 0x3E or (curChapter >= 0x17 and curChapter <= 0x1C))) or
                                        ((i == 0x0F) and (curChapter == 0x3D or (curChapter >= 0x0A and curChapter <= 0x0F)))
                                    ) and (queuedAppearEvents[i] == nil) then
                                        local evtAddr = setupAppearEvent(i)
                                        enqueuePlayerPhaseEvent(evtAddr, 3, true)
                                        queuedAppearEvents[i] = evtAddr
                                    end
                                elseif not (awaitingActiveEvent or (#activeEventAllocs > 0) or (queuedDisappearEvents[i] ~= nil) or eventsActive) then
                                    -- Make sure unit is properly REMU'd.
                                    local unitStatus = memory.read_u32_le(unitPtr + 0x0C)
                                    memory.write_u32_le(unitPtr + 0x0C, bit.bor(unitStatus, 0x04210009))
                                end
                            end
                        elseif newAvailStatus[i] ~= 0 and prevAvailStatus[i] == 0 then
                            -- Unit was not previously available but also doesn't have a unit pointer yet.
                            -- Enqueue a text box event for them.
                            local textIdx = readU16Symbol("UnitReceivedTextIds", (i * 2))
                            local evtAddr = setupTextboxEvent(textIdx)
                            enqueuePlayerPhaseEvent(evtAddr, 3, true)
                            queuedAppearEvents[i] = evtAddr
                        end
                    end
                end
            end
            
            client:writePacket(1, net.packBinaryString("41", id, 1))
        elseif packetType == 2 then
            -- Respond to active event request
            local id, nEvents = net.unpackBinaryString("41", string.sub(payload, 1, 5))
            if not awaitingActiveEvent then
                client:writePacket(1, net.packBinaryString("41", id, 0) .. "no active event requests pending")
            else
                if nEvents == 0 then
                    enqueueActiveResponseEvent(0, 3, false)
                else
                    for i=1, nEvents do
                        local startIdx = 6 + ((i - 1) * 2)
                        local charId = net.unpackBinaryString("2", string.sub(payload, startIdx, startIdx + 2))
                        local textIdx = readU16Symbol("UnitSentTextIds", (charId * 2))
                        local evtAddr = setupTextboxEvent(textIdx)
                        queuedDisappearEvents[charId] = evtAddr
                        enqueueActiveResponseEvent(evtAddr, 3, false)
                    end
                end

                awaitingActiveEvent = false
                client:writePacket(1, net.packBinaryString("41", id, 1))
            end
        elseif packetType == 3 then
            -- Trigger game over
            local id = net.unpackBinaryString("4", payload)
            local evtAddr = setupGameOverEvent()
            enqueuePlayerPhaseEvent(evtAddr, 3, false)
            client:writePacket(1, net.packBinaryString("41", id, 1))
        end
    end
end

net.initServer(handleClient)

local function handleActiveEventRequests()
    if awaitingActiveEvent then
        return
    end

    local evtType = readU32Symbol("ActiveEventType")
    local evtReq = readU32Symbol("ActiveEventRequest")
    if evtType == 1 then
        -- Character recruit event
        net.sendToAllClients(2, net.packBinaryString("4", evtReq))
        awaitingActiveEvent = true
        writeU32Symbol("ActiveEventRequest", 0)
        writeU32Symbol("ActiveEventType", 0)
    elseif evtType == 2 then
        -- Victory event
        net.sendToAllClients(3, net.packBinaryString("4", evtReq))
        enqueueActiveResponseEvent(0, 3, false)
        writeU32Symbol("ActiveEventRequest", 0)
        writeU32Symbol("ActiveEventType", 0)
    elseif evtType == 3 then
        -- Game over event
        local nDead = 0
        local deadChars = ""

        for _, unitPtr in pairs(game_data.unitLookup) do
            local charPtr = memory.read_u32_le(unitPtr)
            if charPtr ~= 0 then
                local state = memory.read_u32_le(unitPtr + 0x0C)
                local charNum = memory.read_u8(charPtr + 4)
                if charNum < 0x23 and bit.band(state, 0x04) ~= 0 then
                    deadChars = deadChars .. string.char(charNum)
                    nDead = nDead + 1
                end
            end
        end

        net.sendToAllClients(4, net.packBinaryString("42", evtReq, nDead) .. deadChars)
        enqueueActiveResponseEvent(0, 3, false)
        writeU32Symbol("ActiveEventRequest", 0)
        writeU32Symbol("ActiveEventType", 0)
    end
end

local nFrames = 0
while true do
    cleanupEventAllocs()
    handleActiveEventRequests()

    -- Send keepalive packets every second
    nFrames = nFrames + 1
    if nFrames >= 60 then
        nFrames = 0
        net.sendToAllClients(0, "")
    end

    net.pollSockets()
    emu.frameadvance()
end
