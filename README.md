# BB84 Quantum Key Distribution Simulator

**Visualizing Secure Key Generation and Eavesdropping Detection**

An interactive simulation of Alice, Bob, and Eve demonstrating quantum key
distribution, basis reconciliation, sifted-key generation, and quantum bit error
rate (QBER) analysis. The dashboard uses actual probabilistic experiments, not
fixed example values. No hardware, accounts, paid APIs, or Qiskit are required.
After installing dependencies, the application works locally without internet.

## Requirements and installation

Python 3.10 or newer, with NumPy, Pandas, Streamlit, Plotly, and pytest.
Open a terminal in this project's directory:

```powershell
python -m venv .venv
```

Activate on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On Windows Command Prompt use `.venv\Scripts\activate.bat`.
On macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies, start the dashboard, and open the local URL printed by
Streamlit (normally http://localhost:8501):

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Run all automated checks:

```bash
python -m pytest -q
```

Run deterministic checks separately from large-sample probability checks:

```bash
python -m pytest -q -m "not statistical"
python -m pytest -q -m statistical
```

`requirements.txt` bounds compatible major versions. `requirements-tested.txt`
records the exact top-level versions used in the delivery checks. These exact
versions were tested on Python 3.14; use the ranges for Python 3.10 if a newer
package release requires a newer interpreter. Random sequences across different
NumPy versions are not promised to be identical.

## Using the laboratory

1. Select 100–10,000 transmitted bits in the sidebar (default 1,000).
2. Enable Eve to intercept, measure, and resend every transmitted state.
3. Optionally enable a reproducible seed, then click **Run Simulation**.
4. Review the computed metric cards and the first 32 or 64 transmission events.
   Expand the complete table, filter retained/discarded/error events, or inspect
   a numbered transmission for an explanation of its outcome.
5. Open **Sifted keys** to compare both complete keys or their first 64 bits.
   Each preview bit carries a `=` or `≠` label as well as a color and border.
6. Open **QBER analysis** for the numerator, denominator, interpretation,
   agreement chart, and observed sifting efficiency.
7. In **Eve comparison**, click **Run Eve ON/OFF comparison** to generate two
   independent experiments at the completed main experiment's bit count.
8. Use **Summary & downloads** to save the full transmission CSV, both complete
   keys as text, the JSON report, and (when generated) the paired comparison CSV.

All exported rows and bits are complete; previews never truncate the simulation.
The report includes the seed, Eve status, bit count, retained and discarded
counts, agreements, mismatches, QBER, efficiency, and interpretation. Comparison
CSV rows contain the exact child seed for reproducing each condition.

Results persist during normal Streamlit reruns, including filters, previews,
and downloads. Changing sidebar controls does not silently rerun an experiment:
a visible notice identifies the completed configuration. A new main experiment
clears its previous comparison. Comparison charts and downloads describe the
separate paired runs, not the main experiment. No stochastic result is cached.

## Project structure

```text
app.py                        Streamlit UI, session state, downloads
bb84_simulator.py             Validated measurement, sifting, metrics, results
visualization.py              Reusable interactive Plotly charts
requirements.txt              Compatible dependency ranges
requirements-tested.txt       Exact versions used for delivery checks
pytest.ini                    Statistical test marker
.streamlit/config.toml        Restrained light theme; telemetry disabled
tests/test_bb84.py             Protocol, validation, reproducibility, statistics
tests/test_qber.py             Metric calculations, empty keys, report data
tests/test_app.py              Dashboard interactions, state, chart integration
README.md                     Setup, usage, scientific model and limitations
VALIDATION.md                 Executed checks and measured outcomes
```

## Quantum measurement model

Alice independently samples each bit and each preparation basis with probability
one half. Z encodes bit 0 as |0⟩ and bit 1 as |1⟩; X encodes bit 0 as |+⟩ and bit
1 as |−⟩. Measuring in the preparation basis reproduces the bit with certainty.
Measuring in the other BB84 basis gives a uniformly random bit.

With Eve disabled, Bob receives Alice's prepared states. With Eve enabled, Eve
selects independent random bases, measures the original states using exactly
those measurement rules, and prepares replacement states in her measurement
bases with her measurement outcomes. Bob independently selects bases and
measures those replacement states. Errors are not injected as arbitrary flips.

Both keys are extracted with the same mask, `alice_bases == bob_bases`. Different
bases are discarded even if the recorded bit values happen to agree. An error
flag is only set for a retained position whose bits disagree. All original and
intermediate state arrays are preserved as read-only snapshots inside the
typed `SimulationResult` dataclass. Tables use one-based event positions.

The vectorized measurement function samples randomness only for incompatible
bases. RNGs are explicit local NumPy generators; there is no global random state.
The core accepts any positive integer N so one-qubit edge cases and large
statistical checks are possible; the UI constrains user experiments to 100–10,000.
Bits, bases, lengths, counts, seeds, and Eve's Boolean setting are validated.

## QBER and expected outcomes

```text
QBER (%) = mismatched sifted bits / total sifted bits × 100
sifting efficiency (%) = sifted bits / transmitted bits × 100
```

QBER is **not** calculated over all transmitted bits. The unavailable empty-key
case is `None` in the core, `N/A` in the interface, JSON `null` in the report,
and a blank QBER field in CSV. A comparison bar for an unavailable QBER is omitted
and labeled N/A; it is never replaced with a fabricated zero.

Without Eve, nonempty sifted keys agree exactly in this noiseless model. For full
intercept-resend, at a sifted position Eve chooses the wrong basis with probability
1/2, after which Bob's result differs from Alice's with probability 1/2. Thus the
expected QBER is 1/4, or 25%. It is an expectation, not a value forced on finite
runs. Independent uniform Alice/Bob bases give an expected 50% sifting efficiency.
Finite samples vary, especially smaller experiments.

## Reproducibility and paired runs

The main simulation uses `numpy.random.default_rng(seed)`. If no seed is supplied,
each run uses fresh entropy. For comparison, `SeedSequence(seed).spawn(2)` derives
two independent streams; one uint64 integer is generated from each child as the
seed of its full Eve OFF or Eve ON experiment. The resulting child seeds are
recorded in comparison exports. The comparison uses the main experiment's
configured seed, but separate child streams, so it does not reuse the main run.
With no seed, every comparison click also uses fresh entropy. With a fixed seed,
repeated identical main or comparison configurations reproduce their results
under the same installed dependency versions. Generator output is suitable for
simulation; it is not a cryptographically secure randomness source.

## Scientific limitations

This is a classical probabilistic simulation of ideal BB84 measurement
statistics. It sends and manipulates no physical qubits. It includes only full
intercept-resend eavesdropping, without channel noise, loss, imperfect sources,
detector limitations, or other attack strategies. QBER indicates disturbance;
it neither uniquely identifies an attacker nor proves a channel secure.

Real QKD requires an authenticated classical channel, parameter estimation,
error correction, privacy amplification, finite-key analysis, and an appropriate
security proof. Sifted keys are not final secure cryptographic keys. The full-key
QBER displayed here is an educational diagnostic using the simulator's access
to both parties' bits. In practical QKD, a public test subset estimates the error
rate, and those disclosed test bits must be removed from secret key material.
This application implements neither that test-sampling process nor final key
generation and makes no claim of production-grade quantum security.

## Troubleshooting

- **Python not found on Windows:** install Python or use its full executable
  path. Disable the Microsoft Store alias if it shadows an installed interpreter.
- **PowerShell blocks activation:** activation is optional. Use
  `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and
  `.\.venv\Scripts\python.exe -m streamlit run app.py` directly.
- **Package missing:** install requirements with the same interpreter used to
  start the app; `python -m pip` avoids a separate pip executable mismatch.
- **Port busy:** add `--server.port 8502` to the Streamlit startup command.
- **Empty key / unavailable QBER:** this is a valid possible stochastic outcome;
  start another experiment or increase the number of transmitted bits.
- **Old results after changing controls:** click Run Simulation to apply the
  changed configuration. The notice describes which completed run is displayed.
- **Different outcomes on another machine:** install matching dependency versions
  and use the same seed and configuration; unseeded experiments vary by design.

## References

- [Streamlit API documentation](https://docs.streamlit.io/develop/api-reference)
- [Streamlit AppTest documentation](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)
- [Analysis of BB84 intercept-resend QBER distributions](https://dl.ifip.org/db/conf/ondm/ondm2023/1570879964.pdf)

See `VALIDATION.md` for the checks actually executed for this delivery.
