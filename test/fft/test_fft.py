import logging
import os
import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.result import SimTimeoutError
from cocotb.triggers import RisingEdge, ClockCycles

logger = logging.getLogger("cocotb")
logger.setLevel(logging.DEBUG)

NFFT = 1024
DATA_WIDTH = 16
QFORMAT = 15
SCALE = 1 << QFORMAT
CLK_PERIOD_NS = 5
TIMEOUT_CYCLES = 5000
DEFAULT_TOL = 1e-1
MIN_TONES = 10
MAX_TONES = 20
AMPLITUDE_HEADROOM = 0.85
GOLDEN_SCALE = 1 / NFFT


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def to_q15(value: float) -> int:
    q = int(round(value * SCALE))
    return max(-SCALE, min(SCALE - 1, q))


def from_q15(value: int) -> float:
    return value / SCALE


def get_seed() -> int:
    return int.from_bytes(os.urandom(4), "little")


def get_tolerance() -> float:
    return DEFAULT_TOL


async def _run_fft_test(dut, seed, tol):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
    rng = np.random.default_rng(seed)
    time_domain_re, golden, tones = make_random_test_vector(NFFT, rng)
    time_domain_im = np.zeros_like(time_domain_re)
    samples_q15 = list(
        zip(
            (to_q15(v) for v in time_domain_re),
            (to_q15(v) for v in time_domain_im),
        )
    )

    await reset_dut(dut)

    # fft #1
    await cocotb.start_soon(drive_input(dut, samples_q15))
    await RisingEdge(dut.o_tready)
    logger.info("starting fft #2")
    await cocotb.start_soon(drive_input(dut, samples_q15))
    outputs1 = await collect_outputs(dut, NFFT)
    await RisingEdge(dut.o_tready)

    reported_indices = sorted(idx for idx, _, _ in outputs1)
    assert reported_indices == list(range(NFFT)), (
        "dut did not emit every bin exactly once"
    )

    outputs_sorted = sorted(outputs1, key=lambda t: t[0])

    max_err_re, max_err_im, results, failing = score_against(
        outputs_sorted, golden, tol, "fft1"
    )

    if failing:
        worst = failing[0]
        failure_summary = (
            f"{len(failing)}/{NFFT} bin(s) exceeded tolerance {tol:.1e} "
            f"(seed={seed}); worst bin={worst['idx']} "
            f"err_re={worst['err_re']:.5f} err_im={worst['err_im']:.5f}"
        )
        assert not failing, failure_summary


# ----------------------------------------------------------------------
# stimulus generation
# ----------------------------------------------------------------------
def make_random_test_vector(nfft: int, rng: np.random.Generator):
    num_tones = int(rng.integers(MIN_TONES, MAX_TONES + 1))

    available_bins = np.arange(1, nfft // 2)
    bins = np.sort(rng.choice(available_bins, size=num_tones, replace=False)).tolist()

    raw_amplitudes = rng.uniform(0.2, 1.0, size=num_tones)
    raw_amplitudes *= AMPLITUDE_HEADROOM / raw_amplitudes.sum()
    amplitudes = raw_amplitudes.tolist()

    phases = rng.uniform(-np.pi, np.pi, size=num_tones).tolist()

    n = np.arange(nfft)
    time_domain = np.zeros(nfft)
    for amp, tone_bin, phase in zip(amplitudes, bins, phases):
        time_domain += amp * np.cos(2 * np.pi * tone_bin * n / nfft + phase)

    golden = np.fft.fft(time_domain) * GOLDEN_SCALE

    tones = list(zip(bins, amplitudes, phases))
    logger.info(
        "generated %d tone(s): %s",
        num_tones,
        ", ".join(f"bin={b} amp={a:.3f} phase={p:+.3f}" for b, a, p in tones),
    )
    return time_domain, golden, tones


# ----------------------------------------------------------------------
# dut drive / collect
# ----------------------------------------------------------------------
async def reset_dut(dut):
    dut.reset.value = 1
    dut.i_tvalid.value = 0
    dut.i_tdata_re.value = 0
    dut.i_tdata_im.value = 0
    await ClockCycles(dut.clk, 5)
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
        logger.debug("drove sample %d: re=%d im=%d", i, re_q, im_q)


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
                "output beat %2d/%d: idx=%2d re=%6d (%8.5f) im=%6d (%8.5f)",
                len(outputs),
                expected_count,
                idx,
                re,
                from_q15(re),
                im,
                from_q15(im),
            )

        if cycles_since_last > TIMEOUT_CYCLES:
            raise SimTimeoutError(
                f"no new output beat for {TIMEOUT_CYCLES} cycles; "
                f"got {len(outputs)}/{expected_count} so far"
            )

    return outputs


# ----------------------------------------------------------------------
# scoring
# ----------------------------------------------------------------------
def score_against(outputs_sorted, golden, tol, label):
    results = []
    for idx, re_q, im_q in outputs_sorted:
        actual = complex(from_q15(re_q), from_q15(im_q))
        g = complex(golden[idx])
        err_re = abs(actual.real - g.real)
        err_im = abs(actual.imag - g.imag)
        results.append(
            {
                "idx": idx,
                "actual": actual,
                "golden": g,
                "err_re": err_re,
                "err_im": err_im,
                "err_mag": abs(actual - g),
            }
        )

    max_re = max(r["err_re"] for r in results)
    max_im = max(r["err_im"] for r in results)

    failing = [r for r in results if r["err_re"] >= tol or r["err_im"] >= tol]
    failing.sort(key=lambda r: max(r["err_re"], r["err_im"]), reverse=True)

    logger.info(
        "[%s] max_err_re=%.6f max_err_im=%.6f  (%d/%d bins over tol=%.1e)",
        label,
        max_re,
        max_im,
        len(failing),
        len(results),
        tol,
    )

    if failing:
        logger.error(
            "[%s] %d bin(s) exceeded tolerance %.1e:", label, len(failing), tol
        )
        for r in failing:
            logger.error(
                "  bin %4d: dut=%+.5f%+.5fj  golden=%+.5f%+.5fj  "
                "err_re=%.5f err_im=%.5f",
                r["idx"],
                r["actual"].real,
                r["actual"].imag,
                r["golden"].real,
                r["golden"].imag,
                r["err_re"],
                r["err_im"],
            )
    return max_re, max_im, results, failing


async def _run_fft_test(dut, seed, tol):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    rng = np.random.default_rng(seed)

    time_domain_re, golden, tones = make_random_test_vector(NFFT, rng)
    time_domain_im, golen_im, tones_im = make_random_test_vector(NFFT, rng)
    samples_q15 = list(
        zip(
            (to_q15(v) for v in time_domain_re),
            (to_q15(v) for v in time_domain_im),
        )
    )

    await reset_dut(dut)

    # fft #1
    await cocotb.start_soon(drive_input(dut, samples_q15))

    # core is ready for another frame
    await RisingEdge(dut.o_tready)
    logger.info("starting fft #2")

    # begin loading frame 2 while fft #1 results drain out
    await cocotb.start_soon(drive_input(dut, samples_q15))
    outputs1 = await collect_outputs(dut, NFFT)

    await RisingEdge(dut.o_tready)

    reported_indices = sorted(idx for idx, _, _ in outputs1)
    assert reported_indices == list(range(NFFT)), (
        "dut did not emit every bin exactly once"
    )

    outputs_sorted = sorted(outputs1, key=lambda t: t[0])

    max_err_re, max_err_im, results, failing = score_against(
        outputs_sorted, golden, tol, "fft1"
    )

    if failing:
        worst = failing[0]
        failure_summary = (
            f"{len(failing)}/{NFFT} bin(s) exceeded tolerance {tol:.1e} "
            f"(seed={seed}); worst bin={worst['idx']} "
            f"err_re={worst['err_re']:.5f} err_im={worst['err_im']:.5f}; "
            f"failing bins: {[r['idx'] for r in failing[:15]]}"
            f"{' ...' if len(failing) > 15 else ''}"
        )
        assert not failing, failure_summary


# ----------------------------------------------------------------------
# test
# ----------------------------------------------------------------------
@cocotb.test()
async def test_fft_random_tones(dut):
    seed = get_seed()
    tol = get_tolerance()
    logger.info("using seed=%d , tolerance=%.1e", seed, tol)
    await _run_fft_test(dut, seed, tol)
