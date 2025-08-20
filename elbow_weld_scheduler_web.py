import io
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.backends.backend_pdf import PdfPages
import streamlit as st

# -----------------------------
# Page / Theme / Styles
# -----------------------------
st.set_page_config(
    page_title="Elbow Weld Scheduler",
    page_icon="⚙️",
    layout="wide",
)

# Optional: light custom styling
st.markdown("""
<style>
/* Header banner */
.app-header {
  padding: 18px 20px;
  border-radius: 12px;
  background: linear-gradient(90deg, #0ea5e9, #22c55e);
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
/* Subsection cards */
.card {
  background: #ffffff10;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  padding: 16px 16px 6px 16px;
  margin-bottom: 12px;
}
/* Tighten expander header */
.streamlit-expanderHeader { font-weight: 700; }
/* Buttons inline */
.button-row > div > button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Session State (for results)
# -----------------------------
ss = st.session_state
ss.setdefault("fig", None)
ss.setdefault("timeline_records", None)
ss.setdefault("machine_run_times", None)
ss.setdefault("machine_overlap_counts", None)

# -----------------------------
# Header with optional logo
# -----------------------------
col_head_l, col_head_r = st.columns([0.78, 0.22])
with col_head_l:
    st.markdown("""
<div class="app-header">
  <div style="font-size: 22px; font-weight: 800;">⚙️ Elbow Weld Process Visualizer</div>
  <div style="font-size: 13px;">Schedule visualization • Overlap detection • CSV & PDF export</div>
</div>
""", unsafe_allow_html=True)

with col_head_r:
    logo = st.file_uploader("Company logo (optional)", type=["png","jpg","jpeg"], label_visibility="collapsed")
    if logo:
        st.image(logo, use_container_width=True)

# -----------------------------
# Lookup Table
# -----------------------------
lookup_table = pd.DataFrame([
    {"Pipe Size": 16, "DR": 7,  "Weld start": 13.3,  "Cooling": 24},
    {"Pipe Size": 16, "DR": 9,  "Weld start": 37.24, "Cooling": 20},
    {"Pipe Size": 16, "DR": 11, "Weld start": 9.31,  "Cooling": 16},
    {"Pipe Size": 16, "DR": 13, "Weld start": 6.65,  "Cooling": 13},
    {"Pipe Size": 18, "DR": 7,  "Weld start": 1.33,  "Cooling": 27},
    {"Pipe Size": 18, "DR": 9,  "Weld start": 11.97, "Cooling": 22},
    {"Pipe Size": 18, "DR": 11, "Weld start": 9.31,  "Cooling": 20},
    {"Pipe Size": 18, "DR": 13, "Weld start": 7.98,  "Cooling": 15},
    {"Pipe Size": 20, "DR": 7,  "Weld start": 15.96, "Cooling": 30},
    {"Pipe Size": 20, "DR": 9,  "Weld start": 13.3,  "Cooling": 24},
    {"Pipe Size": 20, "DR": 11, "Weld start": 10.64, "Cooling": 20},
    {"Pipe Size": 20, "DR": 13, "Weld start": 9.31,  "Cooling": 16},
    {"Pipe Size": 24, "DR": 7,  "Weld start": 19.95, "Cooling": 36},
    {"Pipe Size": 24, "DR": 9,  "Weld start": 15.96, "Cooling": 29},
    {"Pipe Size": 24, "DR": 11, "Weld start": 13.3,  "Cooling": 24},
    {"Pipe Size": 24, "DR": 13, "Weld start": 10.64, "Cooling": 20},
    {"Pipe Size": 30, "DR": 7,  "Weld start": 19.95, "Cooling": 32},
    {"Pipe Size": 30, "DR": 9,  "Weld start": 15.96, "Cooling": 30},
    {"Pipe Size": 30, "DR": 11, "Weld start": 13.3,  "Cooling": 24},
    {"Pipe Size": 30, "DR": 17, "Weld start": 10.64, "Cooling": 19},
])

# -----------------------------
# Tabs: Inputs | Chart & Results
# -----------------------------
tab_inputs, tab_results = st.tabs(["🧩 Inputs", "📊 Chart & Results"])

with tab_inputs:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🌍 Global Step Durations")
    col1, col2 = st.columns(2)
    with col1:
        global_setup = st.number_input("Set up duration (minutes)", min_value=1, value=5)
    with col2:
        global_stamping = st.number_input("Stamping duration (minutes)", min_value=1, value=3)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🛠️ Machine Configurations")
    machines = []

    for i in range(1, 5):
        with st.expander(f"Machine {i}", expanded=(i == 1)):
            c1, c2, c3 = st.columns(3)
            with c1:
                start_time = st.number_input("Start time (min)", min_value=0, value=(i - 1) * 5, key=f"start_{i}")
            with c2:
                number_of_welds = st.slider("Welds per elbow", min_value=1, max_value=4, value=2, key=f"welds_{i}")
            with c3:
                quantity = st.number_input("Number of elbows", min_value=1, value=3, key=f"qty_{i}")

            c4, c5 = st.columns(2)
            with c4:
                pipe_size = st.selectbox("Pipe Size", sorted(lookup_table["Pipe Size"].unique()), key=f"pipe_{i}")
            with c5:
                dr = st.selectbox("DR", sorted(lookup_table["DR"].unique()), key=f"dr_{i}")

            match = lookup_table[(lookup_table["Pipe Size"] == pipe_size) & (lookup_table["DR"] == dr)]
            if match.empty:
                st.warning(f"No match for Pipe Size {pipe_size} and DR {dr}. Using defaults.")
                weld_start, cooling = 10.0, 10.0
            else:
                weld_start = float(match["Weld start"].values[0])
                cooling = float(match["Cooling"].values[0])

            machines.append({
                "start_time": start_time,
                "number_of_welds": number_of_welds,
                "quantity": quantity,
                "step_durations": [global_setup, weld_start, global_stamping, cooling]
            })
    st.markdown('</div>', unsafe_allow_html=True)

    # Action buttons
    col_btn1, col_btn2, col_sp = st.columns([0.18, 0.18, 0.64])
    with col_btn1:
        gen = st.button("📊 Generate Chart", use_container_width=True)
    with col_btn2:
        reset = st.button("🧹 Reset All", use_container_width=True)

    if reset:
        for k in ["fig", "timeline_records", "machine_run_times", "machine_overlap_counts"]:
            ss[k] = None
        st.success("Cleared. Adjust inputs and click **Generate Chart** to start fresh.")

    # Build chart now if requested
    if gen:
        step_labels = ["Set up", "Weld start", "Stamping", "Cooling"]
        step_colors = ["orange", "grey", "yellow", "blue"]

        fig, ax = plt.subplots(figsize=(18, 8), dpi=150)
        all_setup_intervals, all_stamping_intervals, overlap_regions = [], [], []
        timeline_records, machine_run_times = [], []
        machine_overlap_counts = {f"Machine {i+1}": 0 for i in range(4)}

        for idx, machine in enumerate(machines):
            current_time = machine["start_time"]
            machine_start_time = current_time

            for q in range(machine["quantity"]):
                for w in range(machine["number_of_welds"]):
                    for step_idx, duration in enumerate(machine["step_durations"]):
                        start, end = current_time, current_time + duration
                        label = step_labels[step_idx]

                        if label == "Set up":
                            all_setup_intervals.append((start, end, idx + 1))
                        elif label == "Stamping":
                            all_stamping_intervals.append((start, end, idx + 1))

                        ax.barh(y=idx, width=duration, left=start,
                                color=step_colors[step_idx], edgecolor='black', linewidth=0.8)

                        timeline_records.append({
                            "Machine": f"Machine {idx + 1}",
                            "Elbow #": q + 1,
                            "Weld #": w + 1,
                            "Step": label,
                            "Start Time": round(start, 2),
                            "End Time": round(end, 2),
                            "Duration": round(duration, 2)
                        })
                        current_time = end

            machine_run_times.append((f"Machine {idx + 1}", round(current_time - machine_start_time, 2)))

        # Overlap detection
        for s_start, s_end, s_machine in all_setup_intervals:
            for t_start, t_end, t_machine in all_stamping_intervals:
                if s_machine != t_machine and not (s_end <= t_start or s_start >= t_end):
                    overlap_start, overlap_end = max(s_start, t_start), min(s_end, t_end)
                    overlap_regions.append((overlap_start, overlap_end, s_machine - 1))
                    overlap_regions.append((overlap_start, overlap_end, t_machine - 1))
                    machine_overlap_counts[f"Machine {s_machine}"] += 1
                    machine_overlap_counts[f"Machine {t_machine}"] += 1

        for start, end, machine_idx in overlap_regions:
            ax.barh(y=machine_idx, width=end - start, left=start,
                    height=0.75, color='red', alpha=0.28, edgecolor='red', linewidth=0.5)

        ax.set_yticks(range(4))
        ax.set_yticklabels([f"Machine {i+1}" for i in range(4)], fontsize=12)
        ax.set_xlabel("Time (minutes)", fontsize=12)
        ax.set_title("Weld Process Timeline", fontsize=16, weight="bold")
        ax.grid(True, which='both', axis='x', linestyle='--', alpha=0.45)
        ax.xaxis.set_major_locator(plt.MultipleLocator(50))
        ax.xaxis.set_minor_locator(plt.MultipleLocator(10))
        ax.legend([
            Patch(facecolor="orange", edgecolor='black', label="Set up"),
            Patch(facecolor="grey", edgecolor='black', label="Weld start"),
            Patch(facecolor="yellow", edgecolor='black', label="Stamping"),
            Patch(facecolor="blue", edgecolor='black', label="Cooling"),
            Patch(facecolor="red", edgecolor='red', alpha=0.3, label="Overlap")
        ], loc="upper right")

        # Save to session for Results tab
        ss.fig = fig
        ss.timeline_records = timeline_records
        ss.machine_run_times = machine_run_times
        ss.machine_overlap_counts = machine_overlap_counts

with tab_results:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📈 Timeline Chart")
    if ss.fig is not None:
        st.pyplot(ss.fig, use_container_width=True)
    else:
        st.info("No chart yet. Go to **Inputs** and click **Generate Chart**.")
    st.markdown('</div>', unsafe_allow_html=True)

    # KPIs
    if ss.machine_run_times is not None and ss.machine_overlap_counts is not None:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📌 Summary Metrics")

        # Total runtime boxes
        st.markdown("**⏱️ Total Run Time Per Machine**")
        cols = st.columns(4)
        for (name, rt), c in zip(ss.machine_run_times, cols):
            c.metric(label=name, value=f"{rt:.2f} min")

        # Overlap count boxes
        st.markdown("**🚧 Overlap Count Per Machine**")
        cols2 = st.columns(4)
        for (m, count), c in zip(ss.machine_overlap_counts.items(), cols2):
            c.metric(label=m, value=int(count))
        st.markdown('</div>', unsafe_allow_html=True)

    # Data / Downloads
    if ss.timeline_records is not None:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📋 Detailed Timeline Table")
        df = pd.DataFrame(ss.timeline_records)
        st.dataframe(df, use_container_width=True)

        col_dl1, col_dl2, _ = st.columns([0.22, 0.22, 0.56])
        with col_dl1:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📤 Export CSV", data=csv, file_name="weld_timeline.csv", mime="text/csv", use_container_width=True)

        with col_dl2:
            pdf_buffer = io.BytesIO()
            with PdfPages(pdf_buffer) as pdf:
                # re-size for export
                fig_export = ss.fig
                fig_export.set_size_inches(16, 8)
                pdf.savefig(fig_export, dpi=300, bbox_inches='tight')
            st.download_button("📥 Export PDF", data=pdf_buffer.getvalue(),
                               file_name="weld_chart.pdf", mime="application/pdf",
                               use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Sidebar "About"
# -----------------------------
with st.sidebar:
    st.subheader("About")
    st.write(
        "This tool visualizes elbow weld schedules across up to four machines, "
        "highlights overlaps between **Set up** and **Stamping** across machines, "
        "and exports results to CSV/PDF."
    )
    st.caption("© 2025 • Weld Scheduler v1.0")
