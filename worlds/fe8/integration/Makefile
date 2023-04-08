SHELL = /bin/bash
.SHELLFLAGS = -o pipefail -c

BIN_DIR := bin
SRC_DIR := .
INCLUDE_DIR := $(SRC_DIR)/include

CC := arm-none-eabi-gcc
AS := arm-none-eabi-as
LD := arm-none-eabi-ld
CCFLAGS := -I $(INCLUDE_DIR) -c -O3 -ffreestanding -mcpu=arm7tdmi -mthumb-interwork -mabi=aapcs -mthumb
ASFLAGS := -I $(INCLUDE_DIR) -mcpu=arm7tdmi -mthumb-interwork

C_OBJS := ap_event.o save_data.o
ASM_OBJS := event_data.o undeploy_all.o xorshift.o

INCLUDES := $(wildcard $(INCLUDE_DIR)/*.h)
C_OBJS := $(addprefix $(BIN_DIR)/, $(C_OBJS))
ASM_OBJS := $(addprefix $(BIN_DIR)/, $(ASM_OBJS))

base-symbols.json: extract_elf_data.py fireemblem8-relocs.elf
	python3.9 extract_elf_data.py fireemblem8-relocs.elf | jq > base-symbols.json

bin/archipelago.o: $(C_OBJS) $(ASM_OBJS) $(INCLUDES)
	$(LD) -r -o bin/archipelago.o $(C_OBJS) $(ASM_OBJS)

$(ASM_OBJS): $(BIN_DIR)/%.o: $(SRC_DIR)/%.S $(INCLUDE_DIR)/macro.inc
	$(AS) $(ASFLAGS) -o $@ $<

$(C_OBJS): $(BIN_DIR)/%.o: $(SRC_DIR)/%.c $(INCLUDES)
	$(CC) $(CCFLAGS) -o $@ $<

