import cocotb
import random

from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

CLK_PERIOD_NS = 40
LATENCY = 6

G_WIDTH_A = 8
G_WIDTH_B = 8
OUT_WIDTH = G_WIDTH_A + G_WIDTH_B + 1


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
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    await ClockCycles(dut.clk, 1)

    for _ in range(100):
        ar = rand_signed(G_WIDTH_A)
        ai = rand_signed(G_WIDTH_A)
        br = rand_signed(G_WIDTH_B)
        bi = rand_signed(G_WIDTH_B)

        dut.i_ar.value = ar
        dut.i_ai.value = ai
        dut.i_br.value = br
        dut.i_bi.value = bi

        exp_pr = (ar * br) - (ai * bi)
        exp_pi = (ar * bi) + (ai * br)

        exp_pr = wrap_signed(exp_pr, OUT_WIDTH)
        exp_pi = wrap_signed(exp_pi, OUT_WIDTH)

        await ClockCycles(dut.clk, LATENCY)

        got_pr = dut.o_pr.value.to_signed()
        got_pi = dut.o_pi.value.to_signed()

        assert got_pr == exp_pr, f"Wrong REAL! Expected ({exp_pr}) got ({got_pr})"

        assert got_pi == exp_pi, f"Wrong IMAG! Expected ({exp_pi}) got ({got_pi})"


@cocotb.test()
async def overflow(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

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

    await ClockCycles(dut.clk, LATENCY)

    assert dut.o_pr.value.to_signed() == exp_pr
    assert dut.o_pi.value.to_signed() == exp_pi

    #
    # Large positive (01111111 = +127)
    #
    ar = (1 << (G_WIDTH_A - 1)) - 1
    ai = (1 << (G_WIDTH_A - 1)) - 1
    br = (1 << (G_WIDTH_B - 1)) - 1
    bi = (1 << (G_WIDTH_B - 1)) - 1

    dut.i_ar.value = ar
    dut.i_ai.value = ai
    dut.i_br.value = br
    dut.i_bi.value = bi

    exp_pr = wrap_signed((ar * br) - (ai * bi), OUT_WIDTH)
    exp_pi = wrap_signed((ar * bi) + (ai * br), OUT_WIDTH)

    await ClockCycles(dut.clk, LATENCY)

    assert dut.o_pr.value.to_signed() == exp_pr
    assert dut.o_pi.value.to_signed() == exp_pi
