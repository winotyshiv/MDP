"""Streamlit educational laboratory for the ideal BB84 protocol."""
from html import escape
import numpy as np
import streamlit as st
from bb84_simulator import run_bb84_simulation, compare_eve_conditions, comparison_table
from visualization import qber_comparison, sifted_bit_agreement, sifting_efficiency, transmission_preview

st.set_page_config(page_title="BB84 Quantum Lab", page_icon="🔬", layout="wide")
st.markdown("""<style>
.block-container {max-width:1440px; padding-top:2rem;}
h1 {letter-spacing:-.035em;} h2 {letter-spacing:-.02em;}
[data-testid="stMetric"] {border:1px solid #d8e2ea;border-radius:10px;padding:14px;}
.eyebrow {color:#087f8c;font-size:.8rem;font-weight:700;letter-spacing:.14em;}
.keyline {display:flex;flex-wrap:wrap;gap:4px;}
.keybit {display:inline-block;padding:5px 7px;border-radius:4px;font-family:monospace;
 color:#18323a;background:#d2eeed;border:1px solid #83bfbd;}
.keyerror {background:#f8ddc5;border:2px solid #b75d25;color:#532700;}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="eyebrow">QUANTUM CRYPTOGRAPHY LAB · IDEAL BB84</div>', unsafe_allow_html=True)
st.title("BB84 Quantum Key Distribution Simulator")
st.caption("Visualizing Secure Key Generation and Eavesdropping Detection")
st.write("Explore how Alice and Bob establish a shared key and how an intercept-resend eavesdropper can introduce detectable errors.")
st.info("Educational classical simulation: no physical qubits. Sifted keys are intermediate results, not final secure cryptographic keys. QBER alone does not prove security or identify an attacker.")

with st.sidebar:
    st.header("Experiment controls")
    n_bits = st.slider("Number of transmitted bits", 100, 10000, 1000, 100)
    eve = st.toggle("Enable Eve", value=False, help="Eve independently measures and resends every qubit in a random Z or X basis.")
    seeded = st.checkbox("Use a reproducible seed")
    seed_value = st.number_input("Random seed", min_value=0, max_value=2147483647, value=42, step=1, disabled=not seeded)
    seed = int(seed_value) if seeded else None
    run = st.button("Run Simulation", type="primary", use_container_width=True)
    st.caption("Same configuration and seed repeat a run. Without a seed, each click uses fresh randomness.")
    st.divider()
    st.markdown("**Two bases, four states**\n\nZ: 0 → |0⟩ · 1 → |1⟩\n\nX: 0 → |+⟩ · 1 → |−⟩")
    st.caption("Same basis → prepared bit. Different basis → fair random bit.")

config = (n_bits, eve, seed)
if run:
    try:
        if not 100 <= n_bits <= 10000:
            raise ValueError("Choose between 100 and 10,000 transmitted bits.")
        st.session_state.result = run_bb84_simulation(*config)
        st.session_state.result_config = config
        st.session_state.pop("comparison", None)
        st.session_state.pop("comparison_config", None)
    except ValueError as error:
        st.error(str(error))

with st.expander("How the protocol works · Alice → optional Eve → Bob", expanded="result" not in st.session_state):
    a, e, b = st.columns(3)
    a.markdown("**Alice · prepare**\n\nGenerate fair bits → select random Z / X bases → prepare states.")
    e.markdown("**Eve · optional interception**\n\nSelect independent bases → measure → resend the measured state.")
    b.markdown("**Bob · measure**\n\nSelect independent bases → measure the received states.")
    st.markdown("**Reconcile bases → sift keys → estimate errors → interpret disturbance**")
    st.write("Alice and Bob publicly compare bases, not all secret bits. In practical QKD they disclose a test subset to estimate QBER and remove those disclosed bits from the remaining key material.")
    st.caption("This dashboard computes QBER over the complete sifted key for educational inspection. It implements no public test sample or final secret-key generation.")

with st.expander("Model limitations and beginner glossary"):
    st.write("This classical model reproduces ideal BB84 measurement probabilities without manipulating physical qubits. Eve performs only a full intercept-resend attack; other strategies and channel noise are not modeled. Real QKD requires authenticated classical communication, parameter estimation, error correction, privacy amplification, finite-key analysis, and a suitable security proof. This application claims no production-grade quantum security.")
    st.markdown("**Qubit:** a quantum two-level system, modeled here probabilistically. **Basis:** the set of states used to prepare or measure a qubit. **Sifting:** retaining only matching-basis positions. **Sifted key:** intermediate retained bits. **QBER:** percentage of retained bits that disagree.")
    st.caption("Expected full intercept-resend QBER: Eve chooses the wrong basis half the time; Bob then disagrees with Alice half the time at retained positions. ½ × ½ = 25%.")

if "result" not in st.session_state:
    st.subheader("Ready for your first experiment")
    st.write("Choose the bit count and Eve setting, then select Run Simulation. All tables and charts will show measured outcomes from that experiment.")
    st.stop()

r = st.session_state.result
if config != st.session_state.result_config:
    st.warning(f"Controls have changed. Displayed results remain the completed experiment: {r.n_bits:,} bits, Eve {'ON' if r.eve_enabled else 'OFF'}, seed {r.seed if r.seed is not None else 'fresh randomness'}. Select Run Simulation to apply the new settings.")
st.subheader("Simulation overview")
st.caption(f"Completed experiment · {r.n_bits:,} transmitted bits · Eve {'ON' if r.eve_enabled else 'OFF'} · Seed: {r.seed if r.seed is not None else 'not supplied'}")
metrics = r.metrics
for row in [[("Transmitted bits", f"{r.n_bits:,}"), ("Matching bases", f"{r.sifted_count:,}"),
             ("Sifted bits", f"{r.sifted_count:,}"), ("Eve status", "ON" if r.eve_enabled else "OFF")],
            [("Matching sifted bits", f"{r.sifted_count-r.mismatch_count:,}"),
             ("Mismatched sifted bits", f"{r.mismatch_count:,}"),
             ("QBER", "N/A" if r.qber is None else f"{r.qber:.2f}%"),
             ("Sifting efficiency", f"{metrics['sifting_efficiency_percent']:.2f}%")]]:
    for col, (label, value) in zip(st.columns(4), row):
        col.metric(label, value)

transmission, keys, analysis, comparison, exports = st.tabs([
    "Transmission events", "Sifted keys", "QBER analysis", "Eve comparison", "Summary & downloads"])

with transmission:
    st.subheader("Alice and Bob transmission data")
    preview_count = st.radio("Preview length", [32, 64], horizontal=True)
    st.plotly_chart(transmission_preview(r, preview_count), use_container_width=True)
    table = r.transmission_table()
    st.dataframe(table.head(preview_count), hide_index=True, use_container_width=True)
    with st.expander(f"Inspect all {r.n_bits:,} transmission events"):
        selection = st.selectbox("Filter events", ["All positions", "Retained positions", "Sifted mismatches", "Discarded positions"])
        filtered = {"All positions": table, "Retained positions": table[table["Survives sifting"]],
                    "Sifted mismatches": table[table["Sifted mismatch"]], "Discarded positions": table[~table["Survives sifting"]]}[selection]
        st.caption(f"Showing {len(filtered):,} events; exports always contain the complete dataset.")
        st.dataframe(filtered, hide_index=True, use_container_width=True, height=400)
    with st.expander("Explain an individual transmission"):
        position = st.number_input("Transmission position", min_value=1, max_value=r.n_bits, value=1, step=1)
        i = int(position) - 1
        st.write(f"Alice prepared bit {r.alice_bits[i]} in {r.alice_bases[i]} ({table.iloc[i]['Alice state']}).")
        if r.eve_enabled:
            st.write(f"Eve measured in {r.eve_bases[i]}, obtained {r.eve_bits[i]}, and resent bit {r.received_bits[i]} in {r.received_bases[i]}.")
        st.write(f"Bob measured in {r.bob_bases[i]} and obtained {r.bob_bits[i]}. {table.iloc[i]['Outcome']}.")
        if not r.matching_basis[i]:
            st.caption("Alice and Bob chose different bases, so this position contributes neither a key bit nor a QBER error.")
        else:
            st.caption("Alice and Bob chose the same basis. Their measured bit comparison contributes to sifted-key QBER.")

with keys:
    st.subheader("Sifting and shared-key comparison")
    st.write("Only positions where Alice and Bob selected the same basis are retained during sifting. In the ideal model, these positions agree when Eve is absent.")
    st.caption(f"Full key length: {r.sifted_count:,} · Matching: {r.sifted_count-r.mismatch_count:,} · Mismatched: {r.mismatch_count:,}. Preview shows the first {min(64, r.sifted_count)} bits.")
    for col, label, bits in zip(st.columns(2), ["Alice's sifted key", "Bob's sifted key"], [r.alice_sifted, r.bob_sifted]):
        with col:
            st.markdown(f"**{label}**")
            if not r.sifted_count:
                st.info("No sifted bits available.")
            else:
                spans = []
                for i, bit in enumerate(bits[:64]):
                    mismatch = r.alice_sifted[i] != r.bob_sifted[i]
                    cls = "keybit keyerror" if mismatch else "keybit"
                    status = "Mismatch" if mismatch else "Match"
                    spans.append(f'<span class="{cls}" title="Sifted position {i+1}: {status}">{int(bit)}{"≠" if mismatch else "="}</span>')
                st.markdown('<div class="keyline">' + ''.join(spans) + '</div>', unsafe_allow_html=True)
    st.caption("= matching bit · ≠ mismatching bit (also marked with a stronger border).")
    with st.expander("Inspect the complete sifted keys"):
        st.dataframe(r.sifted_table(), hide_index=True, use_container_width=True, height=400)
    st.warning("A sifted key is not automatically a final secure cryptographic key. Practical QKD needs further classical post-processing.")

with analysis:
    st.subheader("QBER analysis")
    st.latex(r"\mathrm{QBER}=\frac{\text{Mismatched sifted bits}}{\text{Total sifted bits}}\times100\%")
    st.write(f"Numerator: **{r.mismatch_count:,} mismatched sifted bits** · Denominator: **{r.sifted_count:,} sifted bits**")
    st.metric("Measured QBER", "N/A" if r.qber is None else f"{r.qber:.2f}%")
    if r.qber is None:
        st.info("No sifted bits available. QBER cannot be calculated.")
    elif r.mismatch_count:
        st.warning("Errors detected. The observed error rate is consistent with possible channel disturbance, including an intercept-resend attack. QBER alone does not uniquely identify the cause of errors.")
    else:
        st.success("No errors observed in the sifted key. This result applies to the ideal simulation model and does not prove that a real communication channel is secure.")
    st.caption("Eve OFF yields exactly 0% whenever the key is nonempty. Eve ON approaches an expected 25% over large samples; each finite experiment can vary. About 50% of positions survive independent basis selection, also with statistical variation.")
    left, right = st.columns(2)
    left.plotly_chart(sifted_bit_agreement(r), use_container_width=True)
    right.plotly_chart(sifting_efficiency(r), use_container_width=True)

with comparison:
    st.subheader("Eve ON / OFF comparison")
    st.write(f"Run two separate {r.n_bits:,}-bit experiments using independent random streams. This comparison uses the completed experiment's bit count and seed, shown above.")
    if st.button("Run Eve ON/OFF comparison", type="primary"):
        st.session_state.comparison = compare_eve_conditions(r.n_bits, r.seed)
        st.session_state.comparison_config = (r.n_bits, r.seed)
    if "comparison" in st.session_state:
        pair = st.session_state.comparison
        st.plotly_chart(qber_comparison(pair), use_container_width=True)
        st.dataframe(comparison_table(pair), hide_index=True, use_container_width=True)
        st.caption("Bars show observed QBER, not assigned theoretical values. Hover to see sifted-bit and mismatch counts. The dotted line is the 25% full-attack expectation. Independent runs can retain different numbers of bits. New main experiments clear this comparison.")
    else:
        st.info("Select Run Eve ON/OFF comparison to generate measured results for both conditions.")

with exports:
    st.subheader("Simulation summary")
    st.write(r.summary())
    st.subheader("Export actual results")
    prefix = f"bb84_{r.n_bits}_eve_{'on' if r.eve_enabled else 'off'}"
    st.download_button("Full transmission table (CSV)", table.to_csv(index=False).encode("utf-8-sig"), f"{prefix}_transmissions.csv", "text/csv")
    for label, bits in [("Alice", r.alice_sifted), ("Bob", r.bob_sifted)]:
        st.download_button(f"{label}'s complete sifted key (TXT)", ''.join(str(int(b)) for b in bits) + '\n', f"{prefix}_{label.lower()}_key.txt", "text/plain")
    st.download_button("Experiment summary and configuration (JSON)", r.report_json(), f"{prefix}_report.json", "application/json")
    if "comparison" in st.session_state:
        st.download_button("Paired Eve comparison (CSV)", comparison_table(st.session_state.comparison).to_csv(index=False), f"{prefix}_comparison.csv", "text/csv")
    st.caption("Exports contain complete simulated results. Revealing sifted bits is suitable for this teaching model; publicly disclosed test bits must be removed in practical QKD.")
