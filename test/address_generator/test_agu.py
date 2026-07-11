import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles


def f_mem_addr_A(level_i, index_j, data_depth_log2):
    mask = (1 << data_depth_log2) - 1
    v_addr = (2 * index_j) << level_i
    return (v_addr | (v_addr >> data_depth_log2)) & mask


def f_mem_addr_B(level_i, index_j, data_depth_log2):
    mask = (1 << data_depth_log2) - 1
    v_addr = (2 * index_j + 1) << level_i
    return (v_addr | (v_addr >> data_depth_log2)) & mask


def f_mem_addr_TW(level_i, index_j, data_depth_log2):
    bitmask = 0
    for k in range(data_depth_log2 - 1):
        if k + 1 <= level_i:
            bitmask |= 1 << (data_depth_log2 - 2 - k)
    return index_j & bitmask


def f_mem_addr_BM(level_i, data_depth_log2):
    bitmask = 0
    for k in range(data_depth_log2 - 1):
        if k + 1 <= level_i:
            bitmask |= 1 << (data_depth_log2 - 2 - k)
    return bitmask


async def f_assert_start(dut):
    dut.i_start.value = 1
    await ClockCycles(dut.i_Clk, 1)
    dut.i_start.value = 0


@cocotb.test()
async def test_agu(dut):
    CLK_PERIOD_NS = 10
    cocotb.start_soon(Clock(dut.i_Clk, CLK_PERIOD_NS, unit="ns").start())

    DATA_DEPTH_LOG2 = int(dut.DATA_DEPTH_LOG2.value)

    await f_assert_start(dut)

    await RisingEdge(dut.o_done)

    await ClockCycles(dut.i_Clk, 10)

    await f_assert_start(dut)

    for i in range(DATA_DEPTH_LOG2):
        await RisingEdge(dut.o_wr_en)

        dut._log.info(f"Starting level i={i}")

        for j in range(2 ** (DATA_DEPTH_LOG2 - 1)):
            await ClockCycles(dut.i_Clk, 1)

            tb_expected_A = f_mem_addr_A(i, j, DATA_DEPTH_LOG2)
            tb_expected_B = f_mem_addr_B(i, j, DATA_DEPTH_LOG2)
            tb_expected_TW = f_mem_addr_TW(i, j, DATA_DEPTH_LOG2)

            dut_A = int(dut.o_raddr_mem_a.value)
            dut_B = int(dut.o_raddr_mem_b.value)
            dut_TW = int(dut.o_raddr_twiddle.value)

            dut._log.info(
                f"i={i:1d} j={j:2d} | "
                f"A: DUT={dut_A:2d} REF={tb_expected_A:2d} | "
                f"B: DUT={dut_B:2d} REF={tb_expected_B:2d} | "
                f"TW: DUT={dut_TW:2d} REF={tb_expected_TW:2d}"
            )

            assert dut_A == tb_expected_A
            assert dut_B == tb_expected_B
            assert dut_TW == tb_expected_TW

        if i == DATA_DEPTH_LOG2 - 1:
            assert dut.o_done.value == 1, "FFT DONE NOT ASSERTED"
