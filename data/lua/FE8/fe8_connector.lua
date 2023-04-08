local net = require("net")
local messages = require("messages")
local game_data = require("game_data")
local rm = require("romalloc")

local playerPhaseEventAllocs = {};
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
        for i=1, #playerPhaseEventAllocs do
            rm.free(playerPhaseEventAllocs[i])
        end
        playerPhaseEventAllocs = {}
    end

    if (readU32Symbol("ActiveEventRequest") == 0) and (readU32Symbol("ActiveEventResponse") == 0) and (#activeEventAllocs > 0) then
        for i=1, #activeEventAllocs do
            rm.free(activeEventAllocs[i])
        end
        activeEventAllocs = {}
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

local function handleClient(client)
    while true do
        local packetType, payload, err = client:readPacket()

        if err then
            return err
        end

        if packetType == 1 then
            local curChapter = readU8Symbol("gRAMChapterData", 0x0E)
            local availSymName = "BaseAvailabilityCh" .. tostring(curChapter)
            local id = net.unpackBinaryString("4", payload)

            if game_data.getSymbolAddress(availSymName) ~= nil then
                -- Sync unlocked characters
                for i=1, 0x22 do
                    local prevAvailable = (readU8Symbol("IsCharacterAvailable", charId) ~= 0)
                    local nowAvailable = (string.byte(payload, 4 + i) == 0)
                    local prevRecruited = (
                        readU8Symbol(availSymName, i) == 1
                    )
                    writeU8Symbol("IsCharacterAvailable", string.byte(payload, 4 + i), i)

                    if prevRecruited and nowAvailable and not prevAvailable then
                        local evtAddr = setupAppearEvent(charId)
                        enqueuePlayerPhaseEvent(evtAddr, 3, true)
                    end
                end
            else
                console.write(string.format("could not find availability map for ch %02X\n", curChapter))
            end
            
            client:writePacket(1, net.packBinaryString("41", id, 1))
        elseif packetType == 2 then
            -- Respond to active event request
            local id, nEvents = net.unpackBinaryString("41", string.sub(payload, 1, 5))
            if not awaitingActiveEvent then
                client:writePacket(1, net.packBinaryString("41", id, 0) .. "no active event requests pending")
                return
            end

            if nEvents == 0 then
                enqueueActiveResponseEvent(0, 3, false)
            else
                for i=1, nEvents do
                    local startIdx = 6 + ((i - 1) * 2)
                    local charId = net.unpackBinaryString("2", string.sub(payload, startIdx, startIdx + 2))
                    local textIdx = readU16Symbol("UnitSentTextIds", (charId * 2))
                    local evtAddr = setupTextboxEvent(textIdx)
                    enqueueActiveResponseEvent(evtAddr, 3, false)
                end
            end

            awaitingActiveEvent = false
            client:writePacket(1, net.packBinaryString("41", id, 1))
        end
    end
end

net.initServer(handleClient)

local function handleActiveEventRequests()
    if awaitingActiveEvent then
        return
    end

    local evtReq = readU32Symbol("ActiveEventRequest")
    if evtReq ~= 0 then
        net.sendToAllClients(2, net.packBinaryString("4", evtReq))
        awaitingActiveEvent = true
        writeU32Symbol("ActiveEventRequest", 0)
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
