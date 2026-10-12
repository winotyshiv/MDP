import json
import pytest
from bb84_simulator import calculate_mismatches, calculate_qber, calculate_sifting_efficiency, run_bb84_simulation


def test_metrics():
    assert calculate_mismatches([0, 1, 1], [1, 1, 0]) == 2
    assert calculate_mismatches([], []) == 0
    assert calculate_qber(12, 100) == 12
    assert calculate_qber(1, 4) == 25
    assert calculate_qber(0, 5) == 0
    assert calculate_qber(0, 0) is None
    assert calculate_sifting_efficiency(50, 100) == 50
    assert calculate_sifting_efficiency(0, 100) == 0


@pytest.mark.parametrize("function,args", [
    (calculate_qber, (2, 1)), (calculate_qber, (1, 0)), (calculate_qber, (-1, 4)),
    (calculate_qber, (True, 4)), (calculate_qber, (1.2, 4)),
    (calculate_sifting_efficiency, (1, 0)), (calculate_sifting_efficiency, (3, 2)),
    (calculate_mismatches, ([0], [])), (calculate_mismatches, ([2], [0]))])
def test_invalid_metrics(function, args):
    with pytest.raises(ValueError):
        function(*args)


def test_empty_experiment_result():
    r = next(run_bb84_simulation(1, False, seed) for seed in range(100)
             if run_bb84_simulation(1, False, seed).sifted_count == 0)
    assert r.qber is None
    assert "could not be calculated" in r.summary()
    assert r.sifted_table().empty
    assert json.loads(r.report_json())["metrics"]["qber_percent"] is None


def test_denominator_is_sifted_count_and_report_actual():
    r = run_bb84_simulation(1000, True, 12)
    assert r.qber == 100 * r.mismatch_count / r.sifted_count
    assert r.qber != 100 * r.mismatch_count / r.n_bits
    assert json.loads(r.report_json())["metrics"] == r.metrics
    assert str(r.mismatch_count) in r.summary()
