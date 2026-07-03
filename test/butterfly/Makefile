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

VERILOG_SOURCES += $(PWD)/../../src/butterfly/butterfly.sv
VERILOG_SOURCES += $(PWD)/../../src/common/complex_mult.sv
VERILOG_SOURCES += $(PWD)/../../src/common/complex_adder.sv
VERILOG_SOURCES += $(PWD)/../../src/fft_pkg.sv

TOPLEVEL = butterfly
MODULE = test_butterfly

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: build test run

build:
	$(MAKE) sim

test:
	$(MAKE)

run:
	$(MAKE)
	gtkwave dump.vcd &
