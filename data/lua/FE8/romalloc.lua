module("romalloc", package.seeall)

local game_data = require("game_data")
local allocations = nil

local function align4(addr)
    return bit.band(addr, 0xFFFFFFFC)
end

local function isAligned4(addr)
    return bit.band(addr, 3) == 0
end

-- always returns 4-aligned addresses
function romalloc(req_size)
    if allocations == nil then
        allocations = {{
            reg_start = game_data.getFreeROMStart(),
            reg_end = 0x0A000000,
            free = true,
        }}
    end

    for i=1, #allocations do
        local region = allocations[i]
        if region.free then
            local reg_size = region.reg_end - region.reg_start
            if reg_size >= req_size then
                local new_reg_start = region.reg_start + req_size
                if not isAligned4(new_reg_start) then
                    new_reg_start = align4(new_reg_start) + 4
                end

                if new_reg_start < region.reg_end then
                    table.insert(allocations, i+1, {
                        reg_start = new_reg_start,
                        reg_end = region.reg_end,
                        free = true,
                    })
                    region.reg_end = new_reg_start
                end
                region.free = false
                return region.reg_start
            end
        end
    end

    console.write(string.format("allocate: could not satisfy request for %u bytes of ROM", req_size))

    return nil
end

function free(req_addr)
    if allocations == nil then
        return
    end

    for i=1, #allocations do
        local region = allocations[i]
        if region.reg_start == req_addr then
            region.free = true

            if i < (#allocations - 1) then
                local nextRegion = allocations[i+1]
                if nextRegion.free then
                    region.reg_end = nextRegion.reg_end
                    table.remove(allocations, i+1)
                end
            end

            if i > 1 then
                local prevRegion = allocations[i-1]
                if prevRegion.free then
                    prevRegion.reg_end = region.reg_end
                    table.remove(allocations, i)
                end
            end

            return
        end
    end

    console.write(string.format("free: failed to deallocate memory at %08x", req_addr))
end

