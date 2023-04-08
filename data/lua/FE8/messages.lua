module("messages", package.seeall)

local game_data = require("game_data")
local huffman_start_addr = game_data.getSymbolAddress("gMsgHuffmanTable")
local msgTableData = game_data.getSymbol("gMsgStringTable")
local nMessages = msgTableData.size / 4

local function loadHuffmanNode(addr)
    -- node_addr = table_start_addr + (index * 4)
    local left = memory.read_u16_le(addr)
    local right = memory.read_u16_le(addr + 2)
    if bit.band(right, 0x8000) == 0 then
        return {
            data = nil,
            terminal = false,
            left = loadHuffmanNode(huffman_start_addr + (left * 4)),
            right = loadHuffmanNode(huffman_start_addr + (right * 4))
        }
    elseif left == 0 then
        return {
            data = nil,
            terminal = true
        }
    else
        local data = string.char(bit.band(left, 0xFF))
        if bit.band(bit.rshift(left, 8), 0xFF) ~= 0 then
            data = data .. string.char(bit.band(bit.rshift(left, 8), 0xFF))
        end

        return {
            data = data,
            terminal = false
        }
    end
end

local huffman_root_addr = game_data.getSymbolAddress("gMsgHuffmanTableRootActual")
local huffmanTreeRoot = loadHuffmanNode(huffman_root_addr)

-- zero-indexed, for consistency with game data
function getMessageText(index)
    if (index < 0) or (index >= nMessages) then
        return nil
    end

    local text_ptr = msgTableData.address + (index * 4)
    local cur_addr = memory.read_u32_le(text_ptr)
    local cur_node = huffmanTreeRoot
    local cur_data = ""

    local cur_byte = memory.read_u8(cur_addr)
    local cur_bit = 0
    while true do
        local next_bit = bit.band(cur_byte, 0x01) ~= 0
        cur_byte = bit.rshift(cur_byte, 1)
        cur_bit = cur_bit + 1

        if cur_bit == 8 then
            cur_addr = cur_addr + 1
            cur_byte = memory.read_u8(cur_addr)
            cur_bit = 0
        end

        if next_bit then
            cur_node = cur_node.right
        else
            cur_node = cur_node.left
        end

        if cur_node.terminal then
            return cur_data
        elseif cur_node.data ~= nil then
            cur_data = cur_data .. cur_node.data
            cur_node = huffmanTreeRoot
        end
    end
end
