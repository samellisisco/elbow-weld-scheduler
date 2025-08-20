import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import io
import base64

# --- Page Config ---
st.set_page_config(layout="wide")

# --- Centered Logo ---
logo_path = "99d58d86-f610-40c9-bdc0-b7f994e2e7a3.png"  # make sure the file is in the same folder

st.markdown(
    f"""
    <div style="text-align: center;">
        <img src="data:image/png;base64,{base64.b64encode(open(logo_path, "rb").read()).decode()}" width="200">
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Title ---
st.markdown("<h1 style='text-align: center;'>⚙️ Elbow Weld Process Visualizer</h1>", unsafe_allow_html=True)


# --- Input Section ---
st.sidebar.header("Input Parameters")

num_elbows = st.sidebar.number_input("Number of elbows", min_value=1, value=5)

welds_per_elbow = st.sidebar.selectbox("Welds per elbow", [1, 2, 3, 4], index=1)

setup_time = st.sidebar.number_input("Setup time per machine (min)", min_value=0, value=10)
weld_time = st.sidebar.number_input("Weld time per weld (min)", min_value=1, value=30)
cool_time = st.sidebar.number_input("Cooling time per elbow (min)", min_value=1, value=15)
stamp_time = st.sidebar.number_input("Stamping time per elbow (min)", min_value=1, value=5)


# --- Process Simulation ---
def generate_schedule(num_elbows, welds_per_elbow, setup_time, weld_time, cool_time, stamp_time):
    schedule = []
    machine_times = {"Weld": 0, "Cool": 0, "Stamp": 0}

    for e in range(num_elbows):
        # Setup
        start = machine_times["Weld"]
        end = start + setup_time
        schedule.append((f"Elbow {e+1} - Setup", "Weld", start, end))
        machine_times["Weld"] = end

        # Welds
        for w in range(welds_per_elbow):
            start = machine_times["Weld"]
            end = start + weld_time
            schedule.append((f"Elbow {e+1} - Weld {w+1}", "Weld", start, end))
            machine_times["Weld"] = end

        # Cooling
        start = machine_times["Cool"]
        if start < end:
            start = end  # cooling starts after weld finishes
        end = start + cool_time
        schedule.append((f"Elbow {e+1} - Cool", "Cool", start, end))
        machine_times["Cool"] = end

        # Stamping
        start = machine_times["Stamp"]
        if start < end:
            start = end  # stamping starts after cooling finishes
        end = start + stamp_time
        schedule.append((f"Elbow {e+1} - Stamp", "Stamp", start, end))
        machine_times["Stamp"] = end

    return schedule, machine_times


schedule, machine_times = generate_schedule(num_elbows, welds_per_elbow, setup_time, weld_time, cool_time, stamp_time)


# --- Detect Overlaps ---
def detect_overlaps(schedule):
    overlaps = {m: 0 for m in ["Weld", "Cool", "Stamp"]}
    percentages = {m: 0 for m in ["Weld", "Cool", "Stamp"]}

    df = pd.DataFrame(schedule, columns=["Task", "Machine", "Start", "End"])

    for machine in df["Machine"].unique():
        machine_df = df[df["Machine"] == machine].sort_values("Start")
        total_time = machine_df["End"].max() - machine_df["Start"].min()

        overlap_time = 0
        prev_end = None
        for _, row in machine_df.iterrows():
            if prev_end and row["Start"] < prev_end:
                overlaps[machine] += 1
                overlap_time += min(row["End"], prev_end) - row["Start"]
            prev_end = max(prev_end or 0, row["End"])

        if total_time > 0:
            percentages[machine] = round((overlap_time / total_time) * 100, 1)

    return overlaps, percentages


overlaps, percentages = detect_overlaps(schedule)


# --- Chart ---
def plot_schedule(schedule, title="Elbow Weld Schedule"):
    colors = {"Weld": "red", "Cool": "blue", "Stamp": "green"}
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, (task, machine, start, end) in enumerate(schedule):
        ax.barh(machine, end - start, left=start, color=colors[machine], edgecolor="black")

    ax.set_xlabel("Time (minutes)")
    ax.set_title(title)
    ax.legend([Patch(color=c) for c in colors.values()], colors.keys())
    return fig


fig = plot_schedule(schedule)
st.pyplot(fig)


# --- Results ---
st.subheader("Machine Run Times")
for m, t in machine_times.items():
    st.write(f"**{m}:** {t} minutes")

st.subheader("Overlap Report")
for m in overlaps:
    st.write(f"**{m}:** {overlaps[m]} overlaps ({percentages[m]}%)")


# --- Export to PDF ---
def export_pdf(schedule, machine_times, overlaps, percentages):
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig = plot_schedule(schedule, "Elbow Weld Schedule")
        pdf.savefig(fig)
        plt.close(fig)

        # Summary page
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis("off")
        text = "Machine Run Times:\n"
        for m, t in machine_times.items():
            text += f"- {m}: {t} minutes\n"

        text += "\nOverlap Report:\n"
        for m in overlaps:
            text += f"- {m}: {overlaps[m]} overlaps ({percentages[m]}%)\n"

        ax.text(0.1, 0.9, text, va="top", fontsize=12)
        pdf.savefig(fig)
        plt.close(fig)

    buf.seek(0)
    return buf


if st.button("📄 Export PDF Report"):
    pdf_buf = export_pdf(schedule, machine_times, overlaps, percentages)
    st.download_button(
        "Download PDF",
        data=pdf_buf,
        file_name="elbow_weld_schedule.pdf",
        mime="application/pdf",
    )
