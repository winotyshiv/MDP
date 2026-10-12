"""Interactive Plotly figures using computed experiment results only."""
import numpy as np
import plotly.graph_objects as go
from bb84_simulator import SimulationResult

TEAL = "#087F8C"
ORANGE = "#C65D21"
GRAY = "#94A3B8"


def _style(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(title=title, template="plotly_white", font=dict(family="Arial", size=13),
                      margin=dict(l=35, r=25, t=65, b=45), height=330,
                      paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-.2))
    return fig


def qber_comparison(results: tuple[SimulationResult, SimulationResult]) -> go.Figure:
    """Actual QBER bars; unavailable values have annotations and no fabricated bar."""
    labels = ["Eve ON" if r.eve_enabled else "Eve OFF" for r in results]
    fig = go.Figure(go.Bar(x=labels, y=[r.qber for r in results],
        text=["N/A" if r.qber is None else f"{r.qber:.2f}%" for r in results],
        textposition="outside", marker_color=[ORANGE if r.eve_enabled else TEAL for r in results],
        customdata=[[r.sifted_count, r.mismatch_count] for r in results],
        hovertemplate="%{x}<br>QBER: %{y:.2f}%<br>Sifted bits: %{customdata[0]}<br>Mismatches: %{customdata[1]}<extra></extra>"))
    for label, r in zip(labels, results):
        if r.qber is None:
            fig.add_annotation(x=label, y=3, text="N/A · no sifted bits", showarrow=False)
    fig.add_hline(y=25, line_dash="dot", line_color=ORANGE,
                  annotation_text="Full attack expectation: 25%", annotation_position="top right")
    fig.update_yaxes(title="Quantum Bit Error Rate (QBER, %)", range=[0, 110], ticksuffix="%")
    fig.update_xaxes(title="Independent experiment condition")
    return _style(fig, "Measured QBER · Eve OFF vs Eve ON")


def sifted_bit_agreement(result: SimulationResult) -> go.Figure:
    """Counts of matching and mismatching sifted bits, including empty keys."""
    counts = [result.sifted_count - result.mismatch_count, result.mismatch_count]
    fig = go.Figure(go.Bar(x=["Matching bits", "Mismatched bits"], y=counts,
        text=counts, textposition="outside", marker_color=[TEAL, ORANGE]))
    fig.update_xaxes(title="Sifted-key outcome")
    fig.update_yaxes(title="Number of sifted bits", range=[0, max(1, max(counts) * 1.2)])
    return _style(fig, "Agreement after sifting")


def sifting_efficiency(result: SimulationResult) -> go.Figure:
    """Measured retained/discarded positions, rather than forced 50% statistics."""
    counts = [result.sifted_count, result.n_bits - result.sifted_count]
    fig = go.Figure(go.Bar(x=["Retained", "Discarded"], y=counts, text=counts,
                          textposition="outside", marker_color=[TEAL, GRAY]))
    fig.update_yaxes(title="Number of transmitted positions", range=[0, max(counts) * 1.2])
    fig.update_xaxes(title="Basis reconciliation outcome")
    return _style(fig, f"Sifting efficiency · {result.metrics['sifting_efficiency_percent']:.2f}%")


def transmission_preview(result: SimulationResult, limit: int = 32) -> go.Figure:
    """Aligned heatmap with explicit text and hover labels for a small event preview."""
    if limit <= 0:
        raise ValueError("Preview limit must be positive.")
    size = min(limit, result.n_bits)
    rows = [("Alice bit", result.alice_bits[:size]), ("Alice basis", result.alice_bases[:size])]
    if result.eve_enabled:
        rows.extend([("Eve basis", result.eve_bases[:size]), ("Eve result", result.eve_bits[:size])])
    rows.extend([("Bob basis", result.bob_bases[:size]), ("Bob result", result.bob_bits[:size]),
                 ("Sifting", np.where(result.matching_basis[:size], "Keep", "Drop")),
                 ("Sifted outcome", np.where(~result.matching_basis[:size], "—",
                    np.where(result.alice_bits[:size] == result.bob_bits[:size], "=", "≠")))])
    text = [[str(v) for v in values] for _, values in rows]
    z = [[{"0": 0, "1": 1, "Z": 0, "X": 1, "Keep": 0, "Drop": 2, "=": 0, "≠": 1, "—": 2}[v]
          for v in values] for values in text]
    fig = go.Figure(go.Heatmap(z=z, text=text, texttemplate="%{text}",
        x=list(range(1, size + 1)), y=[name for name, _ in rows], xgap=2, ygap=2,
        colorscale=[[0, "#D2EEED"], [.49, "#D2EEED"], [.5, "#F8DDC5"], [.74, "#F8DDC5"], [.75, "#E7ECF2"], [1, "#E7ECF2"]],
        zmin=0, zmax=2, showscale=False,
        hovertemplate="Position %{x}<br>%{y}: %{text}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Transmission position", dtick=1)
    return _style(fig, f"First {size} transmissions · Keep / Drop; = match / ≠ mismatch")
