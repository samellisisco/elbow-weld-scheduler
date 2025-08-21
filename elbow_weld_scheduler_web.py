import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import io
import streamlit as st
import os
import base64

# --------------------
# Logo at the top (centered)
# --------------------
logo_path = os.path.join(os.path.dirname(__file__), "logo.png")

if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{logo_base64}" width="200">
        </div>
        """,
        unsafe_allow_html=True,
    )

st.set_page_config(layout="wide")
st.title("Elbow Weld Process Visualizer")

# --- Session State Reset ---
if "clear" not in st.session_state:
    st.session_state.clear = False

# Clear chart button
if st.button("Clear Chart & Results"):
    st.session_state.clear = True

# Lookup table
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

# --- Global Inputs ---
st.header("Global Step Durations")
col1, col2 = st.columns(2)
with col1:
    global_setup = st.number_input("Weld set up duration (minutes)", min_value=1, value=10)
with col2:
    global_stamping = st.number_input("Stamping duration (minutes)", min_value=1, value=1)

# --- Machine Configurations ---
st.header("🛠️ Machine Configurations")
machines = []

for i in range(1, 5):
    with st.expander(f"Machine {i}"):
        c1, c2, c3 = st.columns(3)
        with c1:
            start_time = st.number_input(f"Start time (min)", min_value=0, value=(i - 1) * global_setup, key=f"start_{i}")
        with c2:
            number_of_welds = st.selectbox(f"Welds per elbow", options=[1, 2, 3, 4], index=1, key=f"welds_{i}")
        with c3:
            quantity = st.number_input(f"Number of elbows", min_value=1, value=3, key=f"qty_{i}")

        c4, c5 = st.columns(2)
        with c4:
            pipe_size = st.selectbox(f"Pipe Size", sorted(lookup_table["Pipe Size"].unique()), key=f"pipe_{i}")
        with c5:
            dr = st.selectbox(f"DR", sorted(lookup_table["DR"].unique()), key=f"dr_{i}")

        match = lookup_table[(lookup_table["Pipe Size"] == pipe_size) & (lookup_table["DR"] == dr)]
        if match.empty:
            st.warning(f"No match found for Pipe Size {pipe_size} and DR {dr}. Using default values.")
            weld_start = 10
            cooling = 10
        else:
            weld_start = float(match["Weld start"].values[0])
            cooling = float(match["Cooling"].values[0])

        machines.append({
            "start_time": start_time,
            "number_of_welds": number_of_welds,
            "quantity": quantity,
            "step_durations": [global_setup, weld_start, global_stamping, cooling]
        })

# --- Generate Chart ---
if st.button("📊 Generate Chart"):
    st.session_state.clear = False  # reset clear flag
    fig, ax = plt.subplots(figsize=(16, 8), dpi=150)
    overlap_regions = []
    all_setup_intervals = []
    all_stamping_intervals = []
    timeline_records = []
    machine_run_times = []
    machine_overlap_counts = {f"Machine {i+1}": 0 for i in range(4)}

    step_labels = ["Set up", "Weld start", "Stamping", "Cooling"]
    step_colors = ["orange", "grey", "yellow", "lightblue"]

    for idx, machine in enumerate(machines):
        current_time = machine["start_time"]
        durations = machine["step_durations"]
        machine_start_time = current_time

        for q in range(machine["quantity"]):
            for w in range(machine["number_of_welds"]):
                for step_idx in range(4):
                    start = current_time
                    duration = durations[step_idx]
                    end = start + duration
                    label = step_labels[step_idx]

                    if label == "Set up":
                        all_setup_intervals.append((start, end, idx + 1))
                    elif label == "Stamping":
                        all_stamping_intervals.append((start, end, idx + 1))

                    ax.barh(y=idx, width=duration, left=start,
                            color=step_colors[step_idx], edgecolor='black')

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

    # Overlap detection (setup vs setup, stamping vs stamping, setup vs stamping)
    all_intervals = all_setup_intervals + all_stamping_intervals
    for i1, (s_start, s_end, s_machine) in enumerate(all_intervals):
        for i2, (t_start, t_end, t_machine) in enumerate(all_intervals):
            if i1 < i2 and s_machine != t_machine:
                if not (s_end <= t_start or s_start >= t_end):
                    overlap_start = max(s_start, t_start)
                    overlap_end = min(s_end, t_end)
                    overlap_regions.append((overlap_start, overlap_end, s_machine - 1))
                    overlap_regions.append((overlap_start, overlap_end, t_machine - 1))
                    machine_overlap_counts[f"Machine {s_machine}"] += 1
                    machine_overlap_counts[f"Machine {t_machine}"] += 1

    for start, end, machine_idx in overlap_regions:
        ax.barh(y=machine_idx, width=end - start, left=start,
                height=0.8, color='red', alpha=0.3,
                edgecolor='red', linewidth=0.5)

    ax.set_yticks(range(4))
    ax.set_yticklabels([f"Machine {i + 1}" for i in range(4)], fontsize=12)
    ax.set_xlabel("Time (minutes)", fontsize=12)
    ax.set_title("Weld Process Timeline", fontsize=16, weight="bold")
    ax.grid(True, which='both', axis='x', linestyle='--', alpha=0.5)
    ax.xaxis.set_major_locator(plt.MultipleLocator(50))
    ax.xaxis.set_minor_locator(plt.MultipleLocator(10))

    legend_elements = [
        Patch(facecolor="orange", edgecolor='black', label="Set up"),
        Patch(facecolor="grey", edgecolor='black', label="Weld start"),
        Patch(facecolor="yellow", edgecolor='black', label="Stamping"),
        Patch(facecolor="lightblue", edgecolor='black', label="Cooling"),
        Patch(facecolor="red", edgecolor='red', alpha=0.3, label="Overlap")
    ]
    ax.legend(handles=legend_elements, loc="upper right")

    st.pyplot(fig)

    # Results
    # --- Total Run Time Report ---
    st.subheader("⏱️ Total Run Time Per Machine")
    for name, runtime in machine_run_times:
        st.write(f"**{name}**: {runtime:.2f} minutes ({runtime:.2f/60} hours)")

    # --- Downtime Report ---
    st.subheader("⏳ Downtime Report")

    if timeline_records:
        # Find the maximum end time across all machines
        max_end_time = max([rec["End Time"] for rec in timeline_records])

        # Calculate final end time per machine
        machine_end_times = {}
        for rec in timeline_records:
            machine = rec["Machine"]
            end_time = rec["End Time"]
            if machine not in machine_end_times or end_time > machine_end_times[machine]:
                machine_end_times[machine] = end_time

        # Build downtime data
        downtime_data = []
        total_downtime = 0
        for machine, end_time in machine_end_times.items():
            downtime = max_end_time - end_time
            total_downtime += downtime
            downtime_data.append({
                "Machine": machine,
                "Final End Time (min)": end_time,
                "Downtime (min)": downtime
            })

        # Display downtime table
        downtime_df = pd.DataFrame(downtime_data)
        st.table(downtime_df)

        # Show total downtime
        st.write(f"**Total Downtime:** {total_downtime:.2f} mins ({total_downtime:.2f/60} hours)")
        st.write(f"**Maximum Process Time (min):** {max_end_time:.2f}")
    else:
        st.info("No timeline records available to calculate downtime.")

    st.subheader("📊 Overlap Count Per Machine")
    has_overlap = any(count > 0 for count in machine_overlap_counts.values())
    if has_overlap:
        for machine, count in machine_overlap_counts.items():
            runtime = dict(machine_run_times)[machine]
            percentage = (count / runtime) * 100 if runtime > 0 else 0
            st.write(f"**{machine}**: {count} overlaps ({percentage:.1f}% of runtime)")
    else:
        st.success("✅ No overlaps detected")

    # --- Overlap Type Tracking ---
    overlap_type_durations = {
        "Setup vs Setup": 0,
        "Setup vs Stamping": 0,
        "Stamping vs Stamping": 0
    }

    # Re-run detection with type classification
    for i1, (s_start, s_end, s_machine) in enumerate(all_intervals):
        s_type = "Setup" if (s_start, s_end, s_machine) in all_setup_intervals else "Stamping"
        for i2, (t_start, t_end, t_machine) in enumerate(all_intervals):
            if i1 < i2 and s_machine != t_machine:
                if not (s_end <= t_start or s_start >= t_end):
                    overlap_start = max(s_start, t_start)
                    overlap_end = min(s_end, t_end)
                    overlap_duration = overlap_end - overlap_start

                    if s_type == "Setup" and (t_start, t_end, t_machine) in all_setup_intervals:
                        overlap_type_durations["Setup vs Setup"] += overlap_duration
                    elif s_type == "Stamping" and (t_start, t_end, t_machine) in all_stamping_intervals:
                        overlap_type_durations["Stamping vs Stamping"] += overlap_duration
                    else:
                        overlap_type_durations["Setup vs Stamping"] += overlap_duration
    
    # --- Summarize Overlap Types ---
    total_runtime_all = sum(runtime for _, runtime in machine_run_times)
    total_overlap_time = sum(overlap_type_durations.values())

    st.subheader("🔎 Overlap Breakdown by Type")
    overlap_table = []
    for o_type, duration in overlap_type_durations.items():
        percentage = (duration / total_runtime_all) * 100 if total_runtime_all > 0 else 0
        overlap_table.append({
            "Overlap Type": o_type,
            "Total Time (min)": round(duration, 2),
            "% of Total Runtime": f"{percentage:.2f}%"
        })

    df_overlap = pd.DataFrame(overlap_table)
    st.table(df_overlap)
    
    # --- Updated Machine Utilization Grade ---
    # total_overlap_time is already computed earlier in your overlap section
    if max_end_time > 0:
        utilization_percent = (((max_end_time*4) - total_downtime - total_overlap_time) / (max_end_time*4)) * 100
    else:
        utilization_percent = 0

    # Determine letter grade + color
    if utilization_percent >= 90:
        letter_grade = "A"
        color = "green"
    elif utilization_percent >= 80:
        letter_grade = "B"
        color = "limegreen"
    elif utilization_percent >= 70:
        letter_grade = "C"
        color = "orange"
    elif utilization_percent >= 60:
        letter_grade = "D"
        color = "orangered"
    else:
        letter_grade = "F"
        color = "red"

    st.markdown(f"**Machine Utilization Grade:** {utilization_percent:.2f}%")
    st.markdown(
    f"""
    <div style='text-align: center; 
                color: {color}; 
                font-size: 200px; 
                font-weight: bold; 
                text-shadow: 2px 2px 5px #888;'>
        {letter_grade}
    </div>
    """,
    unsafe_allow_html=True
    )
    
    # --- Downloads ---
    df = pd.DataFrame(timeline_records)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📤 Export Timeline as CSV", data=csv, file_name="weld_timeline.csv", mime="text/csv")

    pdf_buffer = io.BytesIO()
    with PdfPages(pdf_buffer) as pdf:
        # Page 1: Chart
        fig.set_size_inches(16, 8)
        pdf.savefig(fig, dpi=300, bbox_inches='tight')

        # Page 2: Report
        fig2, ax2 = plt.subplots(figsize=(8.5, 11))
        ax2.axis("off")

        y = 1.0
        ax2.text(0.05, y, "Weld Process Report", fontsize=16, weight="bold", transform=ax2.transAxes)
        y -= 0.1

        ax2.text(0.05, y, "⏱️ Total Run Time Per Machine", fontsize=14, weight="bold", transform=ax2.transAxes)
        y -= 0.05
        for name, runtime in machine_run_times:
            ax2.text(0.1, y, f"{name}: {runtime:.2f} minutes", fontsize=12, transform=ax2.transAxes)
            y -= 0.04

        y -= 0.05
        ax2.text(0.05, y, "📊 Overlap Report", fontsize=14, weight="bold", transform=ax2.transAxes)
        y -= 0.05
        if has_overlap:
            for machine, count in machine_overlap_counts.items():
                runtime = dict(machine_run_times)[machine]
                percentage = (count / runtime) * 100 if runtime > 0 else 0
                ax2.text(0.1, y, f"{machine}: {count} overlaps ({percentage:.1f}% of runtime)", fontsize=12, transform=ax2.transAxes)
                y -= 0.04
        else:
            ax2.text(0.1, y, "✅ No overlaps detected", fontsize=12, transform=ax2.transAxes)
            y -= 0.04

        # --- Add Overlap Breakdown by Type ---
        y -= 0.05
        ax2.text(0.05, y, "🔎 Overlap Breakdown by Type", fontsize=14, weight="bold", transform=ax2.transAxes)
        y -= 0.05
        for o_type, duration in overlap_type_durations.items():
            percentage = (duration / total_runtime_all) * 100 if total_runtime_all > 0 else 0
            ax2.text(0.1, y, f"{o_type}: {duration:.2f} min ({percentage:.2f}% of total runtime)", fontsize=12, transform=ax2.transAxes)
            y -= 0.04

        # --- Add Machine Utilization Grade ---
        y -= 0.05
        ax2.text(0.05, y, "⚙️ Machine Utilization", fontsize=14, weight="bold", transform=ax2.transAxes)
        y -= 0.05
        ax2.text(0.1, y, f"Utilization: {utilization_percent:.2f}% (Grade {letter_grade})", fontsize=12, color=color, transform=ax2.transAxes)
        y -= 0.04

        pdf.savefig(fig2, dpi=300, bbox_inches='tight')
        plt.close(fig2)

    st.download_button("📥 Export Chart + Report as PDF", data=pdf_buffer.getvalue(),
                       file_name="weld_report.pdf", mime="application/pdf")

# --- Clear Mode ---
if st.session_state.clear:
    st.info("Chart and results cleared. Adjust inputs and click **Generate Chart** to start fresh.")


