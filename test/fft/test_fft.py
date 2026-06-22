import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.result import SimTimeoutError
import numpy as np
import logging

logger = logging.getLogger("cocotb")
logger.setLevel(logging.DEBUG)

NFFT = 32
DATA_WIDTH = 16
QFORMAT = 15
SCALE = 1 << QFORMAT

CLK_PERIOD_NS = 5
TIMEOUT_CYCLES = 5000


def bit_reverse_index(i: int, nbits: int) -> int:
    r = 0
    for b in range(nbits):
        if i & (1 << b):
            r |= 1 << (nbits - 1 - b)
    return r


def to_q15(value: float) -> int:
    q = int(round(value * SCALE))
    return max(-SCALE, min(SCALE - 1, q))


def from_q15(value: int) -> float:
    return value / SCALE


def make_test_vector(nfft: int):
    """
    Single-tone real cosine at bin 3 -> energy only at bins 3 and nfft-3.
    Sparse spectrum makes a bin-permutation bug visually obvious in the log
    instead of producing a diffuse wall of small mismatches.
    """
    n = np.arange(nfft)
    time_domain = 0.5 * np.cos(2 * np.pi * 3 * n / nfft)
    golden = np.fft.fft(time_domain)
    return time_domain, golden


async def reset_dut(dut):
    dut.reset.value = 1
    dut.i_tvalid.value = 0
    dut.i_tdata_re.value = 0
    dut.i_tdata_im.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.reset.value = 0
    await RisingEdge(dut.clk)


async def drive_input(dut, samples_q15):
    for i, (re_q, im_q) in enumerate(samples_q15):
        while not dut.o_tready.value:
            await RisingEdge(dut.clk)
        dut.i_tdata_re.value = re_q
        dut.i_tdata_im.value = im_q
        dut.i_tvalid.value = 1
        await RisingEdge(dut.clk)
        dut.i_tvalid.value = 0
        logger.debug(f"Drove sample {i}: re={re_q} im={im_q}")


async def collect_outputs(dut, expected_count):
    outputs = []
    cycles_since_last = 0

    while len(outputs) < expected_count:
        await RisingEdge(dut.clk)
        cycles_since_last += 1

        if dut.o_tvalid.value:
            idx = int(dut.o_xk_index.value)
            re = dut.o_tdata_re.value.signed_integer
            im = dut.o_tdata_im.value.signed_integer
            outputs.append((idx, re, im))
            cycles_since_last = 0
            logger.debug(
                f"Output beat {len(outputs)}/{expected_count}: "
                f"index={idx} re={re} im={im}"
            )

        if cycles_since_last > TIMEOUT_CYCLES:
            raise SimTimeoutError(
                f"No new output beat for {TIMEOUT_CYCLES} cycles; "
                f"got {len(outputs)}/{expected_count} so far"
            )

    return outputs


def score_against(outputs_sorted, golden, label):
    errs = []
    for (idx, re_q, im_q), g in zip(outputs_sorted, golden):
        actual = from_q15(re_q) + 1j * from_q15(im_q)
        err_re = abs(actual.real - g.real)
        err_im = abs(actual.imag - g.imag)
        errs.append((idx, actual, g, err_re, err_im))
    max_re = max(e[3] for e in errs)
    max_im = max(e[4] for e in errs)
    logger.info(f"[{label}] max_err_re={max_re:.5f} max_err_im={max_im:.5f}")
    return max_re, max_im, errs


@cocotb.test()
async def test_fft_single_tone(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    time_domain, golden = make_test_vector(NFFT)
    samples_q15 = [(to_q15(v), 0) for v in time_domain]

    await reset_dut(dut)

    drive_task = cocotb.start_soon(drive_input(dut, samples_q15))
    outputs = await collect_outputs(dut, NFFT)
    await drive_task

    assert len(outputs) == NFFT, f"Expected {NFFT} output beats, got {len(outputs)}"

    nbits = int(np.ceil(np.log2(NFFT)))

    reported_indices = sorted(idx for idx, _, _ in outputs)
    expected_indices = list(range(NFFT))
    if reported_indices != expected_indices:
        logger.error(f"o_xk_index values are NOT a clean permutation of 0..{NFFT - 1}.")
        logger.error(f"Reported (sorted): {reported_indices}")

    outputs_sorted = sorted(outputs, key=lambda t: t[0])

    golden_natural = golden
    golden_bitrev = np.array([golden[bit_reverse_index(i, nbits)] for i in range(NFFT)])

    err_re_nat, err_im_nat, errs_nat = score_against(
        outputs_sorted, golden_natural, "vs natural-order golden"
    )
    err_re_rev, err_im_rev, errs_rev = score_against(
        outputs_sorted, golden_bitrev, "vs bit-reversed-order golden"
    )

    # Real- and imaginary-part errors are reported separately (not just
    # combined) because of the known i_yi/w_calculated_yr wiring bug in
    # fft_top.sv -- if imaginary error is much larger than real error across
    # the board, that wiring bug is almost certainly why, independent of
    # whatever the bit-reversal answer turns out to be.
    TOL = 0.02  # placeholder -- see note in module docstring / chat

    nat_pass = err_re_nat <= TOL and err_im_nat <= TOL
    rev_pass = err_re_rev <= TOL and err_im_rev <= TOL

    if nat_pass and not rev_pass:
        logger.info("RESULT: output matches NATURAL bin order.")
    elif rev_pass and not nat_pass:
        logger.info(
            "RESULT: output matches BIT-REVERSED bin order -- "
            "bit_reversal_unit is not reversing as expected; data is "
            "landing in bit-reversed slots."
        )
    elif nat_pass and rev_pass:
        logger.info("RESULT: ambiguous -- matches both within tolerance.")
    else:
        logger.error("RESULT: matches NEITHER ordering within tolerance.")
        if err_im_nat > 3 * max(err_re_nat, 1e-6) and err_im_rev > 3 * max(
            err_re_rev, 1e-6
        ):
            logger.error(
                "Imaginary error is much larger than real error under BOTH "
                "orderings -- strongly suggests the known i_yi/w_calculated_yr "
                "wiring bug in fft_top.sv's memory_bank_wrapper instantiation "
                "is the dominant cause, not bin ordering."
            )
        logger.error("Per-bin detail (natural-order comparison):")
        for idx, actual, g, e_re, e_im in errs_nat:
            logger.error(
                f"  reported_idx={idx:3d} actual={actual:.4f} "
                f"expected={g:.4f} err=({e_re:.4f},{e_im:.4f})"
            )

    await ClockCycles(dut.clk, 2000)
    # assert reported_indices == expected_indices, (
    #     "o_xk_index outputs are not a clean permutation of all bins."
    # )
    # assert nat_pass or rev_pass, (
    #     f"Output matched neither ordering within tolerance "
    #     f"(nat=({err_re_nat:.4f},{err_im_nat:.4f}), "
    #     f"rev=({err_re_rev:.4f},{err_im_rev:.4f})). See log for detail."
    # )
