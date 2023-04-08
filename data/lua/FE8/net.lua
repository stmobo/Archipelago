module("net", package.seeall)

local game_data = require("game_data")
local socket = require("socket")
local serverSock = nil
local clientHandler = nil
local connectedClients = {} -- Keyed by socket objects
local waiting = false

function packBinaryString(fmt, ...)
    local ret = ""
    for i=1, #fmt do
        local nBytes = tonumber(fmt:sub(i, i), 16)
        local curVal = arg[i]
        for j=1, nBytes do
            ret = ret .. string.char(bit.band(bit.rshift(curVal, (nBytes - j) * 8), 0xFF))
        end
    end
    return ret
end

function unpackBinaryString(fmt, s)
    local ret = {}
    local curOffset = 1
    for i=1, #fmt do
        local nBytes = tonumber(fmt:sub(i, i), 16)
        local curVal = 0
        for j=1, nBytes do
            curVal = bit.bor(bit.lshift(curVal, 8), string.byte(s, curOffset))
            curOffset = curOffset + 1
        end
        table.insert(ret, curVal)
    end
    return unpack(ret)
end

function initServer(handler)
    local portAddr = game_data.getSymbolAddress("APConnectorPort")
    local bindPort = memory.read_u16_le(portAddr)

    serverSock, err = socket.bind('localhost', bindPort)
    if serverSock then
        serverSock:settimeout(0)
        local ip, port = serverSock:getsockname()
        console.writeline("Server started on " .. ip .. ":" .. port)
        clientHandler = handler
    else
        console.writeline("Could not bind server: " .. error)
    end
end

event.onexit(function()
    if serverSock ~= nil then
        serverSock:close()
    end

    for clientSock, client in pairs(connectedClients) do
        clientSock:close()
    end
end)

function pollSockets()
    local newSocket, err = serverSock:accept()
    if newSocket then
        console.writeline("Accepted connection from " .. newSocket:getpeername())

        local newClient = Client:new(newSocket)
        connectedClients[newSocket] = newClient
        
        local newCo = coroutine.create(clientHandler)
        resumeCoroutineAndCheck(newCo, newClient)
    end

    for clientSock, client in pairs(connectedClients) do
        if client:wantsRead() then
            client:pollRead()
        end

        if client:wantsWrite() then
            client:pollWrite()
        end
    end
end

function sendToAllClients(packetType, data)
    for _, client in pairs(connectedClients) do
        client:writePacket(packetType, data)
    end
end

function resumeCoroutineAndCheck(co, ...)
    local ret = {coroutine.resume(co, unpack(arg))}
    local status = table.remove(ret, 1)
    if status then
        return unpack(ret)
    else
        console.writeline("coroutine returned error: " .. tostring(ret[1]))
        return nil, ret[1]
    end
end

Client = {}
function Client:new(clientSock)
    local o = {
        socket = clientSock,
        readBuf = "",
        writeBuf = "",
        waitingReaders = {},
        waitingWriters = {}
    }

    self.__index = self
    clientSock:settimeout(0)
    
    local ret = setmetatable(o, self)
    return ret
end

function Client:wantsRead()
    return #self.waitingReaders > 0
end

function Client:wantsWrite()
    return #self.writeBuf > 0
end

function Client:read(maxLen)
    if #self.readBuf > 0 then
        local data = ""

        if (maxLen ~= nil) and (#self.readBuf > maxLen) then
            data = string.sub(self.readBuf, 1, maxLen)
            self.readBuf = string.sub(self.readBuf, #data + 1)
        else
            data = self.readBuf
            self.readBuf = ""
        end

        return data, nil
    else
        local curCo = coroutine.running()
    
        table.insert(self.waitingReaders, {
            maxLen = maxLen,
            co = curCo
        })
    
        return coroutine.yield()
    end
end

function Client:readExact(len)
    local buf = ""

    while #buf < len do
        local data, err = self:read(len - #buf)

        if data then
            buf = buf .. data
        else
            return nil, err
        end
    end

    return buf, nil
end

function Client:write(data)
    self.writeBuf = self.writeBuf .. data
end

function Client:flush()
    local curCo = coroutine.running()
    table.insert(self.waitingWriters, {
        remaining = #self.writeBuf,
        co = curCo
    })

    return coroutine.yield()
end

function Client:close()
    connectedClients[self.socket] = nil
    self.socket:close()

    for _, reader in ipairs(self.waitingReaders) do
        resumeCoroutineAndCheck(reader.co, nil, "closed")
    end

    for _, writer in ipairs(self.waitingWriters) do
        resumeCoroutineAndCheck(writer.co, nil, "closed")
    end

    self.waitingReaders = {}
    self.waitingWriters = {}
end

function Client:writePacket(packetType, data)
    local packed = packBinaryString("44", #data, packetType) .. data
    self:write(packed)
end

function Client:readPacket()
    local header, err = self:readExact(8)

    if header == nil then
        return nil, nil, err
    end

    local len, packetType = unpackBinaryString("44", header)
    local payload, err = self:readExact(len)
    if payload == nil then
        return nil, err
    end

    return packetType, payload, nil
end

function Client:pollRead(maxReadCalls)
    if maxReadCalls == nil then
        maxReadCalls = 1
    end

    local i = 0
    while (i < maxReadCalls) or (maxReadCalls == 0) do
        local data, err, partial = self.socket:receive(1024)
        if (data == nil) and (err ~= 'timeout') then
            if #self.waitingReaders > 0 then
                local reader = table.remove(self.waitingReaders, 1)
                resumeCoroutineAndCheck(reader.co, nil, err)
            end

            return nil, err
        end
        
        data = data or partial
        if (data == nil) or (#data == 0) then
            break
        end

        self.readBuf = self.readBuf .. data
        i = i + 1
    end

    while (#self.waitingReaders > 0) and (#self.readBuf > 0) do
        local reader = table.remove(self.waitingReaders, 1)
        if (reader.maxLen ~= nil) and (reader.maxLen ~= 0) then
            local data = string.sub(self.readBuf, 1, reader.maxLen)
            self.readBuf = string.sub(self.readBuf, #data + 1)
            resumeCoroutineAndCheck(reader.co, data, nil)
        else
            local data = self.readBuf
            self.readBuf = ""
            resumeCoroutineAndCheck(reader.co, data, nil)
            break
        end
    end

    return true, nil
end

function Client:pollWrite()
    local nWritten, err, partial = self.socket:send(self.writeBuf)
    if (not nWritten) and (err ~= 'timeout') then
        if #self.waitingWriters > 0 then
            local writer = table.remove(self.waitingWriters, 1)
            resumeCoroutineAndCheck(writer.co, nil, err)
        end

        return nil, err
    end

    nWritten = nWritten or partial
    self.writeBuf = string.sub(self.writeBuf, nWritten + 1)

    while (#self.waitingWriters > 0) and (nWritten > 0) do
        local writer = self.waitingWriters[1]
        if writer.remaining <= nWritten then
            table.remove(self.waitingWriters, 1)
            nWritten = nWritten - writer.remaining
            resumeCoroutineAndCheck(writer.co, true, nil)
        else
            writer.remaining = writer.remaining - nWritten
            break
        end
    end

    return true, nil
end

