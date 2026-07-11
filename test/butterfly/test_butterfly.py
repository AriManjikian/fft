import cocotb
import random
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


def rand(width):
    val = random.getrandbits(width)
    if val & (1 << (width - 1)):
        val -= 1 << width
    return val


def q_mul(a, b, q):
    return (a * b) >> q


def butterfly_model(ar, ai, br, bi, tr, ti, q):
    brtr = (br * tr) >> q
    biti = (bi * ti) >> q
    brti = (br * ti) >> q
    bitr = (bi * tr) >> q

    xr = ar + (brtr - biti)
    xi = ai + (brti + bitr)
    yr = ar + (biti - brtr)
    yi = ai - (brti + bitr)

    xr_half = xr / 2
    xi_half = xi / 2
    yr_half = yr / 2
    yi_half = yi / 2

    return xr_half, xi_half, yr_half, yi_half


@cocotb.test()
async def test_radix2_random(dut):
    CLK_PERIOD_NS = 10
    cocotb.start_soon(Clock(dut.i_Clk, CLK_PERIOD_NS, unit="ns").start())

    DATA_WIDTH = int(dut.DATA_WIDTH.value)
    QFORMAT = int(dut.DATA_FORMAT.value)
    LATENCY = 9

    for _ in range(10):
        ar = rand(DATA_WIDTH)
        ai = rand(DATA_WIDTH)
        br = rand(DATA_WIDTH)
        bi = rand(DATA_WIDTH)
        tr = rand(DATA_WIDTH)
        ti = rand(DATA_WIDTH)

        dut.i_ar.value = ar & ((1 << DATA_WIDTH) - 1)
        dut.i_ai.value = ai & ((1 << DATA_WIDTH) - 1)
        dut.i_br.value = br & ((1 << DATA_WIDTH) - 1)
        dut.i_bi.value = bi & ((1 << DATA_WIDTH) - 1)
        dut.i_tr.value = tr & ((1 << DATA_WIDTH) - 1)
        dut.i_ti.value = ti & ((1 << DATA_WIDTH) - 1)

        await ClockCycles(dut.i_Clk, LATENCY)

        xr, xi, yr, yi = butterfly_model(ar, ai, br, bi, tr, ti, QFORMAT)

        dut_xr = int(dut.o_xr.value.to_signed())
        dut_xi = int(dut.o_xi.value.to_signed())
        dut_yr = int(dut.o_yr.value.to_signed())
        dut_yi = int(dut.o_yi.value.to_signed())

        dut._log.info(f"DUT xr={dut_xr}  REF xr={xr:.1f}")
        dut._log.info(f"DUT xi={dut_xi}  REF xi={xi:.1f}")
        dut._log.info(f"DUT yr={dut_yr}  REF yr={yr:.1f}")
        dut._log.info(f"DUT yi={dut_yi}  REF yi={yi:.1f}")

        assert abs(dut_xr - xr) <= 1.0, f"XR mismatch: DUT={dut_xr} REF={xr:.1f}"
        assert abs(dut_xi - xi) <= 1.0, f"XI mismatch: DUT={dut_xi} REF={xi:.1f}"
        assert abs(dut_yr - yr) <= 1.0, f"YR mismatch: DUT={dut_yr} REF={yr:.1f}"
        assert abs(dut_yi - yi) <= 1.0, f"YI mismatch: DUT={dut_yi} REF={yi:.1f}"
