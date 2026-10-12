import numpy as np
import pytest
from bb84_simulator import (generate_random_bits, generate_random_bases, measure_qubit,
    simulate_bob_measurement, simulate_eve_intercept_resend, sift_keys,
    run_bb84_simulation, compare_eve_conditions, comparison_table, state_label)


def test_generators():
    rng = np.random.default_rng(7)
    assert set(generate_random_bits(1000, rng)) == {0, 1}
    assert set(generate_random_bases(1000, rng)) == {"Z", "X"}
    assert len(generate_random_bits(0, rng)) == 0


@pytest.mark.parametrize("basis", ["X", "Z"])
@pytest.mark.parametrize("bit", [0, 1])
def test_same_basis(bit, basis):
    rng = np.random.default_rng(1)
    assert all(measure_qubit(bit, basis, basis, rng) == bit for _ in range(100))


def test_sifting_uses_same_positions():
    a, b, mask = sift_keys([1, 0, 1, 1, 0, 1], list("ZXZXZX"),
                           [1, 0, 0, 1, 0, 1], list("ZXXZZX"))
    assert mask.tolist() == [True, True, False, False, True, True]
    assert a.tolist() == b.tolist() == [1, 0, 0, 1]
    assert len(sift_keys([0], ["Z"], [1], ["X"])[0]) == 0


@pytest.mark.parametrize("eve", [False, True])
def test_reproducibility_and_accounting(eve):
    r, repeat = run_bb84_simulation(10000, eve, 42), run_bb84_simulation(10000, eve, 42)
    for field in ("alice_bits", "alice_bases", "bob_bits", "bob_bases", "matching_basis", "received_bits"):
        np.testing.assert_array_equal(getattr(r, field), getattr(repeat, field))
    assert len(r.alice_sifted) == len(r.bob_sifted)
    m = r.metrics
    assert m["matching_basis_count"] + m["discarded_count"] == 10000
    assert m["matching_sifted_bits"] + m["mismatched_sifted_bits"] == r.sifted_count
    assert r.mismatch_count <= r.sifted_count
    assert len(r.transmission_table()) == 10000
    assert not r.alice_bits.flags.writeable
    if eve:
        np.testing.assert_array_equal(r.received_bits, r.eve_bits)
        np.testing.assert_array_equal(r.received_bases, r.eve_bases)
        same = r.alice_bases == r.eve_bases
        np.testing.assert_array_equal(r.alice_bits[same], r.eve_bits[same])
        same = r.bob_bases == r.received_bases
        np.testing.assert_array_equal(r.bob_bits[same], r.received_bits[same])
    else:
        assert r.qber == 0
        assert r.eve_bits is r.eve_bases is None
        assert set(r.transmission_table()["Eve basis"]) == {"—"}


def test_comparison_metadata_and_independence():
    off, on = compare_eve_conditions(1000, 99)
    assert off.n_bits == on.n_bits == 1000
    assert not off.eve_enabled and on.eve_enabled
    assert off.seed != on.seed
    assert not np.array_equal(off.alice_bits, on.alice_bits)
    repeat = compare_eve_conditions(1000, 99)
    np.testing.assert_array_equal(on.bob_bits, repeat[1].bob_bits)
    np.testing.assert_array_equal(run_bb84_simulation(1000, True, on.seed).bob_bits, on.bob_bits)
    assert comparison_table((off, on))["condition"].tolist() == ["Eve OFF", "Eve ON"]


@pytest.mark.parametrize("n", [0, -1, 1.5, True, "100"])
def test_invalid_counts(n):
    with pytest.raises(ValueError, match="integer"):
        run_bb84_simulation(n, False)


def test_invalid_arrays_and_configuration():
    rng = np.random.default_rng(0)
    for args in [([2], ["Z"], ["X"]), ([0], ["Y"], ["Z"]), ([0, 1], ["Z"], ["X"]), ([[0]], ["Z"], ["X"])]:
        with pytest.raises(ValueError):
            simulate_bob_measurement(*args, rng)
    with pytest.raises(ValueError):
        simulate_eve_intercept_resend([0, 1], ["Z"], rng)
    with pytest.raises(ValueError):
        run_bb84_simulation(10, "ON")
    with pytest.raises(ValueError):
        run_bb84_simulation(10, False, -1)
    with pytest.raises(ValueError):
        measure_qubit(0, "Y", "Z", rng)
    with pytest.raises(ValueError):
        generate_random_bits(-1, rng)


def test_state_labels():
    assert [state_label(b, p) for p in ["Z", "X"] for b in [0, 1]] == ["|0⟩", "|1⟩", "|+⟩", "|−⟩"]


@pytest.mark.statistical
def test_scalar_incompatible_measurements_unbiased():
    rng = np.random.default_rng(123)
    for preparation, measurement in [("Z", "X"), ("X", "Z")]:
        for bit in [0, 1]:
            samples = [measure_qubit(bit, preparation, measurement, rng) for _ in range(20000)]
            assert abs(np.mean(samples) - .5) < .025


@pytest.mark.statistical
def test_full_attack_statistics():
    r = run_bb84_simulation(200000, True, 122)
    assert abs(r.qber - 25) < 1
    assert abs(r.metrics["sifting_efficiency_percent"] - 50) < 1
    for bits in (r.alice_bits, r.eve_bits, r.bob_bits):
        assert abs(bits.mean() - .5) < .01
    for bases in (r.alice_bases, r.eve_bases, r.bob_bases):
        assert abs(np.mean(bases == "Z") - .5) < .01
    assert abs(np.mean(r.alice_bases == r.eve_bases) - .5) < .01
    assert abs(np.mean(r.eve_bases == r.bob_bases) - .5) < .01
