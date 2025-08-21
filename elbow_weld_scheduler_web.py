import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import io
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
if st.button("🧹 Clear Chart & Results"):
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
    {"Pipe Size": 24, "DR": 9,  "Weld start": 16.62, "Cooling": 28},
    {"Pipe Size": 24, "DR": 11, "Weld start": 13.3,  "Cooling": 24},
    {"Pipe Size": 24, "DR": 13, "Weld start": 10.64, "Cooling": 20},
])

# Global step durations
global_steps = {"Setup": 10, "Stamping": 5}

# User inputs
st.sidebar.header("Input Parameters")
pipe_size = st.sidebar.selectbox("Pipe Size", lookup_table["Pipe Size"].unique())
dr = st.sidebar.selectbox("DR", lookup_table["DR"].unique())
machines = st.sidebar.number_input("Number of Machines", 1, 10, 3)
elbows = st.sidebar.number_input("Number of Elbows", 1, 50, 5)
welds_per_elbow = st.sidebar.selectbox("Welds per Elbow", [2, 4, 6])

# Lookup weld start + cooling
row = lookup_table[(lookup_table["Pipe Size"] == pipe_size) & (lookup_table["DR"] == dr)]
if row.empty:
    st.error("No matching entry found in lookup table.")
    st.stop()

weld_start = row["Weld start"].values[0]
cooling = row["Cooling"].values[0]

# Build process schedule
schedule = []
for m in range(machines):
    time = 0
    for e in range(elbows):
        for w in range(welds_per_elbow):
            # Setup
            schedule.append((f"Machine {m+1}", "Setup", time, time+global_steps["Setup"]))
            time += global_steps["Setup"]

            # Stamping
            schedule.append((f"Machine {m+1}", "Stamping", time, time+global_steps["Stamping"]))
            time += global_steps["Stamping"]

            # Weld start
            schedule.append((f"Machine {m+1}", "Weld start", time, time+weld_start))
            time += weld_start

            # Cooling
            schedule.append((f"Machine {m+1}", "Cooling", time, time+cooling))
            time += cooling

schedule_df = pd.DataFrame(schedule, columns=["Machine", "Step", "Start", "Finish"])

# --------------------
# Plot chart
# --------------------
fig, ax = plt.subplots(figsize=(12, 6))
colors = {"Setup": "lightblue", "Stamping": "orange", "Weld start": "green", "Cooling": "red"}
for i, row in schedule_df.iterrows():
    ax.barh(row["Machine"], row["Finish"]-row["Start"], left=row["Start"], color=colors[row["Step"]])

ax.set_xlabel("Time (minutes)")
ax.set_ylabel("Machines")
ax.set_title("Process Schedule")
ax.legend(handles=[Patch(color=c, label=s) for s,c in colors.items()])
st.pyplot(fig)

# --------------------
# Overlap detection
# --------------------
overlaps = []
for m1 in range(machines):
    df1 = schedule_df[schedule_df["Machine"] == f"Machine {m1+1}"]
    for m2 in range(m1+1, machines):
        df2 = schedule_df[schedule_df["Machine"] == f"Machine {m2+1}"]
        for _, r1 in df1.iterrows():
            for _, r2 in df2.iterrows():
                overlap_start = max(r1["Start"], r2["Start"])
                overlap_end = min(r1["Finish"], r2["Finish"])
                if overlap_start < overlap_end:
                    overlap_time = overlap_end - overlap_start
                    # classify overlap type
                    if r1["Step"] == "Setup" and r2["Step"] == "Setup":
                        otype = "Setup vs Setup"
                    elif r1["Step"] == "Stamping" and r2["Step"] == "Stamping":
                        otype = "Stamping vs Stamping"
                    else:
                        otype = "Setup vs Stamping"
                    overlaps.append((r1["Machine"], r1["Step"], r2["Machine"], r2["Step"], overlap_time, otype))

overlap_df = pd.DataFrame(overlaps, columns=["Machine1","Step1","Machine2","Step2","Overlap Time","Type"])

if not overlap_df.empty:
    st.subheader("Overlap Report")
    st.write(overlap_df)

    # summarize by machine
    machine_summary = overlap_df.groupby("Machine1")["Overlap Time"].sum().add(
        overlap_df.groupby("Machine2")["Overlap Time"].sum(), fill_value=0
    ).reset_index()
    machine_summary.columns = ["Machine","Total Overlap Time"]

    # total runtime per machine
    runtime_summary = schedule_df.groupby("Machine").apply(lambda x: x["Finish"].max()).reset_index()
    runtime_summary.columns = ["Machine","Total Runtime"]

    # merge
    merged = pd.merge(machine_summary, runtime_summary, on="Machine")
    merged["% Runtime Overlap"] = (merged["Total Overlap Time"]/merged["Total Runtime"]*100).round(2)
    st.write("### Overlap Totals per Machine")
    st.dataframe(merged)

    # summarize overlap by type
    type_summary = overlap_df.groupby("Type")["Overlap Time"].sum().reset_index()
    total_runtime_all = runtime_summary["Total Runtime"].sum()
    type_summary["% of Total Runtime"] = (type_summary["Overlap Time"]/total_runtime_all*100).round(2)
    st.write("### Overlap by Type")
    st.dataframe(type_summary)

    # Machine Utilization Grade
    total_overlap_all = type_summary["Overlap Time"].sum()
    utilization = (1 - (total_overlap_all/total_runtime_all))*100
    st.write("### Machine Utilization Grade")
    st.write(f"Utilization: **{utilization:.2f}%**")

    if utilization >= 90:
        grade = "A"
    elif utilization >= 80:
        grade = "B"
    elif utilization >= 70:
        grade = "C"
    elif utilization >= 60:
        grade = "D"
    else:
        grade = "F"

    st.markdown(f"<h1 style='text-align:center; color:green;'>{grade}</h1>", unsafe_allow_html=True)

else:
    st.success("No overlaps detected!")

# --------------------
# Export PDF
# --------------------
if st.button("📄 Export PDF"):
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        pdf.savefig(fig)

        # Add overlap summary
        fig2, ax2 = plt.subplots(figsize=(8,3))
        ax2.axis("off")
        table_data = merged[["Machine","Total Overlap Time","Total Runtime","% Runtime Overlap"]].values.tolist()
        table = ax2.table(cellText=table_data,
                          colLabels=["Machine","Total Overlap Time","Total Runtime","% Runtime Overlap"],
                          loc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        pdf.savefig(fig2)

    st.download_button("Download PDF", data=buf.getvalue(), file_name="report.pdf")
