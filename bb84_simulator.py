"""Classical stochastic model of ideal BB84; no physical qubits or security proof."""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
import json
import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray


def _count(value: int, name: str, minimum: int = 0) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}.")
    return int(value)


def _bits(values: ArrayLike) -> NDArray:
    a = np.asarray(values)
    if a.ndim != 1 or not np.all(np.isin(a, [0, 1])):
        raise ValueError("Bits must be a one-dimensional sequence containing only 0 and 1.")
    return a.astype(np.int8)


def _bases(values: ArrayLike) -> NDArray:
    a = np.asarray(values)
    if a.ndim != 1 or not np.all(np.isin(a, ["Z", "X"])):
        raise ValueError("Bases must be a one-dimensional sequence containing only Z and X.")
    return a.astype("U1")


def _lengths(*arrays: NDArray) -> None:
    if len({len(a) for a in arrays}) > 1:
        raise ValueError("Input arrays must have identical lengths.")


def _seed(seed: int | None) -> int | None:
    return None if seed is None else _count(seed, "seed")


def generate_random_bits(n: int, rng: np.random.Generator) -> NDArray:
    """Generate independent fair bits using the caller's generator."""
    return rng.integers(0, 2, size=_count(n, "n"), dtype=np.int8)


def generate_random_bases(n: int, rng: np.random.Generator) -> NDArray:
    """Generate independent, equally likely computational/diagonal bases."""
    return np.array(["Z", "X"])[generate_random_bits(n, rng)]


def measure_qubit(bit: int, preparation_basis: str, measurement_basis: str,
                  rng: np.random.Generator) -> int:
    """Same basis preserves the bit; incompatible basis gives a fair bit."""
    b = _bits([bit])[0]
    p, m = _bases([preparation_basis, measurement_basis])
    return int(b) if p == m else int(rng.integers(0, 2))


def simulate_bob_measurement(received_bits: ArrayLike, received_bases: ArrayLike,
                             bob_bases: ArrayLike, rng: np.random.Generator) -> NDArray:
    """Vectorized measurement, sampling only incompatible-basis positions."""
    bits, prepared, measured = _bits(received_bits), _bases(received_bases), _bases(bob_bases)
    _lengths(bits, prepared, measured)
    result = bits.copy()
    incompatible = prepared != measured
    result[incompatible] = generate_random_bits(int(incompatible.sum()), rng)
    return result


def simulate_eve_intercept_resend(alice_bits: ArrayLike, alice_bases: ArrayLike,
                                  rng: np.random.Generator) -> tuple[NDArray, NDArray]:
    """Return Eve's measured bits and bases, also defining her replacement states."""
    bits, bases = _bits(alice_bits), _bases(alice_bases)
    _lengths(bits, bases)
    eve_bases = generate_random_bases(len(bits), rng)
    eve_bits = simulate_bob_measurement(bits, bases, eve_bases, rng)
    return eve_bits, eve_bases


def sift_keys(alice_bits: ArrayLike, alice_bases: ArrayLike, bob_bits: ArrayLike,
              bob_bases: ArrayLike) -> tuple[NDArray, NDArray, NDArray]:
    """Extract both keys with the same publicly reconciled basis mask."""
    a, ab, b, bb = _bits(alice_bits), _bases(alice_bases), _bits(bob_bits), _bases(bob_bases)
    _lengths(a, ab, b, bb)
    mask = ab == bb
    return a[mask], b[mask], mask


def calculate_mismatches(alice_sifted: ArrayLike, bob_sifted: ArrayLike) -> int:
    """Count disagreements in equally sized binary keys."""
    a, b = _bits(alice_sifted), _bits(bob_sifted)
    _lengths(a, b)
    return int(np.count_nonzero(a != b))


def calculate_qber(mismatch_count: int, sifted_count: int) -> float | None:
    """QBER in percent, or None when there are no sifted bits."""
    errors, total = _count(mismatch_count, "mismatch_count"), _count(sifted_count, "sifted_count")
    if errors > total:
        raise ValueError("Mismatches cannot exceed sifted bits.")
    return 100.0 * errors / total if total else None


def calculate_sifting_efficiency(sifted_count: int, transmitted_count: int) -> float:
    """Percentage of transmitted positions retained after basis reconciliation."""
    kept, total = _count(sifted_count, "sifted_count"), _count(transmitted_count, "transmitted_count", 1)
    if kept > total:
        raise ValueError("Sifted bits cannot exceed transmitted bits.")
    return 100.0 * kept / total


@dataclass(frozen=True)
class SimulationResult:
    """Complete experiment state; arrays are read-only snapshots."""
    n_bits: int
    eve_enabled: bool
    seed: int | None
    alice_bits: NDArray
    alice_bases: NDArray
    eve_bits: NDArray | None
    eve_bases: NDArray | None
    received_bits: NDArray
    received_bases: NDArray
    bob_bases: NDArray
    bob_bits: NDArray
    matching_basis: NDArray
    alice_sifted: NDArray
    bob_sifted: NDArray

    @property
    def sifted_count(self) -> int:
        return len(self.alice_sifted)

    @property
    def mismatch_count(self) -> int:
        return calculate_mismatches(self.alice_sifted, self.bob_sifted)

    @property
    def qber(self) -> float | None:
        return calculate_qber(self.mismatch_count, self.sifted_count)

    @property
    def metrics(self) -> dict:
        return {"transmitted_bits": self.n_bits, "eve_enabled": self.eve_enabled,
                "seed": self.seed, "matching_basis_count": self.sifted_count,
                "discarded_count": self.n_bits - self.sifted_count,
                "sifted_bits": self.sifted_count,
                "matching_sifted_bits": self.sifted_count - self.mismatch_count,
                "mismatched_sifted_bits": self.mismatch_count, "qber_percent": self.qber,
                "sifting_efficiency_percent": calculate_sifting_efficiency(self.sifted_count, self.n_bits)}

    def transmission_table(self) -> pd.DataFrame:
        """Every event, including the state received by Bob; one-based positions."""
        mismatch = self.matching_basis & (self.alice_bits != self.bob_bits)
        return pd.DataFrame({"Position": np.arange(1, self.n_bits + 1),
            "Alice bit": self.alice_bits, "Alice basis": self.alice_bases,
            "Alice state": [state_label(b, p) for b, p in zip(self.alice_bits, self.alice_bases)],
            "Eve basis": self.eve_bases if self.eve_enabled else "—",
            "Eve result": self.eve_bits if self.eve_enabled else "—",
            "Received bit": self.received_bits, "Received basis": self.received_bases,
            "Bob basis": self.bob_bases, "Bob result": self.bob_bits,
            "Basis match": self.matching_basis, "Survives sifting": self.matching_basis,
            "Sifted mismatch": mismatch,
            "Outcome": np.where(~self.matching_basis, "Discarded: different bases",
                                  np.where(mismatch, "Retained: mismatch", "Retained: match"))})

    def sifted_table(self) -> pd.DataFrame:
        return pd.DataFrame({"Sifted position": np.arange(1, self.sifted_count + 1),
            "Transmission position": np.flatnonzero(self.matching_basis) + 1,
            "Alice bit": self.alice_sifted, "Bob bit": self.bob_sifted,
            "Outcome": np.where(self.alice_sifted == self.bob_sifted, "Match", "Mismatch")})

    def summary(self) -> str:
        q = "N/A" if self.qber is None else f"{self.qber:.2f}%"
        text = (f"Alice transmitted {self.n_bits:,} simulated qubits with Eve {'ON' if self.eve_enabled else 'OFF'}. "
                f"After basis reconciliation, {self.sifted_count:,} matching-basis positions became sifted bits. "
                f"The keys contain {self.mismatch_count:,} mismatches; QBER is {q}. ")
        if self.qber is None:
            return text + "No bits survived sifting, so QBER could not be calculated."
        if self.eve_enabled:
            return text + "Full intercept-resend has an expected QBER of 25%, with finite-sample variation. QBER alone does not identify the cause of disturbance."
        return text + "Zero sifted errors are expected in this ideal noiseless model. This does not prove real-world security."

    def report_json(self) -> str:
        """Export configuration, actual metrics, interpretation, and model limitations."""
        return json.dumps({"model": "Ideal classical BB84; full intercept-resend when Eve ON",
                           "metrics": self.metrics, "summary": self.summary(),
                           "qber_scope": "Complete sifted key; educational simulation metric",
                           "security": "Not a final secure key; no authentication, error correction, privacy amplification or finite-key security proof"}, indent=2, allow_nan=False)


def state_label(bit: int, basis: str) -> str:
    """Return the conventional ket label for a validated BB84 state."""
    b = int(_bits([bit])[0])
    p = _bases([basis])[0]
    return {("Z", 0): "|0⟩", ("Z", 1): "|1⟩", ("X", 0): "|+⟩", ("X", 1): "|−⟩"}[(p, b)]


def run_bb84_simulation(n_bits: int, eve_enabled: bool, seed: int | None = None) -> SimulationResult:
    """Execute ideal BB84. Core accepts any positive N; UI limits N to 100–10,000."""
    n = _count(n_bits, "n_bits", 1)
    if not isinstance(eve_enabled, (bool, np.bool_)):
        raise ValueError("eve_enabled must be Boolean.")
    seed = _seed(seed)
    rng = np.random.default_rng(seed)
    a, ab = generate_random_bits(n, rng), generate_random_bases(n, rng)
    e, eb = simulate_eve_intercept_resend(a, ab, rng) if eve_enabled else (None, None)
    received, rb = (e.copy(), eb.copy()) if eve_enabled else (a.copy(), ab.copy())
    bb = generate_random_bases(n, rng)
    b = simulate_bob_measurement(received, rb, bb, rng)
    sa, sb, mask = sift_keys(a, ab, b, bb)
    for array in (a, ab, e, eb, received, rb, bb, b, sa, sb, mask):
        if array is not None:
            array.setflags(write=False)
    return SimulationResult(n, bool(eve_enabled), seed, a, ab, e, eb, received, rb, bb, b, mask, sa, sb)


def compare_eve_conditions(n_bits: int, seed: int | None = None) -> tuple[SimulationResult, SimulationResult]:
    """Run two independent child RNG streams spawned from the comparison seed."""
    children = np.random.SeedSequence(_seed(seed)).spawn(2)
    seeds = [int(s.generate_state(1, dtype=np.uint64)[0]) for s in children]
    return run_bb84_simulation(n_bits, False, seeds[0]), run_bb84_simulation(n_bits, True, seeds[1])


def comparison_table(results: tuple[SimulationResult, SimulationResult]) -> pd.DataFrame:
    """Measured metrics and reproducible child seeds for comparison export."""
    return pd.DataFrame([{"condition": "Eve ON" if r.eve_enabled else "Eve OFF", **r.metrics} for r in results])
