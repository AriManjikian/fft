# Makefile
SIM ?= verilator
TOPLEVEL_LANG ?= verilog

EXTRA_ARGS += \
    --trace \
    --trace-structs \
    --coverage \
    --coverage-line \
    --coverage-toggle

WAVES = 1

VERILOG_SOURCES += $(PWD)/../../src/common/complex_adder.sv
VERILOG_SOURCES += $(PWD)/../../src/common/complex_mult.sv
VERILOG_SOURCES += $(PWD)/../../src/common/sp_bram.sv
VERILOG_SOURCES += $(PWD)/../../src/common/tpd_bram.sv
VERILOG_SOURCES += $(PWD)/../../src/memory_bank/memory_bank.sv
VERILOG_SOURCES += $(PWD)/../../src/memory_bank/memory_bank_wrapper.sv
VERILOG_SOURCES += $(PWD)/../../src/memory_bank/twiddle_rom.sv
VERILOG_SOURCES += $(PWD)/../../src/memory_bank/twiddle_rom_wrapper.sv
VERILOG_SOURCES += $(PWD)/../../src/butterfly/butterfly.sv
VERILOG_SOURCES += $(PWD)/../../src/address_generator/bit_reversal_unit.sv
VERILOG_SOURCES += $(PWD)/../../src/address_generator/agu.sv
VERILOG_SOURCES += $(PWD)/../../src/fft_top.sv
VERILOG_SOURCES += $(PWD)/../../src/fft_pkg.sv

TOPLEVEL = fft_top
MODULE = test_fft

PROJECT_ROOT := $(abspath $(CURDIR)/../..)
PLUSARGS += +BASE_PATH=$(PROJECT_ROOT)/scripts/twiddle_factors
include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: build test run

build:
	$(MAKE) sim

test:
	$(MAKE)

run:
	$(MAKE)
	gtkwave dump.vcd &
