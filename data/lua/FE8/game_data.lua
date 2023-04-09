module("game_data", package.seeall)

local descriptorBaseAddress = 0x09000000
local symbolTable = {}
unitLookup = {}
local freeROMStart = 0;

function getSymbol(name)
    return symbolTable[name]
end

function getSymbolAddress(name)
    local data = symbolTable[name]
    if data ~= nil then
        return data.address
    end
end

function getSymbolSize(name)
    local data = symbolTable[name]
    if data ~= nil then
        return data.size
    end
end

function getFreeROMStart()
    return freeROMStart
end

-- Initialize the symbol table
if memory.read_u32_le(descriptorBaseAddress) == 0xDEADC0DE then
    freeROMStart = memory.read_u32_le(descriptorBaseAddress + 0x08)
    local symTableAddress = memory.read_u32_le(descriptorBaseAddress + 0x0C)
    local symTableLength = memory.read_u32_le(descriptorBaseAddress + 0x10)
    local strTableAddress = memory.read_u32_le(descriptorBaseAddress + 0x14)

    for i=0, (symTableLength - 1) do
        local symbolAddr = memory.read_u32_le(symTableAddress + (i * 12))
        local nameAddr = memory.read_u32_le(symTableAddress + 0x04 + (i * 12))
        local symbolSize = memory.read_u32_le(symTableAddress + 0x08 + (i * 12))
        if symbolSize == 0 then
            symbolSize = nil
        end

        local nameLength = memory.read_u16_le(nameAddr)
        local nameBytes = memory.read_bytes_as_array(nameAddr + 2, nameLength)
        local name = ""
        for _, c in ipairs(nameBytes) do
            name = name .. string.char(c)
        end

        symbolTable[name] = {
            address = symbolAddr,
            size = symbolSize
        }
        
        -- if symbolSize ~= nil then
        --     console.writeline(string.format("Loaded symbol %s = %08x (size %u)", name, symbolAddr, symbolSize))
        -- else
        --     console.writeline(string.format("Loaded symbol %s = %08x (unknown size)", name, symbolAddr))
        -- end
    end

    console.writeline(string.format("Loaded %u symbols.", symTableLength))

    -- gUnitLookup is in ROM, so we can just fetch it now
    local lookupPtr = getSymbolAddress("gUnitLookup")
    local nLookupsLoaded = 0
    for i=1, 0x100 do
        local unitPtr = memory.read_u32_le(lookupPtr + ((i - 1) * 4))
        if unitPtr ~= 0 then
            unitLookup[i] = unitPtr
            nLookupsLoaded = nLookupsLoaded + 1
        end
    end

    console.writeline(string.format("Loaded %u unit lookup pointers.", nLookupsLoaded))
else
    console.writeline("ROM doesn't have valid descriptor header?")
end

function getCharacterUnitPtr(characterId)
    for _, unitPtr in pairs(unitLookup) do
        local charPtr = memory.read_u32_le(unitPtr)
        if charPtr ~= 0 then
            local charNum = memory.read_u8(charPtr + 4)
            if charNum == characterId then
                return unitPtr
            end
        end
    end
end

function getAllPlayableCharacterUnits()
    local ret = {}

    for i=1, 62 do
        -- gUnitLookup[0] is always null, so we can skip it
        local unitPtr = unitLookup[i]
        if unitPtr ~= nil then
            local charPtr = memory.read_u32_le(unitPtr)
            if charPtr ~= 0 then
                local charNum = memory.read_u8(charPtr + 4)
                if (charNum > 0) and (charNum ~= 0x1B) and (charNum <= 0x22) then
                    ret[charNum] = unitPtr
                end
            end
        end
    end

    return ret
end

function findProc(scriptAddr)
    local procArray = getSymbolAddress("sProcArray")
    for i=0, 63 do
        local curProcAddr = procArray + (i * 0x6C)
        -- proc script pointer is at +0
        if memory.read_u32_le(curProcAddr) == scriptAddr then
            return curProcAddr
        end
    end

    return nil
end

function canEnqueueEvents()
    local bmProc = getSymbolAddress("gProc_BMapMain")
    local wmProc = getSymbolAddress("gUnknown_08A3EE74")
    local procArray = getSymbolAddress("sProcArray")
    for i=0, 63 do
        local curProcAddr = procArray + (i * 0x6C)
        local scriptAddr = memory.read_u32_le(curProcAddr)
        -- proc script pointer is at +0
        if scriptAddr == bmProc or scriptAddr == wmProc then
            return true
        end
    end

    return false
end

EventBuilder = {}
function EventBuilder:new()
    local o = {
        instructions = {}
    }

    self.__index = self
    local ret = setmetatable(o, self)
    return ret
end

function EventBuilder:push(val, width)
    table.insert(self.instructions, {
        value=val,
        width=width
    })
end

function EventBuilder:push_u8(...)
    for i=1, arg.n do
        table.insert(self.instructions, {
            value=arg[i],
            width=1
        })
    end
end

function EventBuilder:push_u16(...)
    for i=1, arg.n do
        table.insert(self.instructions, {
            value=arg[i],
            width=2
        })
    end
end

function EventBuilder:push_u32(...)
    for i=1, arg.n do
        table.insert(self.instructions, {
            value=arg[i],
            width=4
        })
    end
end

function EventBuilder:size()
    local sz = 0
    for i=1, #self.instructions do
        sz = sz + self.instructions[i].width
    end
    return sz
end

function EventBuilder:write(addr)
    local curAddr = addr
    for i=1, #self.instructions do
        local val = self.instructions[i].value
        local width = self.instructions[i].width
        if width == 1 then
            memory.write_u8(curAddr, val)
            curAddr = curAddr + 1
        elseif width == 2 then
            memory.write_u16_le(curAddr, val)
            curAddr = curAddr + 2
        elseif width == 4 then
            memory.write_u32_le(curAddr, val)
            curAddr = curAddr + 4
        end
    end
end
