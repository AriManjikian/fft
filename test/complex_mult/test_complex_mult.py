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

    WIDTH_A = int(dut.DATA_WIDTH_A.value)
    WIDTH_B = int(dut.DATA_WIDTH_B.value)
    OUT_WIDTH = WIDTH_A + WIDTH_B + 1
    LATENCY = 6

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

        exp_pr = (ar * br) - (ai * bi)
        exp_pi = (ar * bi) + (ai * br)

        exp_pr = wrap_signed(exp_pr, OUT_WIDTH)
        exp_pi = wrap_signed(exp_pi, OUT_WIDTH)

        await ClockCycles(dut.i_Clk, LATENCY)

        got_pr = dut.o_pr.value.to_signed()
        got_pi = dut.o_pi.value.to_signed()

        assert got_pr == exp_pr, f"Wrong REAL! Expected ({exp_pr}) got ({got_pr})"

        assert got_pi == exp_pi, f"Wrong IMAG! Expected ({exp_pi}) got ({got_pi})"


@cocotb.test()
async def overflow(dut):
    CLK_PERIOD_NS = 10
    cocotb.start_soon(Clock(dut.i_Clk, CLK_PERIOD_NS, unit="ns").start())

    WIDTH_A = int(dut.DATA_WIDTH_A.value)
    WIDTH_B = int(dut.DATA_WIDTH_B.value)
    OUT_WIDTH = WIDTH_A + WIDTH_B + 1
    LATENCY = 6

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

    exp_pr = wrap_signed((ar * br) - (ai * bi), OUT_WIDTH)
    exp_pi = wrap_signed((ar * bi) + (ai * br), OUT_WIDTH)

    await ClockCycles(dut.i_Clk, LATENCY)

    assert dut.o_pr.value.to_signed() == exp_pr
    assert dut.o_pi.value.to_signed() == exp_pi

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

    exp_pr = wrap_signed((ar * br) - (ai * bi), OUT_WIDTH)
    exp_pi = wrap_signed((ar * bi) + (ai * br), OUT_WIDTH)

    await ClockCycles(dut.i_Clk, LATENCY)

    assert dut.o_pr.value.to_signed() == exp_pr
    assert dut.o_pi.value.to_signed() == exp_pi
