import logging
import os
import cocotb
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from cocotb.clock import Clock
from cocotb.result import SimTimeoutError
from cocotb.triggers import RisingEdge, ClockCycles

matplotlib.use("TkAgg")

logger = logging.getLogger("cocotb")
logger.setLevel(logging.DEBUG)

NFFT = DATA_WIDTH = QFORMAT = SCALE = GOLDEN_SCALE = 0

TIMEOUT_CYCLES = 5000
DEFAULT_TOL = 4e-4
MIN_TONES = 1
MAX_TONES = 20
AMPLITUDE_HEADROOM = 0.85

SQUARE_MIN_PERIODS = 1
SQUARE_MAX_PERIODS = 8
SQUARE_MIN_DUTY = 0.2
SQUARE_MAX_DUTY = 0.8

PLOT_RESULTS = os.environ.get("PLOT", "0") == "1"


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def to_fixed(value):
    max_val = (1 << (DATA_WIDTH - 1)) - 1
    min_val = -(1 << (DATA_WIDTH - 1))
    q = int(round(value * SCALE))
    return max(min_val, min(max_val, q))


def from_fixed(value):
    return value / SCALE


def from_fixed_mag(value):
    return value / (SCALE**2)


def get_seed() -> int:
    return int.from_bytes(os.urandom(4), "little")


def get_tolerance() -> float:
    return DEFAULT_TOL


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


def make_square_wave_test_vector(
    nfft: int,
    num_periods: int,
    duty: float = 0.5,
    amplitude: float = AMPLITUDE_HEADROOM,
    phase: float = 0.0,
):
    if not (0.0 < duty < 1.0):
        raise ValueError("duty must be in (0, 1)")
    if num_periods < 1 or nfft % num_periods != 0:
        raise ValueError("num_periods must evenly divide nfft")

    n = np.arange(nfft)
    period_samples = nfft / num_periods
    phase_samples = (phase / (2 * np.pi)) * period_samples
    frac = ((n + phase_samples) % period_samples) / period_samples

    time_domain = np.where(frac < duty, amplitude, -amplitude)

    golden = np.fft.fft(time_domain) * GOLDEN_SCALE

    logger.info(
        "generated square wave: periods=%d duty=%.2f amplitude=%.3f phase=%+.3f",
        num_periods,
        duty,
        amplitude,
        phase,
    )
    return time_domain, golden


def make_single_sample_test_vector(
    nfft: int,
    amplitude: float = AMPLITUDE_HEADROOM,
):
    time_domain = np.zeros(nfft, dtype=np.float64)
    time_domain[nfft // 2] = amplitude

    golden = np.fft.fft(time_domain) * GOLDEN_SCALE

    logger.info(
        "generated single sample: amplitude=%.3f",
        amplitude,
    )
    return time_domain, golden


def make_random_square_wave_test_vector(nfft: int, rng: np.random.Generator):
    divisors = [d for d in range(1, nfft // 2 + 1) if nfft % d == 0]
    max_periods = min(SQUARE_MAX_PERIODS, max(divisors))
    candidates = [d for d in divisors if SQUARE_MIN_PERIODS <= d <= max_periods]
    if not candidates:
        candidates = [1]
    num_periods = int(rng.choice(candidates))

    duty = float(rng.uniform(SQUARE_MIN_DUTY, SQUARE_MAX_DUTY))
    amplitude = float(rng.uniform(0.3, AMPLITUDE_HEADROOM))
    phase = float(rng.uniform(-np.pi, np.pi))

    return make_square_wave_test_vector(
        nfft, num_periods=num_periods, duty=duty, amplitude=amplitude, phase=phase
    )


# ----------------------------------------------------------------------
# dut drive / collect
# ----------------------------------------------------------------------
async def reset_dut(dut):
    dut.reset.value = 1
    dut.i_tvalid.value = 0
    dut.i_tdata_re.value = 0
    dut.i_tdata_im.value = 0
    await ClockCycles(dut.i_Clk, 5)
    dut.reset.value = 0
    await RisingEdge(dut.i_Clk)


async def drive_input(dut, samples_q15):
    for i, (re_q, im_q) in enumerate(samples_q15):
        while not dut.o_tready.value:
            await RisingEdge(dut.i_Clk)
        dut.i_tdata_re.value = re_q
        dut.i_tdata_im.value = im_q
        dut.i_tvalid.value = 1
        await RisingEdge(dut.i_Clk)
        dut.i_tvalid.value = 0
        logger.debug("drove sample %d: re=%d im=%d", i, re_q, im_q)


async def collect_outputs(dut, expected_count):
    outputs = []
    cycles_since_last = 0

    while len(outputs) < expected_count:
        await RisingEdge(dut.i_Clk)
        cycles_since_last += 1

        if dut.o_tvalid.value:
            idx = int(dut.o_xk_index.value)
            re = dut.o_tdata_re.value.signed_integer
            im = dut.o_tdata_im.value.signed_integer
            mag = dut.o_mag_sq.value.signed_integer
            outputs.append((idx, re, im, mag))
            cycles_since_last = 0
            logger.debug(
                "output beat %2d/%d: idx=%2d re=%6d (%8.5f) im=%6d (%8.5f) mag=%6d (%8.5f)",
                len(outputs),
                expected_count,
                idx,
                re,
                from_fixed(re),
                im,
                from_fixed(im),
                mag,
                from_fixed_mag(mag),
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
    for idx, re_q, im_q, mag in outputs_sorted:
        actual = complex(from_fixed(re_q), from_fixed(im_q))
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


# ----------------------------------------------------------------------
# plotting
# ----------------------------------------------------------------------
def plot_results(time_domain_re, time_domain_im, outputs_sorted, golden, tol, seed):
    nfft = len(golden)
    bins = np.arange(nfft)

    dut_re = np.full(nfft, np.nan)
    dut_im = np.full(nfft, np.nan)
    dut_mag_sq = np.full(nfft, np.nan)
    for idx, re_q, im_q, mag_q in outputs_sorted:
        dut_re[idx] = from_fixed(re_q)
        dut_im[idx] = from_fixed(im_q)
        dut_mag_sq[idx] = from_fixed_mag(mag_q)

    golden_re = golden.real
    golden_im = golden.imag
    golden_mag_sq = golden_re**2 + golden_im**2

    err_re = dut_re - golden_re
    err_im = dut_im - golden_im

    fig, axes = plt.subplots(4, 1, figsize=(12, 10))
    fig.suptitle(f"FFT test results (seed={seed}, NFFT={nfft})")

    # --- panel 1: input samples ---
    n = np.arange(len(time_domain_re))
    axes[0].plot(n, time_domain_re, label="input (real)", linewidth=1)
    axes[0].plot(n, time_domain_im, label="input (imag)", linewidth=1)
    axes[0].set_title("Input time-domain samples")
    axes[0].set_xlabel("sample n")
    axes[0].set_ylabel("amplitude")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, alpha=0.3)

    # --- panel 2: golden vs dut overlay ---
    axes[1].plot(
        bins, golden_re, label="golden (real)", linewidth=1.2, marker="o", markersize=2
    )
    axes[1].plot(
        bins, dut_re, "--", label="dut (real)", linewidth=1.0, marker="o", markersize=2
    )
    axes[1].plot(
        bins, golden_im, label="golden (imag)", linewidth=1.2, marker="o", markersize=2
    )
    axes[1].plot(
        bins, dut_im, "--", label="dut (imag)", linewidth=1.0, marker="o", markersize=2
    )
    axes[1].set_title("Golden vs DUT FFT output")
    axes[1].set_xlabel("bin index")
    axes[1].set_ylabel("amplitude")
    axes[1].legend(loc="upper right", ncol=2)
    axes[1].grid(True, alpha=0.3)

    # --- panel 3: dut magnitude^2 vs golden magnitude^2 ---
    axes[2].plot(
        bins,
        golden_mag_sq,
        label="golden magnitude^2",
        linewidth=1.2,
        marker="o",
        markersize=2,
    )
    axes[2].plot(
        bins,
        dut_mag_sq,
        "--",
        label="dut magnitude^2",
        linewidth=1.0,
        marker="o",
        markersize=2,
    )
    axes[2].set_title("DUT vs golden FFT magnitude^2 (|X[k]|^2)")
    axes[2].set_xlabel("bin index")
    axes[2].set_ylabel("magnitude^2")
    axes[2].legend(loc="upper right", ncol=2)
    axes[2].grid(True, alpha=0.3)

    # --- panel 4: error, normalized to tolerance ---
    axes[3].plot(
        bins, err_re, label="err (real)", linewidth=1, marker="o", markersize=2
    )
    axes[3].plot(
        bins, err_im, label="err (imag)", linewidth=1, marker="o", markersize=2
    )
    axes[3].axhline(tol, color="r", linestyle=":", linewidth=1, label="+tol")
    axes[3].axhline(-tol, color="r", linestyle=":", linewidth=1, label="-tol")
    axes[3].set_title(f"Raw error (dut - golden); tol={tol:.1e}")
    axes[3].set_xlabel("bin index")
    axes[3].set_ylabel("error")
    axes[3].legend(loc="upper right", ncol=2)
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


async def _setup_dut_and_clock(dut):
    global NFFT, DATA_WIDTH, QFORMAT, SCALE, GOLDEN_SCALE
    NFFT = int(dut.NFFT.value)
    DATA_WIDTH = int(dut.DATA_WIDTH.value)
    QFORMAT = int(dut.QFORMAT.value)

    SCALE = 1 << QFORMAT
    GOLDEN_SCALE = 1 / NFFT

    CLK_PERIOD_NS = 10
    cocotb.start_soon(Clock(dut.i_Clk, CLK_PERIOD_NS, unit="ns").start())


async def _run_two_frame_test(
    dut, time_domain_re, time_domain_im, golden, tol, label, seed=0
):
    samples_q15 = list(
        zip(
            (to_fixed(v) for v in time_domain_re),
            (to_fixed(v) for v in time_domain_im),
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
    outputs1 = await collect_outputs(dut, len(golden))

    await RisingEdge(dut.o_tready)

    reported_indices = sorted(idx for idx, _, _, _ in outputs1)
    assert reported_indices == list(range(NFFT)), (
        "dut did not emit every bin exactly once"
    )

    outputs_sorted = sorted(outputs1, key=lambda t: t[0])

    max_err_re, max_err_im, results, failing = score_against(
        outputs_sorted, golden, tol, label
    )

    if PLOT_RESULTS:
        plot_results(time_domain_re, time_domain_im, outputs_sorted, golden, tol, seed)

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


@cocotb.test()
async def test_fft_random_tones(dut):
    await _setup_dut_and_clock(dut)
    seed = get_seed()
    tol = get_tolerance()
    logger.info("using seed=%d , tolerance=%.1e", seed, tol)

    rng = np.random.default_rng(seed)

    time_domain_re, _golden_re_only, tones = make_random_test_vector(NFFT, rng)
    time_domain_im, _golden_im_only, tones_im = make_random_test_vector(NFFT, rng)

    golden = np.fft.fft(time_domain_re + 1j * time_domain_im) * GOLDEN_SCALE

    await _run_two_frame_test(
        dut, time_domain_re, time_domain_im, golden, tol, "fft_random", seed
    )


@cocotb.test()
async def test_fft_square_wave(dut):
    await _setup_dut_and_clock(dut)
    seed = get_seed()
    tol = get_tolerance()
    logger.info("using seed=%d , tolerance=%.1e", seed, tol)

    rng = np.random.default_rng(seed)

    time_domain_re, golden_re_only = make_random_square_wave_test_vector(NFFT, rng)
    time_domain_im = np.zeros(NFFT)

    golden = np.fft.fft(time_domain_re + 1j * time_domain_im) * GOLDEN_SCALE

    await _run_two_frame_test(
        dut, time_domain_re, time_domain_im, golden, tol, "fft_square", seed
    )


@cocotb.test()
async def test_fft_single_sample(dut):
    await _setup_dut_and_clock(dut)
    tol = get_tolerance()
    logger.info("using tolerance=%.1e", tol)

    time_domain_re, golden_re_only = make_single_sample_test_vector(NFFT)
    time_domain_im = np.zeros(NFFT)

    golden = np.fft.fft(time_domain_re + 1j * time_domain_im) * GOLDEN_SCALE

    await _run_two_frame_test(
        dut, time_domain_re, time_domain_im, golden, tol, "fft_single_sample"
    )
