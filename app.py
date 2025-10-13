import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import numpy as np

st.set_page_config(layout="wide", page_title="NiTiHf Lattice Correspondence & Diffraction Viewer")

AUSTENITE = {
    'name': 'B2 Austenite',
    'space_group': 'Pm-3m (221)',
    'a': 3.096,
    'b': 3.096,
    'c': 3.096,
    'alpha': 90,
    'beta': 90,
    'gamma': 90,
    'structure': 'Cubic',
}

MARTENSITE = {
    'name': 'B19\' Martensite',
    'space_group': 'P2₁/m (11)',
    'a': 2.974,
    'b': 4.079,
    'c': 4.755,
    'alpha': 90,
    'beta': 96.62,
    'gamma': 90,
    'structure': 'Monoclinic',
}


def format_hkl(hkl_string):
    try:
        hkl_string = str(hkl_string).strip()
        hkl_string = hkl_string.replace('(', '').replace(')', '')
        values = [float(x.strip()) for x in hkl_string.split(',')]
        formatted = []
        for v in values:
            if v == int(v):
                formatted.append(str(int(v)))
            else:
                formatted.append(str(v))
        return f"({', '.join(formatted)})"
    except:
        return hkl_string


@st.cache_data
def load_data():
    try:
        df = pd.read_excel('hkl_corresp_table_NiTiHf_extended.xlsx', sheet_name='Lattice correspondance')

        column_mapping = {
            'Martensite planes (h,k,l)': 'martensite',
            ' Multiplicity of martensite planes': 'mult_M',
            'Corresponding austenite planes (h,k,l)': 'austenite',
            'Multiplicity of austenite planes': 'mult_A',
            'Martensite planes spacing dMhkl [A]': 'dM',
            'Austenite planes spacing dAhkl [A]': 'dA',
            'Angle between normals of martensite and corresponding austenite planes [deg.]': 'angle',
            'Normal transformation strain (dAhkl - dMhkl)/dAhkl*100 [%]': 'strain_normal',
            'Shear transformation strain [%]': 'strain_shear',
        }

        existing_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=existing_cols)

        if 'Transformation strain (dAhkl - dMhkl)/dAhkl*100 [%]' in df.columns:
            df = df.rename(columns={'Transformation strain (dAhkl - dMhkl)/dAhkl*100 [%]': 'strain'})
        else:
            df['strain'] = df['strain_normal']

        df['martensite'] = df['martensite'].apply(format_hkl)
        df['austenite'] = df['austenite'].apply(format_hkl)

        return df
    except FileNotFoundError:
        st.error("⚠️ Excel file 'hkl_corresp_table_NiTiHf_extended.xlsx' not found. Please upload the file.")
        return None
    except Exception as e:
        st.error(f"⚠️ Error loading data: {str(e)}")
        return None


def d_to_twotheta(d_spacing, wavelength=1.5406):
    if d_spacing <= 0:
        return None
    sin_theta = wavelength / (2 * d_spacing)
    if abs(sin_theta) > 1:
        return None
    theta = np.arcsin(sin_theta)
    return 2 * np.degrees(theta)


def create_progress_bar(value, min_val, max_val, width=100):
    if pd.isna(value) or min_val is None or max_val is None:
        return ""

    if value >= 0:
        color = "#27ae60"
        if max_val > 0:
            normalized = value / max_val
        else:
            normalized = 0
    else:
        color = "#e74c3c"
        if min_val < 0:
            normalized = abs(value / min_val)
        else:
            normalized = 0

    normalized = max(0, min(1, normalized))
    filled_width = int(normalized * width)

    bar = f'<div style="width:{width}px; height:20px; background-color:#ecf0f1; border-radius:3px; display:inline-block; vertical-align:middle;">' \
          f'<div style="width:{filled_width}px; height:20px; background-color:{color}; border-radius:3px; transition: width 0.3s ease;"></div></div>'

    return bar


st.sidebar.title("NiTiHf Lattice Viewer")
st.sidebar.info(
    "Explore crystallographic correspondence between austenite and martensite phases in NiTiHf shape memory alloy. "
    "Visit main app: **[XRDlicious](https://xrdlicious.com)**. 🌀 Developed by **[IMPLANT team](https://implant.fs.cvut.cz/)**. "
    "Contact for buggs or ideas: **lebedmi2@cvut.cz**."
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔬 Crystal Structures")

with st.sidebar.expander("**Austenite (B2)**", expanded=False):
    st.markdown(f"**Space Group:** {AUSTENITE['space_group']}")
    st.markdown(f"**Structure:** {AUSTENITE['structure']}")
    st.markdown(f"**Lattice Parameters:**")
    st.markdown(f"- a = {AUSTENITE['a']:.3f} Å")
    st.markdown(f"- b = {AUSTENITE['b']:.3f} Å")
    st.markdown(f"- c = {AUSTENITE['c']:.3f} Å")
    st.markdown(f"- α = β = γ = {AUSTENITE['alpha']}°")

with st.sidebar.expander("**Martensite (B19')**", expanded=False):
    st.markdown(f"**Space Group:** {MARTENSITE['space_group']}")
    st.markdown(f"**Structure:** {MARTENSITE['structure']}")
    st.markdown(f"**Lattice Parameters:**")
    st.markdown(f"- a = {MARTENSITE['a']:.3f} Å")
    st.markdown(f"- b = {MARTENSITE['b']:.3f} Å")
    st.markdown(f"- c = {MARTENSITE['c']:.3f} Å")
    st.markdown(f"- α = {MARTENSITE['alpha']}°")
    st.markdown(f"- β = {MARTENSITE['beta']:.2f}°")
    st.markdown(f"- γ = {MARTENSITE['gamma']}°")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Filters & Options")

st.title("🔬 Austenite-Martensite NiTiHf Correspondence")
st.markdown(
    "Interactive visualization of crystallographic plane relationships between austenite and martensite NiTiHf shape memory alloy phases")
st.markdown("---")

df = load_data()

if df is not None:
    col_search, col_angle, col_wave = st.columns([2, 1, 1])

    with col_search:
        search_mode = st.radio(
            "**Search Direction:**",
            options=["Martensite → Austenite", "Austenite → Martensite"],
            horizontal=True,
            help="Choose whether to search by martensite or austenite reflection"
        )

    with col_angle:
        max_angle = st.number_input(
            "**Max Angle (°):**",
            min_value=0.0,
            max_value=90.0,
            value=15.0,
            step=1.0,
            help="Filter by maximum angle between normals"
        )

    with col_wave:
        wavelength_options = {
            "Cu Kα₁ (1.5406 Å)": 1.5406,
            "Mo Kα₁ (0.7093 Å)": 0.7093,
            "Cr Kα₁ (2.2897 Å)": 2.2897,
            "Fe Kα₁ (1.9360 Å)": 1.9360,
            "Co Kα₁ (1.7889 Å)": 1.7889,
            "Ag Kα₁ (0.5594 Å)": 0.5594
        }

        wavelength_label = st.selectbox(
            "**X-ray Wavelength:**",
            options=list(wavelength_options.keys()),
            index=0,
            help="Common X-ray sources:\n"
                 "• Copper (Cu Kα₁): 1.5406 Å\n"
                 "• Molybdenum (Mo Kα₁): 0.7093 Å\n"
                 "• Chromium (Cr Kα₁): 2.2897 Å\n"
                 "• Iron (Fe Kα₁): 1.9360 Å\n"
                 "• Cobalt (Co Kα₁): 1.7889 Å\n"
                 "• Silver (Ag Kα₁): 0.5594 Å"
        )
        wavelength = wavelength_options[wavelength_label]

    if search_mode == "Martensite → Austenite":
        search_column = 'martensite'
        result_column = 'austenite'
        search_label = "Martensite"
        result_label = "Austenite"
        search_d = 'dM'
        result_d = 'dA'
        search_color = '#e74c3c'
        result_color = '#3498db'
    else:
        search_column = 'austenite'
        result_column = 'martensite'
        search_label = "Austenite"
        result_label = "Martensite"
        search_d = 'dA'
        result_d = 'dM'
        search_color = '#3498db'
        result_color = '#e74c3c'

    unique_reflections = sorted(df[search_column].unique())
    selected_reflection = st.selectbox(
        f"**Select {search_label} Reflection (h,k,l):**",
        ["-- Select a reflection --"] + unique_reflections,
        index=0
    )

    if selected_reflection != "-- Select a reflection --":
       # st.markdown("---")

        filtered_df = df[df[search_column] == selected_reflection].copy()
        filtered_df = filtered_df[filtered_df['angle'] <= max_angle]

        global_strain_min = df['strain'].min()
        global_strain_max = df['strain'].max()

        global_shear_min = None
        global_shear_max = None
        if 'strain_shear' in df.columns:
            global_shear_min = df['strain_shear'].min()
            global_shear_max = df['strain_shear'].max()

        if len(filtered_df) == 0:
            st.warning(
                f"No corresponding reflections found with angle ≤ {max_angle}°. Try increasing the maximum angle.")
        else:
            col_opt1, col_opt2, col_opt3 = st.columns(3)
            with col_opt1:
                show_diffraction = st.sidebar.checkbox("Show Diffraction Pattern", value=True)
            with col_opt2:
                combine_graphs = st.sidebar.checkbox("Combine d-spacing bars", value=False)
            with col_opt3:
                max_display = st.sidebar.number_input("Max rows to display", min_value=5, max_value=100, value=20, step=5)

            st.markdown("---")

            st.subheader(f"Correspondence for {search_label} Reflection {selected_reflection}")
            st.markdown(
                f"*Showing {min(len(filtered_df), max_display)} of {len(filtered_df)} reflections with angle ≤ {max_angle}°*")

            with st.expander("📊 Strain Range Information", expanded=False):
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.metric("Global Strain Min", f"{global_strain_min:.2f}%")
                    st.metric("Global Strain Max", f"{global_strain_max:.2f}%")
                with col_info2:
                    if global_shear_min is not None:
                        st.metric("Global Shear Strain Min", f"{global_shear_min:.2f}%")
                        st.metric("Global Shear Strain Max", f"{global_shear_max:.2f}%")

            display_cols = [search_column, result_column, search_d, result_d, 'angle', 'strain']
            if 'mult_M' in filtered_df.columns:
                if search_column == 'martensite':
                    display_cols.insert(1, 'mult_M')
                    display_cols.insert(3, 'mult_A')
                else:
                    display_cols.insert(1, 'mult_A')
                    display_cols.insert(3, 'mult_M')
            if 'strain_shear' in filtered_df.columns:
                display_cols.append('strain_shear')

            display_df = filtered_df[display_cols].head(max_display).copy()

            col_names = {
                'martensite': 'Martensite (h,k,l)',
                'austenite': 'Austenite (h,k,l)',
                'mult_M': 'Mult. M',
                'mult_A': 'Mult. A',
                'dM': 'd-spacing M (Å)',
                'dA': 'd-spacing A (Å)',
                'angle': 'Angle (°)',
                'strain': 'Strain (%)',
                'strain_shear': 'Shear Strain (%)'
            }
            display_df = display_df.rename(columns={k: v for k, v in col_names.items() if k in display_df.columns})

            display_df['Strain Bar'] = display_df['Strain (%)'].apply(
                lambda x: create_progress_bar(x, global_strain_min, global_strain_max, 120)
            )

            if 'Shear Strain (%)' in display_df.columns and global_shear_min is not None:
                display_df['Shear Bar'] = display_df['Shear Strain (%)'].apply(
                    lambda x: create_progress_bar(x, global_shear_min, global_shear_max, 120)
                )

            cols_order = [c for c in display_df.columns if c not in ['Strain Bar', 'Shear Bar']]
            if 'Strain (%)' in cols_order:
                idx = cols_order.index('Strain (%)')
                cols_order.insert(idx + 1, 'Strain Bar')
            if 'Shear Strain (%)' in cols_order and 'Shear Bar' in display_df.columns:
                idx = cols_order.index('Shear Strain (%)')
                cols_order.insert(idx + 1, 'Shear Bar')

            display_df = display_df[cols_order]

            html_table = "<table style='width:100%; border-collapse: collapse; font-size:16px;'>"
            html_table += "<thead><tr style='background-color:#34495e; color:white;'>"
            for col in display_df.columns:
                if col not in ['Strain Bar', 'Shear Bar']:
                    html_table += f"<th style='padding:12px; text-align:center; font-size:18px; font-weight:bold; border:1px solid #ddd;'>{col}</th>"
                else:
                    html_table += f"<th style='padding:12px; text-align:center; font-size:18px; font-weight:bold; border:1px solid #ddd;'>Visual</th>"
            html_table += "</tr></thead><tbody>"

            for idx, row in display_df.iterrows():
                html_table += "<tr style='border-bottom:1px solid #ddd;'>"
                for col in display_df.columns:
                    if col == 'Strain Bar' or col == 'Shear Bar':
                        html_table += f"<td style='padding:10px; text-align:center; border:1px solid #ddd;'>{row[col]}</td>"
                    elif col == 'Angle (°)':
                        val = row[col]
                        if val < 5:
                            color = '#27ae60'
                        elif val < 10:
                            color = '#f39c12'
                        else:
                            color = '#e74c3c'
                        html_table += f"<td style='padding:10px; text-align:center; color:{color}; font-weight:bold; border:1px solid #ddd;'>{val:.2f}</td>"
                    elif col == 'Strain (%)' or col == 'Shear Strain (%)':
                        val = row[col]
                        color = '#27ae60' if val > 0 else '#e74c3c'
                        html_table += f"<td style='padding:10px; text-align:center; color:{color}; font-weight:bold; border:1px solid #ddd;'>{val:.2f}</td>"
                    elif 'd-spacing' in col:
                        html_table += f"<td style='padding:10px; text-align:center; border:1px solid #ddd;'>{row[col]:.4f}</td>"
                    else:
                        html_table += f"<td style='padding:10px; text-align:center; border:1px solid #ddd;'>{row[col]}</td>"
                html_table += "</tr>"

            html_table += "</tbody></table>"

            st.markdown(html_table, unsafe_allow_html=True)

            if len(filtered_df) > max_display:
                st.sidebar.info(f"📊 Displaying first {max_display} rows. Increase 'Max rows to display' to see more.")

            st.markdown("---")

            selected_d = filtered_df[search_d].iloc[0]

            if show_diffraction:
                st.subheader("📈 Simulated Diffraction Pattern")

                selected_reflections = [selected_reflection]
                selected_d_spacings = [selected_d]

                result_reflections = filtered_df[result_column].head(max_display).tolist()
                result_d_spacings = filtered_df[result_d].head(max_display).tolist()

                selected_peaks = []
                for refl, d in zip(selected_reflections, selected_d_spacings):
                    two_theta = d_to_twotheta(d, wavelength)
                    if two_theta and 10 <= two_theta <= 120:
                        selected_peaks.append({
                            '2θ': two_theta,
                            'label': refl,
                            'type': search_label,
                            'd': d
                        })

                result_peaks = []
                for refl, d in zip(result_reflections, result_d_spacings):
                    two_theta = d_to_twotheta(d, wavelength)
                    if two_theta and 10 <= two_theta <= 120:
                        result_peaks.append({
                            '2θ': two_theta,
                            'label': refl,
                            'type': result_label,
                            'd': d
                        })

                all_peaks = selected_peaks + result_peaks
                all_peaks.sort(key=lambda x: x['2θ'])

                grouped_peaks = []
                tolerance = 0.1
                i = 0
                while i < len(all_peaks):
                    current_peak = all_peaks[i]
                    group = [current_peak]
                    j = i + 1
                    while j < len(all_peaks) and abs(all_peaks[j]['2θ'] - current_peak['2θ']) < tolerance:
                        group.append(all_peaks[j])
                        j += 1

                    grouped_peaks.append({
                        '2θ': np.mean([p['2θ'] for p in group]),
                        'labels': group
                    })
                    i = j

                fig_diff = go.Figure()

                max_intensity = 100

                peak_trace_map = {}
                peak_hover_map = {}

                for peak in grouped_peaks:
                    two_theta = peak['2θ']

                    has_selected = any(p['type'] == search_label for p in peak['labels'])
                    has_result = any(p['type'] == result_label for p in peak['labels'])

                    if has_selected:
                        if search_label not in peak_trace_map:
                            peak_trace_map[search_label] = {'x': [], 'y': []}
                            peak_hover_map[search_label] = []

                        search_planes = [p['label'] for p in peak['labels'] if p['type'] == search_label]
                        search_d_values = [p['d'] for p in peak['labels'] if p['type'] == search_label]
                        hover_text = f"<b>2θ:</b> {two_theta:.2f}°<br><b>{search_label}:</b> {', '.join(search_planes)}<br><b>d:</b> {search_d_values[0]:.4f} Å"

                        peak_trace_map[search_label]['x'].extend([two_theta, two_theta, None])
                        peak_trace_map[search_label]['y'].extend([0, max_intensity, None])
                        peak_hover_map[search_label].extend([hover_text, hover_text, None])

                    if has_result:
                        if result_label not in peak_trace_map:
                            peak_trace_map[result_label] = {'x': [], 'y': []}
                            peak_hover_map[result_label] = []

                        result_planes = [p['label'] for p in peak['labels'] if p['type'] == result_label]
                        result_d_values = [p['d'] for p in peak['labels'] if p['type'] == result_label]
                        hover_text = f"<b>2θ:</b> {two_theta:.2f}°<br><b>{result_label}:</b> {', '.join(result_planes)}<br><b>d:</b> {result_d_values[0]:.4f} Å"

                        peak_trace_map[result_label]['x'].extend([two_theta, two_theta, None])
                        peak_trace_map[result_label]['y'].extend([0, max_intensity, None])
                        peak_hover_map[result_label].extend([hover_text, hover_text, None])

                if search_label in peak_trace_map:
                    fig_diff.add_trace(go.Scatter(
                        x=peak_trace_map[search_label]['x'],
                        y=peak_trace_map[search_label]['y'],
                        mode='lines',
                        line=dict(color=search_color, width=3),
                        name=search_label,
                        hovertext=peak_hover_map[search_label],
                        hoverinfo='text'
                    ))

                if result_label in peak_trace_map:
                    fig_diff.add_trace(go.Scatter(
                        x=peak_trace_map[result_label]['x'],
                        y=peak_trace_map[result_label]['y'],
                        mode='lines',
                        line=dict(color=result_color, width=3),
                        name=result_label,
                        hovertext=peak_hover_map[result_label],
                        hoverinfo='text'
                    ))

                max_annotations = 15
                for peak in grouped_peaks[:max_annotations]:
                    label_parts = []
                    color = '#000000'

                    for p in peak['labels']:
                        if p['type'] == search_label:
                            label_parts.append(f"{search_label[0]}: {p['label']}")
                            color = search_color
                        else:
                            label_parts.append(f"{result_label[0]}: {p['label']}")
                            if color == '#000000':
                                color = result_color

                    label_text = '<br>'.join(label_parts[:2])
                    if len(label_parts) > 2:
                        label_text += f'<br>+{len(label_parts) - 2} more'

                    fig_diff.add_annotation(
                        x=peak['2θ'],
                        y=max_intensity + 5,
                        text=label_text,
                        showarrow=True,
                        arrowhead=2,
                        arrowsize=1,
                        arrowwidth=3,
                        arrowcolor=color,
                        ax=0,
                        ay=-40,
                        font=dict(size=16, color=color, family='Arial Black'),
                        bgcolor='rgba(255,255,255,0.8)',
                        borderpad=4
                    )

                fig_diff.update_layout(
                    xaxis_title="2θ (degrees)",
                    yaxis_title="Intensity (a.u.)",
                    height=600,
                    hovermode='closest',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                        font=dict(size=26, color='#000000')
                    ),
                    font=dict(size=26, color='#000000'),
                    xaxis=dict(
                        range=[10, 120],
                        tickfont=dict(size=24, color='#000000'),
                        title_font=dict(size=28, color='#000000'),
                        gridcolor='#d0d0d0',
                        linecolor='#000000',
                        linewidth=2
                    ),
                    yaxis=dict(
                        range=[0, max_intensity + 20],
                        tickfont=dict(size=24, color='#000000'),
                        title_font=dict(size=28, color='#000000'),
                        gridcolor='#d0d0d0',
                        linecolor='#000000',
                        linewidth=2
                    ),
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=22,
                        font_family="Arial"
                    )
                )

                st.plotly_chart(fig_diff, use_container_width=True)

                st.markdown("---")

            st.subheader("📊 d-spacing Comparison")

            max_bars = min(15, len(filtered_df))
            display_bars_df = filtered_df.head(max_bars)

            if not combine_graphs:
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**{search_label} Reflection**")

                    fig_search = go.Figure()
                    fig_search.add_trace(go.Bar(
                        x=[selected_reflection],
                        y=[selected_d],
                        name=search_label,
                        marker_color=search_color,
                        text=[f"{selected_d:.3f} Å"],
                        textposition='outside',
                        textfont=dict(size=22, family='Arial Black', color='#000000'),
                        hovertemplate='<b>%{x}</b><br>d = %{y:.3f} Å<extra></extra>'
                    ))

                    y_max = selected_d * 1.2

                    fig_search.update_layout(
                        xaxis_title="Reflection",
                        yaxis_title="d-spacing (Å)",
                        height=550,
                        showlegend=False,
                        font=dict(size=26, color='#000000'),
                        xaxis=dict(
                            tickfont=dict(size=24, color='#000000'),
                            title_font=dict(size=28, color='#000000'),
                            linecolor='#000000',
                            linewidth=2
                        ),
                        yaxis=dict(
                            range=[0, y_max],
                            tickfont=dict(size=24, color='#000000'),
                            title_font=dict(size=28, color='#000000'),
                            gridcolor='#d0d0d0',
                            linecolor='#000000',
                            linewidth=2
                        ),
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        hoverlabel=dict(
                            bgcolor="white",
                            font_size=22,
                            font_family="Arial"
                        )
                    )

                    st.plotly_chart(fig_search, use_container_width=True)

                with col2:
                    st.markdown(f"**Corresponding {result_label} Reflections (showing first {max_bars})**")

                    fig_result = go.Figure()
                    fig_result.add_trace(go.Bar(
                        x=display_bars_df[result_column].tolist(),
                        y=display_bars_df[result_d].tolist(),
                        name=result_label,
                        marker_color=result_color,
                        text=[f"{d:.3f} Å" for d in display_bars_df[result_d]],
                        textposition='outside',
                        textfont=dict(size=22, family='Arial Black', color='#000000'),
                        hovertemplate='<b>%{x}</b><br>d = %{y:.3f} Å<extra></extra>'
                    ))

                    y_max_result = display_bars_df[result_d].max() * 1.2

                    fig_result.update_layout(
                        xaxis_title="Reflection",
                        yaxis_title="d-spacing (Å)",
                        height=550,
                        showlegend=False,
                        xaxis_tickangle=-45,
                        font=dict(size=26, color='#000000'),
                        xaxis=dict(
                            tickfont=dict(size=24, color='#000000'),
                            title_font=dict(size=28, color='#000000'),
                            linecolor='#000000',
                            linewidth=2
                        ),
                        yaxis=dict(
                            range=[0, y_max_result],
                            tickfont=dict(size=24, color='#000000'),
                            title_font=dict(size=28, color='#000000'),
                            gridcolor='#d0d0d0',
                            linecolor='#000000',
                            linewidth=2
                        ),
                        margin=dict(b=120),
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        hoverlabel=dict(
                            bgcolor="white",
                            font_size=22,
                            font_family="Arial"
                        )
                    )

                    st.plotly_chart(fig_result, use_container_width=True)

            else:
                st.markdown(
                    f"**Combined View: {search_label} & {result_label} (showing first {max_bars} {result_label.lower()} reflections)**")

                fig_combined = go.Figure()

                fig_combined.add_trace(go.Bar(
                    x=[selected_reflection],
                    y=[selected_d],
                    name=search_label,
                    marker_color=search_color,
                    text=[f"{selected_d:.3f} Å"],
                    textposition='outside',
                    textfont=dict(size=22, family='Arial Black', color='#000000'),
                    hovertemplate='<b>%{x}</b><br>d = %{y:.3f} Å<extra></extra>'
                ))

                fig_combined.add_trace(go.Bar(
                    x=display_bars_df[result_column].tolist(),
                    y=display_bars_df[result_d].tolist(),
                    name=result_label,
                    marker_color=result_color,
                    text=[f"{d:.3f} Å" for d in display_bars_df[result_d]],
                    textposition='outside',
                    textfont=dict(size=22, family='Arial Black', color='#000000'),
                    hovertemplate='<b>%{x}</b><br>d = %{y:.3f} Å<extra></extra>'
                ))

                y_max_combined = max(selected_d, display_bars_df[result_d].max()) * 1.2

                fig_combined.update_layout(
                    xaxis_title="Reflection",
                    yaxis_title="d-spacing (Å)",
                    height=650,
                    barmode='group',
                    xaxis_tickangle=-45,
                    font=dict(size=26, color='#000000'),
                    xaxis=dict(
                        tickfont=dict(size=24, color='#000000'),
                        title_font=dict(size=28, color='#000000'),
                        linecolor='#000000',
                        linewidth=2
                    ),
                    yaxis=dict(
                        range=[0, y_max_combined],
                        tickfont=dict(size=24, color='#000000'),
                        title_font=dict(size=28, color='#000000'),
                        gridcolor='#d0d0d0',
                        linecolor='#000000',
                        linewidth=2
                    ),
                    margin=dict(b=140),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                        font=dict(size=26, color='#000000')
                    ),
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=22,
                        font_family="Arial"
                    )
                )

                st.plotly_chart(fig_combined, use_container_width=True)

    else:
        st.info(
            f"👆 Please select a {search_label.lower()} reflection from the dropdown above to view corresponding {result_label.lower()} data and visualizations.")

        st.markdown("---")
        st.subheader("📐 Crystal Structure Information")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Austenite (B2)")
            st.markdown(f"**Space Group:** {AUSTENITE['space_group']}")
            st.markdown(f"**Crystal System:** {AUSTENITE['structure']}")
            st.markdown("**Lattice Parameters:**")
            st.markdown(f"- a = b = c = {AUSTENITE['a']:.3f} Å")
            st.markdown(f"- α = β = γ = {AUSTENITE['alpha']}°")

        with col2:
            st.markdown("### Martensite (B19')")
            st.markdown(f"**Space Group:** {MARTENSITE['space_group']}")
            st.markdown(f"**Crystal System:** {MARTENSITE['structure']}")
            st.markdown("**Lattice Parameters:**")
            st.markdown(f"- a = {MARTENSITE['a']:.3f} Å")
            st.markdown(f"- b = {MARTENSITE['b']:.3f} Å")
            st.markdown(f"- c = {MARTENSITE['c']:.3f} Å")
            st.markdown(f"- α = {MARTENSITE['alpha']}°, β = {MARTENSITE['beta']:.2f}°, γ = {MARTENSITE['gamma']}°")
else:
    st.warning("⚠️ Please ensure 'hkl_corresp_table_NiTiHf_extended.xlsx' is in the same directory as this script.")
