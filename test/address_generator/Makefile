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

VERILOG_SOURCES += $(PWD)/../../src/fft_pkg.sv
VERILOG_SOURCES += $(PWD)/../../src/address_generator/agu.sv

TOPLEVEL = agu
MODULE = test_agu

include $(shell cocotb-config  --makefiles)/Makefile.sim

.PHONY: build test run

build:
	$(MAKE) sim

test:
	$(MAKE)

run:
	$(MAKE)
	gtkwave dump.vcd &
