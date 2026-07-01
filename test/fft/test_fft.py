import logging
import os

import cocotb

import matplotlib.pyplot as plt
import numpy as np
from cocotb.clock import Clock
from cocotb.result import SimTimeoutError
from cocotb.triggers import RisingEdge

logger = logging.getLogger("cocotb")
logger.setLevel(logging.DEBUG)

NFFT = 1024
DATA_WIDTH = 16
QFORMAT = 15
SCALE = 1 << QFORMAT

CLK_PERIOD_NS = 5
TIMEOUT_CYCLES = 5000
TONE_BIN = 24
GOLDEN_SCALE = 1 / NFFT

PLOT_DIR = os.path.join(os.path.dirname(__file__), "plots")


# ----------------------------------------------------------------------
# Fixed-point helpers
# ----------------------------------------------------------------------
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
    """Single-tone real cosine -> sparse golden spectrum (bins TONE_BIN, nfft-TONE_BIN)."""
    n = np.arange(nfft)
    time_domain = 0.5 * np.cos(2 * np.pi * TONE_BIN * n / nfft)
    golden = np.fft.fft(time_domain) * GOLDEN_SCALE
    return time_domain, golden


# ----------------------------------------------------------------------
# DUT drive / collect
# ----------------------------------------------------------------------
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
        logger.debug("Drove sample %d: re=%d im=%d", i, re_q, im_q)


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
                "Output beat %2d/%d: idx=%2d re=%6d (%8.5f) im=%6d (%8.5f)",
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
                f"No new output beat for {TIMEOUT_CYCLES} cycles; "
                f"got {len(outputs)}/{expected_count} so far"
            )

    return outputs


# ----------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------
def score_against(outputs_sorted, golden, label):
    errs = []
    for (idx, re_q, im_q), g in zip(outputs_sorted, golden):
        actual = from_q15(re_q) + 1j * from_q15(im_q)
        err_re = abs(actual.real - g.real)
        err_im = abs(actual.imag - g.imag)
        errs.append((idx, actual, g, err_re, err_im))
    max_re = max(e[3] for e in errs)
    max_im = max(e[4] for e in errs)
    logger.info("[%s] max_err_re=%.5f max_err_im=%.5f", label, max_re, max_im)
    return max_re, max_im, errs


# ----------------------------------------------------------------------
# Plotting — DUT vs golden overlay
# ----------------------------------------------------------------------
def plot_overlay(outputs_sorted, golden, label, filename):
    bins = np.array([idx for idx, _, _ in outputs_sorted])
    dut_complex = np.array(
        [from_q15(re) + 1j * from_q15(im) for _, re, im in outputs_sorted]
    )
    dut_mag = np.abs(dut_complex)
    golden_mag = np.abs(golden)
    err = np.abs(dut_mag - golden_mag[bins])

    plt.style.use("dark_background")
    fig, (ax_mag, ax_err) = plt.subplots(
        2,
        1,
        figsize=(13, 7),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
        facecolor="#0d1117",
    )
    fig.suptitle(
        f"FFT Core vs NumPy Golden — {label}",
        fontsize=15,
        fontweight="bold",
        color="#e6edf3",
    )

    # Magnitude overlay
    ax_mag.fill_between(
        np.arange(len(golden_mag)),
        golden_mag,
        color="#58a6ff",
        alpha=0.25,
        label="golden |X[k]|",
    )
    ax_mag.plot(
        np.arange(len(golden_mag)), golden_mag, color="#58a6ff", lw=1.5, alpha=0.8
    )
    ax_mag.scatter(
        bins,
        dut_mag,
        color="#ff7b72",
        s=18,
        zorder=5,
        label="DUT |X[k]|",
        edgecolors="none",
    )
    ax_mag.set_ylabel("Magnitude")
    ax_mag.set_facecolor("#161b22")
    ax_mag.legend(loc="upper right", framealpha=0.3)
    ax_mag.grid(alpha=0.15)
    ax_mag.set_title(
        "Overlay: DUT samples on golden magnitude spectrum",
        fontsize=10,
        color="#9198a1",
    )

    # Annotate the expected tone bins
    for b in (TONE_BIN, NFFT - TONE_BIN):
        ax_mag.axvline(b, color="#3fb950", ls="--", lw=0.8, alpha=0.6)
        ax_mag.text(
            b,
            ax_mag.get_ylim()[1] * 0.9,
            f"bin {b}",
            color="#3fb950",
            fontsize=8,
            ha="center",
        )

    # Error subplot
    ax_err.semilogy(bins, np.clip(err, 1e-9, None), color="#d29922", lw=1.0)
    ax_err.set_ylabel("|error|")
    ax_err.set_xlabel("Bin index k")
    ax_err.set_facecolor("#161b22")
    ax_err.grid(alpha=0.15)

    for ax in (ax_mag, ax_err):
        for spine in ax.spines.values():
            spine.set_color("#30363d")

    fig.tight_layout()
    os.makedirs(PLOT_DIR, exist_ok=True)
    out_path = os.path.join(PLOT_DIR, filename)
    fig.savefig(out_path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info("Saved overlay plot -> %s", out_path)
    return out_path


# ----------------------------------------------------------------------
# Test
# ----------------------------------------------------------------------
@cocotb.test()
async def test_fft_single_tone(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    time_domain, golden = make_test_vector(NFFT)
    samples_q15 = [(to_q15(v), 0) for v in time_domain]

    await reset_dut(dut)

    # FFT #1
    await cocotb.start_soon(drive_input(dut, samples_q15))

    # Core is ready for another frame
    await RisingEdge(dut.o_tready)
    logger.info("Starting FFT #2")

    # Begin loading frame 2 while FFT #1 results drain out
    await cocotb.start_soon(drive_input(dut, samples_q15))
    outputs1 = await collect_outputs(dut, NFFT)

    await RisingEdge(dut.o_tready)

    nbits = int(np.ceil(np.log2(NFFT)))

    reported_indices = sorted(idx for idx, _, _ in outputs1)
    assert reported_indices == list(range(NFFT)), (
        "DUT did not emit every bin exactly once"
    )

    outputs_sorted = sorted(outputs1, key=lambda t: t[0])

    golden_natural = golden
    golden_bitrev = np.array([golden[bit_reverse_index(i, nbits)] for i in range(NFFT)])

    err_re_nat, err_im_nat, _ = score_against(
        outputs_sorted, golden_natural, "FFT1 natural"
    )
    err_re_rev, err_im_rev, _ = score_against(
        outputs_sorted, golden_bitrev, "FFT1 bitrev"
    )

    # Plot against whichever ordering actually fits better — makes a
    # bin-permutation bug obvious even before checking the assertion.
    natural_is_better = (err_re_nat + err_im_nat) <= (err_re_rev + err_im_rev)
    best_label = "natural order" if natural_is_better else "bit-reversed order"
    best_golden = golden_natural if natural_is_better else golden_bitrev

    plot_overlay(outputs_sorted, best_golden, best_label, "fft1_overlay.png")

    TOL = 1e-2
    assert min(err_re_nat, err_re_rev) < TOL, (
        "Real part mismatch exceeds tolerance in both orderings"
    )
    assert min(err_im_nat, err_im_rev) < TOL, (
        "Imag part mismatch exceeds tolerance in both orderings"
    )
