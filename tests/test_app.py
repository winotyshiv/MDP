"""Integration checks exercise the actual Streamlit app and session state."""
from pathlib import Path
import numpy as np
from streamlit.testing.v1 import AppTest
from bb84_simulator import run_bb84_simulation
from visualization import qber_comparison, sifted_bit_agreement, sifting_efficiency, transmission_preview

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def button(at, label):
    return next(b for b in at.button if b.label == label)


def test_dashboard_end_to_end():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert not at.metric
    at.sidebar.checkbox[0].check().run()
    button(at, "Run Simulation").click().run()
    assert not at.exception
    r = at.session_state["result"]
    assert r.n_bits == 1000 and not r.eve_enabled and r.qber == 0
    assert len(at.metric) == 9
    assert next(m.value for m in at.metric if m.label == "Transmitted bits") == "1,000"
    assert next(m.value for m in at.metric if m.label == "QBER") == "0.00%"
    assert len(at.get("download_button")) == 4
    original = r.bob_bits.copy()
    at.radio[0].set_value(64).run()
    assert not at.exception
    np.testing.assert_array_equal(at.session_state["result"].bob_bits, original)
    at.selectbox[0].set_value("Sifted mismatches").run()
    assert not at.exception
    button(at, "Run Eve ON/OFF comparison").click().run()
    assert not at.exception
    assert len(at.get("download_button")) == 5
    off, on = at.session_state["comparison"]
    assert off.n_bits == on.n_bits == r.n_bits
    assert off.qber == 0
    assert on.eve_enabled
    at.sidebar.toggle[0].set_value(True).run()
    assert not at.session_state["result"].eve_enabled
    assert any("Controls have changed" in w.value for w in at.warning)
    button(at, "Run Simulation").click().run()
    assert not at.exception
    assert at.session_state["result"].eve_enabled
    assert "comparison" not in at.session_state
    at.sidebar.slider[0].set_value(10000).run()
    button(at, "Run Simulation").click().run()
    assert not at.exception
    assert at.session_state["result"].n_bits == 10000
    assert len(at.session_state["result"].transmission_table()) == 10000
    at.number_input[-1].set_value(10000).run()
    assert not at.exception


def test_dashboard_zero_sifted_bits():
    # Inject a valid core result because the UI intentionally only accepts N >= 100.
    r = next(run_bb84_simulation(1, False, s) for s in range(100)
             if run_bb84_simulation(1, False, s).sifted_count == 0)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["result"] = r
    at.session_state["result_config"] = (1, False, r.seed)
    at.run()
    assert not at.exception
    assert all(m.value == "N/A" for m in at.metric if m.label in ["QBER", "Measured QBER"])
    assert any("No sifted bits" in i.value for i in at.info)


def test_charts_use_actual_metrics_and_handle_empty_keys():
    off = run_bb84_simulation(1000, False, 3)
    on = run_bb84_simulation(1000, True, 4)
    fig = qber_comparison((off, on))
    assert list(fig.data[0].y) == [off.qber, on.qber]
    assert list(fig.data[0].customdata[1]) == [on.sifted_count, on.mismatch_count]
    assert sum(sifted_bit_agreement(on).data[0].y) == on.sifted_count
    assert sum(sifting_efficiency(on).data[0].y) == on.n_bits
    assert len(transmission_preview(on, 64).data[0].x) == 64
    empty = next(run_bb84_simulation(1, False, s) for s in range(100)
                 if run_bb84_simulation(1, False, s).sifted_count == 0)
    assert qber_comparison((empty, on)).data[0].y[0] is None
    for chart in [qber_comparison((empty, on)), sifted_bit_agreement(empty),
                  sifting_efficiency(empty), transmission_preview(empty)]:
        assert chart.to_json()
