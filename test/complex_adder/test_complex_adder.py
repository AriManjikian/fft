import cocotb
import random

from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


def rand_signed(width):
    return random.randint(-(1 << (width - 1)), (1 << (width - 1)) - 1)


def wrap_signed(value, width):
    mask = (1 << width) - 1
    value &= mask

    if value & (1 << (width - 1)):
        value -= 1 << width

    return value


@cocotb.test()
async def basic(dut):
    CLK_PERIOD_NS = 10
    cocotb.start_soon(Clock(dut.i_Clk, CLK_PERIOD_NS, unit="ns").start())

    WIDTH_A = int(dut.DATA_WIDTH.value)
    WIDTH_B = int(dut.DATA_WIDTH.value)
    OUT_WIDTH = max(WIDTH_A, WIDTH_B) + 1

    await ClockCycles(dut.i_Clk, 1)

    for _ in range(100):
        ar = rand_signed(WIDTH_A)
        ai = rand_signed(WIDTH_A)
        br = rand_signed(WIDTH_B)
        bi = rand_signed(WIDTH_B)

        dut.i_ar.value = ar
        dut.i_ai.value = ai
        dut.i_br.value = br
        dut.i_bi.value = bi

        await ClockCycles(dut.i_Clk, 1)

        exp_cr = ar + br
        exp_ci = ai + bi

        exp_cr = wrap_signed(exp_cr, OUT_WIDTH)
        exp_ci = wrap_signed(exp_ci, OUT_WIDTH)

        await ClockCycles(dut.i_Clk, 1)

        got_cr = dut.o_cr.value.to_signed()
        got_ci = dut.o_ci.value.to_signed()

        assert got_cr == exp_cr, f"Wrong REAL! Expected ({exp_cr}) got ({got_cr})"

        assert got_ci == exp_ci, f"Wrong IMAG! Expected ({exp_ci}) got ({got_ci})"


@cocotb.test()
async def overflow(dut):
    CLK_PERIOD_NS = 10
    cocotb.start_soon(Clock(dut.i_Clk, CLK_PERIOD_NS, unit="ns").start())

    WIDTH_A = int(dut.DATA_WIDTH.value)
    WIDTH_B = int(dut.DATA_WIDTH.value)
    OUT_WIDTH = max(WIDTH_A, WIDTH_B) + 1

    #
    # Large negative (-1)
    #
    ar = -1
    ai = -1
    br = -1
    bi = -1

    dut.i_ar.value = ar
    dut.i_ai.value = ai
    dut.i_br.value = br
    dut.i_bi.value = bi

    await ClockCycles(dut.i_Clk, 1)

    exp_cr = wrap_signed(ar + br, OUT_WIDTH)
    exp_ci = wrap_signed(ai + bi, OUT_WIDTH)

    await ClockCycles(dut.i_Clk, 1)

    got_cr = dut.o_cr.value.to_signed()
    got_ci = dut.o_ci.value.to_signed()

    assert got_cr == exp_cr, f"Wrong REAL! Expected ({exp_cr}) got ({got_cr})"
    assert got_ci == exp_ci, f"Wrong IMAG! Expected ({exp_ci}) got ({got_ci})"

    #
    # Large positive (01111111 = +127)
    #
    ar = (1 << (WIDTH_A - 1)) - 1
    ai = (1 << (WIDTH_A - 1)) - 1
    br = (1 << (WIDTH_B - 1)) - 1
    bi = (1 << (WIDTH_B - 1)) - 1

    dut.i_ar.value = ar
    dut.i_ai.value = ai
    dut.i_br.value = br
    dut.i_bi.value = bi

    await ClockCycles(dut.i_Clk, 1)

    exp_cr = wrap_signed(ar + br, OUT_WIDTH)
    exp_ci = wrap_signed(ai + bi, OUT_WIDTH)

    await ClockCycles(dut.i_Clk, 1)

    got_cr = dut.o_cr.value.to_signed()
    got_ci = dut.o_ci.value.to_signed()

    assert got_cr == exp_cr, f"Wrong REAL! Expected ({exp_cr}) got ({got_cr})"
    assert got_ci == exp_ci, f"Wrong IMAG! Expected ({exp_ci}) got ({got_ci})"
