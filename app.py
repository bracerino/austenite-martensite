import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from crystallography import (
    Lattice,
    build_correspondence,
    caglioti_fwhm,
    d_to_twotheta,
    gaussian,
    lorentzian,
    pearson_vii,
    pseudo_voigt,
)
from seo import inject_seo_metadata

inject_seo_metadata()

st.set_page_config(
    page_title="NiTiHf Lattice Correspondence",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem;}
    /* Tabs styled as in XRDlicious. Streamlit >= 1.5x renders tabs with React Aria
       ([data-testid="stTab"], [data-selected]) instead of BaseWeb buttons. */
    .stTabs [role="tablist"] {gap: 20px !important; padding: 4px 2px 10px 2px !important;}
    .stTabs [role="tablist"]::after {display: none !important;}
    .stTabs [data-testid="stTab"] {
        height: auto !important; min-height: 2.9rem; padding: 8px 18px !important;
        background-color: #f0f4ff !important; border-radius: 12px !important; border: none !important;
        color: #1e3a8a !important; transition: all 0.3s ease !important;
    }
    .stTabs [data-testid="stTab"] p {
        font-size: 1.15rem !important; color: #1e3a8a !important; font-weight: 600 !important; margin: 0 !important;
    }
    .stTabs [data-testid="stTab"][data-hovered], .stTabs [data-testid="stTab"]:hover {
        background-color: #dbe5ff !important;
    }
    .stTabs [data-testid="stTab"][data-selected], .stTabs [data-testid="stTab"][aria-selected="true"] {
        background-color: #e0e7ff !important; box-shadow: 0 2px 6px rgba(30, 58, 138, 0.3) !important;
    }
    .stTabs [data-testid="stTab"][data-selected] p {font-weight: 700 !important;}
    .stTabs [data-testid="stTab"] .react-aria-SelectionIndicator {display: none !important;}
    /* Search-direction switcher (st.segmented_control, key="direction"): stacked, prominent buttons.
       Streamlit >= 1.5x renders it as a React Aria toggle group: buttons carry
       data-variant="segmented_control" and [data-selected] when active. */
    .st-key-direction [data-testid="stWidgetLabel"] p {
        font-size: 1.15rem !important; font-weight: 700 !important; color: #1e3a8a !important;
    }
    .st-key-direction [data-testid="stButtonGroup"] > div:has(> [data-variant="segmented_control"]) {
        display: flex !important; flex-direction: column !important; align-items: stretch !important;
        gap: 8px !important; width: 100% !important; overflow: visible !important;
    }
    .st-key-direction [data-variant="segmented_control"] {
        width: 100% !important; justify-content: flex-start !important; margin: 0 !important;
        min-height: 3rem !important; padding: 10px 18px !important;
        border: 2px solid #1e3a8a !important; border-radius: 12px !important;
        background-color: #f0f4ff !important; color: #1e3a8a !important; transition: all 0.2s ease !important;
    }
    .st-key-direction [data-variant="segmented_control"]:hover {background-color: #dbe5ff !important;}
    .st-key-direction [data-variant="segmented_control"][data-selected] {
        background-color: #1e3a8a !important; color: #ffffff !important;
        box-shadow: 0 3px 8px rgba(30, 58, 138, 0.35) !important;
    }
    .st-key-direction [data-variant="segmented_control"] p,
    .st-key-direction [data-variant="segmented_control"] span {
        font-size: 1.1rem !important; font-weight: 700 !important; color: inherit !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

A_COLOR = "#3498db"
M_COLOR = "#e74c3c"

# Martensite lattice in the standard B19' setting: unique axis b, beta = angle between a and c.
# Lattice correspondence: a_M || [100]_B2, b_M || [011]_B2, c_M || [0-11]_B2.
PRESETS = {
    "NiTiHf — B2 / B19'": {
        "a0": 3.096, "a": 3.059, "b": 4.079, "c": 4.890, "beta": 103.5,
        "source": "Parameters used for the original NiTiHf correspondence table "
                  "(hkl_corresp_table_NiTiHf_extended.xlsx).",
    },
    "NiTi — B2 / B19'": {
        "a0": 3.015, "a": 2.898, "b": 4.108, "c": 4.646, "beta": 97.78,
        "source": "B2: Otsuka & Ren, Prog. Mater. Sci. 50 (2005) 511. "
                  "B19': Kudoh et al., Acta Metall. 33 (1985) 2049.",
    },
}
CUSTOM = "Custom"
LATTICE_KEYS = ("a0", "a", "b", "c", "beta")

WAVELENGTHS = {
    "Cu Kα₁ (1.5406 Å)": 1.5406,
    "Mo Kα₁ (0.7093 Å)": 0.7093,
    "Cr Kα₁ (2.2897 Å)": 2.2897,
    "Fe Kα₁ (1.9360 Å)": 1.9360,
    "Co Kα₁ (1.7889 Å)": 1.7889,
    "Ag Kα₁ (0.5594 Å)": 0.5594,
    "Custom": None,
}

# Shared plot styling (large fonts for readability and for figures exported to papers/slides)
PLOT_FONT = dict(size=24, family="Arial")
AXIS_STYLE = dict(title_font=dict(size=30), tickfont=dict(size=24), showline=False, mirror=False,
                  ticks="outside", ticklen=8, gridcolor="rgba(128,128,128,0.25)")
LEGEND_FONT = dict(size=24)
HOVER_STYLE = dict(font_size=22)

PROFILES = ["Sticks only", "Gaussian", "Lorentzian", "Pseudo-Voigt", "Pearson VII"]

# ----------------------------------------------------------------------------------------------
# Session state helpers
# ----------------------------------------------------------------------------------------------


def _apply_preset():
    preset = PRESETS.get(st.session_state["preset"])
    if preset is not None:
        for k in LATTICE_KEYS:
            st.session_state[f"lat_{k}"] = preset[k]


if "preset" not in st.session_state:
    st.session_state["preset"] = next(iter(PRESETS))
    _apply_preset()


def _mark_custom():
    preset = PRESETS.get(st.session_state["preset"])
    if preset is not None and any(
        not np.isclose(st.session_state[f"lat_{k}"], preset[k]) for k in LATTICE_KEYS
    ):
        st.session_state["preset"] = CUSTOM


@st.cache_data(show_spinner="Computing lattice correspondence…")
def get_correspondence(a0, a, b, c, beta, max_index):
    return build_correspondence(Lattice(a0, a0, a0), Lattice(a, b, c, 90.0, beta, 90.0), max_index)


# ----------------------------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------------------------

with st.sidebar:
    st.title("🔬 Lattice Viewer")
    st.caption(
        "Crystallographic correspondence between B2 austenite and B19' martensite. "
        "Visit also our main app **[XRDlicious](https://xrdlicious.com)**. "
        "Bugs & suggestions: **lebedmi2@cvut.cz**"
    )

    st.subheader("Diffraction & display")
    wl_label = st.selectbox("X-ray wavelength", list(WAVELENGTHS), index=0)
    wavelength = WAVELENGTHS[wl_label]
    if wavelength is None:
        wavelength = st.number_input("Wavelength λ (Å)", min_value=0.1, max_value=5.0, value=1.5406,
                                     step=0.0001, format="%.4f")
    max_display = st.number_input("Max. rows to display", min_value=5, max_value=500, value=50, step=5)

    st.subheader("Lattice parameters")
    st.selectbox(
        "Preset",
        list(PRESETS) + [CUSTOM],
        key="preset",
        on_change=_apply_preset,
        help="Pick a predefined alloy or edit the values below to define your own lattice.",
    )
    if st.session_state["preset"] in PRESETS:
        st.caption(PRESETS[st.session_state["preset"]]["source"])
    else:
        st.caption("Custom lattice — edit any value below.")

    st.markdown(f"**<span style='color:{A_COLOR}'>Austenite B2</span>** · Pm-3m (221)", unsafe_allow_html=True)
    st.number_input("a₀ (Å)", key="lat_a0", min_value=1.0, max_value=10.0, step=0.001, format="%.4f",
                    on_change=_mark_custom)

    st.markdown(f"**<span style='color:{M_COLOR}'>Martensite B19'</span>** · P2₁/m (11), unique axis b",
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.number_input("a (Å)", key="lat_a", min_value=1.0, max_value=10.0, step=0.001, format="%.4f",
                    on_change=_mark_custom)
    c2.number_input("b (Å)", key="lat_b", min_value=1.0, max_value=10.0, step=0.001, format="%.4f",
                    on_change=_mark_custom)
    c1.number_input("c (Å)", key="lat_c", min_value=1.0, max_value=10.0, step=0.001, format="%.4f",
                    on_change=_mark_custom)
    c2.number_input("β (°)", key="lat_beta", min_value=60.0, max_value=150.0, step=0.01, format="%.2f",
                    on_change=_mark_custom, help="Set β = 90° for orthorhombic B19 martensite.")

    st.subheader("Options")
    max_index = st.slider("Max. martensite Miller index |h|, |k|, |l|", 2, 6, 4,
                          help="Range of martensite planes included in the correspondence search.")
    only_diffracting = st.toggle(
        "Only reflections that can diffract", value=False,
        help="Hide austenite planes with half-integer indices (they do not diffract in B2) and "
             "martensite 0k0 reflections with odd k (extinct in P2₁/m).",
    )

lat = {k: float(st.session_state[f"lat_{k}"]) for k in LATTICE_KEYS}
df = get_correspondence(lat["a0"], lat["a"], lat["b"], lat["c"], lat["beta"], max_index)

# ----------------------------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------------------------

st.title("Austenite ↔ Martensite Correspondence")

v_a = lat["a0"] ** 3  # B2 cell = 1 formula unit
v_m = lat["a"] * lat["b"] * lat["c"] * np.sin(np.radians(lat["beta"])) / 2  # B19' cell = 2 formula units
DIRECTIONS = ["🔵 Austenite → 🔴 Martensite", "🔴 Martensite → 🔵 Austenite"]
c_dir, m1, m2, m3, m4 = st.columns([1.5, 1, 1, 1, 1], vertical_alignment="center")
with c_dir:
    direction = st.segmented_control("🔁 Search direction", DIRECTIONS, default=DIRECTIONS[0], key="direction",
                                     help="Choose which phase you pick a reflection from.")
    direction = direction or DIRECTIONS[0]
m1.metric("B2 volume / f.u.", f"{v_a:.3f} Å³")
m2.metric("B19' volume / f.u.", f"{v_m:.3f} Å³")
m3.metric("Volume change ΔV/V", f"{(v_m - v_a) / v_a * 100:+.2f} %")
m4.metric("Monoclinic shear (β − 90°)", f"{lat['beta'] - 90:.2f}°")

# ----------------------------------------------------------------------------------------------
# Search controls
# ----------------------------------------------------------------------------------------------

c_refl, c_ang = st.columns([2.5, 1.5])

if direction == DIRECTIONS[1]:
    search, result = "martensite", "austenite"
    s_label, r_label, s_d, r_d = "Martensite", "Austenite", "dM", "dA"
    s_color, r_color = M_COLOR, A_COLOR
    s_allowed, r_allowed = "allowed_M", "allowed_A"
    default_refl = "(-1 1 1)"
else:
    search, result = "austenite", "martensite"
    s_label, r_label, s_d, r_d = "Austenite", "Martensite", "dA", "dM"
    s_color, r_color = A_COLOR, M_COLOR
    s_allowed, r_allowed = "allowed_A", "allowed_M"
    default_refl = "(1 1 0)"

pool = df[df[s_allowed] & df[r_allowed]] if only_diffracting else df
choices = (pool.groupby(search)[s_d].first().sort_values(ascending=False))
d_lookup = choices.to_dict()

with c_refl:
    options = list(choices.index)
    sel_key = f"refl_{search}"
    if st.session_state.get(sel_key) not in options:
        st.session_state[sel_key] = default_refl if default_refl in options else options[0]

    def _fmt(lbl):
        tt = float(d_to_twotheta(d_lookup[lbl], wavelength))
        tt_txt = f"2θ = {tt:.2f}°" if np.isfinite(tt) else "2θ: out of range"
        return f"{lbl}   ·   d = {d_lookup[lbl]:.4f} Å   ·   {tt_txt}"

    selected = st.selectbox(
        f"{s_label} reflection (h k l) — sorted by d-spacing", options, key=sel_key, format_func=_fmt,
        help="Type to search, e.g. '1 1 0'.",
    )

with c_ang:
    min_angle, max_angle = st.slider(
        "Angle between plane normals (°)", 0.0, 30.0, (0.0, 15.0), step=0.5,
        help="Keep only correspondences whose plane normals are within this angular range.",
    )

sel = pool[(pool[search] == selected) & pool["angle"].between(min_angle, max_angle)].copy()
sel_d = d_lookup[selected]
sel_tt = float(d_to_twotheta(sel_d, wavelength))
sel["2θ_r"] = d_to_twotheta(sel[r_d].to_numpy(), wavelength)
sel["d2θ"] = sel["2θ_r"] - sel_tt
sel = sel.sort_values(["angle", r_d], ascending=[True, False])

if sel.empty:
    st.warning(
        f"No corresponding {r_label.lower()} planes for {selected} with the angle between normals in "
        f"{min_angle}°–{max_angle}°. Widen the angle range or switch off 'Only reflections that can diffract'."
    )
    st.stop()

# Summary for the selected reflection
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"{s_label} {selected}", f"d = {sel_d:.4f} Å")
k2.metric("Peak position", f"2θ = {sel_tt:.3f}°" if np.isfinite(sel_tt) else "out of range")
k3.metric(f"Corresponding {r_label.lower()} planes", f"{len(sel)}",
          help=f"{sel[result].nunique()} distinct planes, {sel[r_d].round(5).nunique()} distinct d-spacings")
closest = sel.loc[sel["d2θ"].abs().idxmin()] if sel["d2θ"].notna().any() else None
k4.metric("Smallest peak shift Δ2θ", f"{closest['d2θ']:+.3f}°" if closest is not None else "—",
          help=f"Between {selected} and {closest[result]}" if closest is not None else None)

tab_table, tab_xrd, tab_d = st.tabs(
    ["📋 Correspondence table", "📈 Diffraction peaks", "📊 d-spacing comparison"],
    key="main_tab",
)

# ----------------------------------------------------------------------------------------------
# Tab 1: correspondence table
# ----------------------------------------------------------------------------------------------

with tab_table:
    shown = sel.head(int(max_display))
    st.caption(f"Showing {len(shown)} of {len(sel)} correspondences · click a column header to sort.")

    table = pd.DataFrame({
        f"{s_label} (hkl)": shown[search],
        f"{r_label} (hkl)": shown[result],
        "Variant": shown["variant"],
        "Mult. M": shown["mult_M"],
        "Mult. A": shown["mult_A"],
        "d M (Å)": shown["dM"],
        "d A (Å)": shown["dA"],
        f"2θ {r_label[0]} (°)": shown["2θ_r"],
        "Δ2θ (°)": shown["d2θ"],
        "Angle (°)": shown["angle"],
        "Normal strain (%)": shown["strain"],
        "Shear strain (%)": shown["strain_shear"],
        "Diffracts": shown[r_allowed],
    })

    smax = max(df["strain"].abs().max(), 1e-9)

    def _strain_bg(v):
        alpha = min(abs(v) / smax, 1.0) * 0.6
        rgb = "39,174,96" if v >= 0 else "231,76,60"
        return f"background-color: rgba({rgb},{alpha:.2f})"

    def _angle_color(v):
        return f"color: {'#27ae60' if v < 5 else '#f39c12' if v < 10 else '#e74c3c'}; font-weight: 600"

    styled = (
        table.style
        .map(_strain_bg, subset=["Normal strain (%)"])
        .map(_angle_color, subset=["Angle (°)"])
        .map(lambda _: f"color: {A_COLOR}; font-weight: 600", subset=["Austenite (hkl)"])
        .map(lambda _: f"color: {M_COLOR}; font-weight: 600", subset=["Martensite (hkl)"])
        .format({"d M (Å)": "{:.4f}", "d A (Å)": "{:.4f}", f"2θ {r_label[0]} (°)": "{:.3f}",
                 "Δ2θ (°)": "{:+.3f}", "Angle (°)": "{:.2f}", "Normal strain (%)": "{:+.2f}",
                 "Shear strain (%)": "{:.2f}"}, na_rep="—")
    )
    st.dataframe(
        styled, hide_index=True,
        column_config={
            "Variant": st.column_config.NumberColumn(help="Lattice correspondence variant (1–12)"),
            "Δ2θ (°)": st.column_config.NumberColumn(help=f"2θ({r_label}) − 2θ({s_label} {selected})"),
            "Angle (°)": st.column_config.NumberColumn(
                help="Angle between the martensite and austenite plane normals"),
            "Normal strain (%)": st.column_config.NumberColumn(help="(d_M − d_A) / d_A × 100"),
            "Shear strain (%)": st.column_config.NumberColumn(help="Angle between normals in radians × 100"),
            "Diffracts": st.column_config.CheckboxColumn(
                help=f"Whether this {r_label.lower()} plane gives a diffraction peak"),
        },
    )
    st.download_button(
        "⬇️ Download all correspondences (CSV)",
        sel.drop(columns=["hkl_M", "hkl_A"]).to_csv(index=False).encode(),
        file_name=f"correspondence_{search}_{selected.strip('()').replace(' ', '_')}.csv",
        mime="text/csv",
    )

# ----------------------------------------------------------------------------------------------
# Tab 2: diffraction peaks
# ----------------------------------------------------------------------------------------------

with tab_xrd:
    peaks = [{"phase": s_label, "hkl": selected, "d": sel_d, "2θ": sel_tt}]
    for d_val, grp in sel.groupby(sel[r_d].round(6)):
        peaks.append({"phase": r_label, "hkl": ", ".join(sorted(grp[result].unique())), "d": d_val,
                      "2θ": float(d_to_twotheta(d_val, wavelength)),
                      "allowed": bool(grp[r_allowed].any())})
    peaks = [p for p in peaks if np.isfinite(p["2θ"])]
    if len(peaks) < 2:
        st.info("The corresponding peaks are outside the measurable 2θ range for this wavelength.")

    plot_slot = st.container()  # the plot is drawn here, above its settings

    settings = st.container(border=True)
    settings.markdown("**⚙️ Peak profile settings**")
    o1, o2, o3, o4 = settings.columns(4)
    profile = o1.selectbox("Peak shape", PROFILES, index=PROFILES.index("Pseudo-Voigt"),
                           help="Draw each peak as a modelled profile instead of a vertical line.")
    width_mode = o2.radio("Peak width", ["Constant FWHM", "Caglioti (U, V, W)"], index=1, horizontal=True,
                          help="Caglioti U, V, W describe the instrumental broadening of a diffractometer "
                               "(optics, slits, wavelength spread), not of a material. They are normally refined "
                               "from a line-profile standard such as NIST LaB₆ (SRM 660) or Si (SRM 640) measured "
                               "on the same instrument. Sample effects (crystallite size, microstrain, defects) "
                               "add extra broadening on top — martensite peaks are typically broader.",
                          disabled=profile == PROFILES[0])
    show_sticks = o3.toggle("Show stick positions", value=True)
    zoom = o4.toggle("Zoom to peaks", value=True)

    p1, p2, p3, p4 = settings.columns(4)
    if width_mode == "Constant FWHM":
        fwhm_const = p1.number_input("FWHM (° 2θ)", 0.005, 5.0, 0.15, 0.01, format="%.3f",
                                     disabled=profile == PROFILES[0])
        fwhm_of = lambda tt: np.full_like(np.asarray(tt, float), fwhm_const)
    else:
        u = p1.number_input("U", -1.0, 1.0, 0.01, 0.001, format="%.4f")
        v = p2.number_input("V", -1.0, 1.0, -0.005, 0.001, format="%.4f")
        w = p3.number_input("W", 0.0, 1.0, 0.005, 0.001, format="%.4f")
        fwhm_of = lambda tt: caglioti_fwhm(tt, u, v, w)
    shape_param = None
    if profile == "Pseudo-Voigt":
        shape_param = p4.slider("η (Lorentzian fraction)", 0.0, 1.0, 0.5, 0.05)
    elif profile == "Pearson VII":
        shape_param = p4.slider("m (shape exponent)", 1.0, 10.0, 1.5, 0.1,
                                help="m = 1 → Lorentzian, m → ∞ → Gaussian")

    tts = np.array([p["2θ"] for p in peaks])
    if zoom and len(tts):
        margin = max(2.0, 0.15 * (tts.max() - tts.min()))
        x_range = [max(0.0, tts.min() - margin), min(180.0, tts.max() + margin)]
    else:
        x_range = [5.0, 160.0]

    fig = go.Figure()
    if profile != PROFILES[0]:
        x = np.linspace(x_range[0], x_range[1], 4000)
        for phase, color in [(s_label, s_color), (r_label, r_color)]:
            y = np.zeros_like(x)
            for p in (p for p in peaks if p["phase"] == phase):
                fw = float(fwhm_of(p["2θ"]))
                if profile == "Gaussian":
                    y += gaussian(x, p["2θ"], fw)
                elif profile == "Lorentzian":
                    y += lorentzian(x, p["2θ"], fw)
                elif profile == "Pseudo-Voigt":
                    y += pseudo_voigt(x, p["2θ"], fw, shape_param)
                else:
                    y += pearson_vii(x, p["2θ"], fw, shape_param)
            fig.add_trace(go.Scatter(x=x, y=100 * y, mode="lines", name=f"{phase} ({profile})",
                                     line=dict(color=color, width=2.5), fill="tozeroy",
                                     opacity=0.6, hoverinfo="skip"))

    if show_sticks or profile == PROFILES[0]:
        for phase, color in [(s_label, s_color), (r_label, r_color)]:
            xs, ys, hov = [], [], []
            for p in (p for p in peaks if p["phase"] == phase):
                ht = (f"<b>{phase}</b> {p['hkl']}<br>2θ = {p['2θ']:.3f}°<br>d = {p['d']:.4f} Å"
                      f"<br>Δ2θ = {p['2θ'] - sel_tt:+.3f}°")
                xs += [p["2θ"], p["2θ"], None]
                ys += [0, 100, None]
                hov += [ht, ht, None]
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=f"{phase} positions",
                                     line=dict(color=color, width=2 if profile != PROFILES[0] else 3,
                                               dash="dot" if profile != PROFILES[0] else "solid"),
                                     hovertext=hov, hoverinfo="text"))

    for i, p in enumerate(peaks[:20]):
        is_sel = p["phase"] == s_label
        lbl = p["hkl"] if len(p["hkl"]) < 30 else p["hkl"][:27] + "…"
        fig.add_annotation(x=p["2θ"], y=100, text=f"{p['phase'][0]}: {lbl}", showarrow=True, arrowhead=2,
                           ax=0, ay=-40 - 34 * (i % 3), font=dict(color=s_color if is_sel else r_color, size=22),
                           bgcolor="rgba(255,255,255,0.85)", arrowcolor=s_color if is_sel else r_color)

    fig.update_layout(
        height=800, margin=dict(t=150, b=170, l=110, r=30),
        xaxis=dict(title="2θ (°)", range=x_range, **AXIS_STYLE),
        yaxis=dict(title="Normalised intensity", range=[0, 130] if profile == PROFILES[0] else None,
                   **AXIS_STYLE),
        legend=dict(orientation="h", yanchor="top", y=-0.16, xanchor="center", x=0.5, font=LEGEND_FONT),
        hovermode="closest", hoverlabel=HOVER_STYLE,
        font=PLOT_FONT,
    )
    plot_slot.plotly_chart(fig, config={"toImageButtonOptions": {"format": "png", "scale": 3}})
    plot_slot.caption(
        f"λ = {wavelength:.4f} Å, Bragg's law λ = 2d sin θ. All peaks have the same height — intensities "
        "(structure factors, texture, phase fractions) are not modelled; the figure shows positions and "
        "peak overlap only."
    )

    peak_df = pd.DataFrame([{
        "Phase": p["phase"], "Reflection(s)": p["hkl"], "d (Å)": p["d"], "2θ (°)": p["2θ"],
        "Δ2θ vs selected (°)": p["2θ"] - sel_tt, "FWHM (°)": float(fwhm_of(p["2θ"])) if profile != PROFILES[0] else None,
    } for p in sorted(peaks, key=lambda p: p["2θ"])])
    st.dataframe(peak_df.style.format({"d (Å)": "{:.4f}", "2θ (°)": "{:.3f}", "Δ2θ vs selected (°)": "{:+.3f}",
                                       "FWHM (°)": "{:.3f}"}, na_rep="—")
                 .map(lambda ph: f"color: {A_COLOR if ph == 'Austenite' else M_COLOR}; font-weight: 600",
                      subset=["Phase"]),
                 hide_index=True)

# ----------------------------------------------------------------------------------------------
# Tab 3: d-spacing comparison
# ----------------------------------------------------------------------------------------------

with tab_d:
    bars = sel.drop_duplicates(result).head(30)
    fig_d = go.Figure()
    fig_d.add_trace(go.Bar(x=[selected], y=[sel_d], name=s_label, marker_color=s_color,
                           text=[f"{sel_d:.3f}"], textposition="outside", textfont=dict(size=22)))
    fig_d.add_trace(go.Bar(x=bars[result], y=bars[r_d], name=r_label, marker_color=r_color,
                           text=[f"{d:.3f}" for d in bars[r_d]], textposition="outside", textfont=dict(size=22),
                           customdata=np.stack([bars["angle"], bars["strain"]], axis=1),
                           hovertemplate="%{x}<br>d = %{y:.4f} Å<br>angle = %{customdata[0]:.2f}°"
                                         "<br>strain = %{customdata[1]:+.2f} %<extra></extra>"))
    fig_d.add_hline(y=sel_d, line_dash="dash", line_color=s_color, opacity=0.6)
    fig_d.update_layout(
        height=760, margin=dict(t=60, b=240, l=110, r=30),
        yaxis=dict(title="d-spacing (Å)", range=[0, max(sel_d, bars[r_d].max()) * 1.25], **AXIS_STYLE),
        xaxis=dict(title="Reflection", tickangle=-45, **AXIS_STYLE), font=PLOT_FONT,
        legend=dict(orientation="h", yanchor="top", y=-0.36, xanchor="center", x=0.5, font=LEGEND_FONT),
        hoverlabel=HOVER_STYLE,
    )
    st.plotly_chart(fig_d)
    st.caption(f"Showing up to 30 distinct {r_label.lower()} planes. Dashed line = d of the selected "
               f"{s_label.lower()} reflection.")
