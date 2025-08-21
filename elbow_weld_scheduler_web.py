import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import base64

# --- App Title and Logo ---
logo_path = "99d58d86-f610-40c9-bdc0-b7f994e2e7a3.png"
logo_base64 = base64.b64encode(open(logo_path, "rb").read()).decode()
st.markdown(
    f"""
    <div style="text-align:center;">
        <img src="data:image/png;base64,{logo_base64}" width="200">
        <h1>Elbow Weld Scheduler</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Global Durations ---
st.sidebar.header("Global Step Durations (minutes)")
global_durations = {
    "Set up": st.sidebar.number_input("Set up duration", 5, 120, 30),
    "Stamping": st.sidebar.number_input("Stamping duration", 5, 120, 45),
    "Cooling": st.sidebar.number_input("Cooling duration", 5, 120, 20),
    "Weld": st.sidebar.number_input("Weld duration", 5, 120, 60),
}

# --- Manual Inputs ---
st.sidebar.header("Manual Inputs")
num_elbows = st.sidebar.number_input("Number of Elbows", 1, 20, 4)
welds_per_elbow = st.sidebar.selectbox("Welds per Elbow", [2, 4, 6], index=1)
machines = ["Machine A", "Machine B", "Machine C", "Machine D"]

# --- Schedule Generation ---
def generate_schedule():
    records = []
    machine_index = 0
    for elbow in range(1, num_elbows + 1):
        for weld in range(1, welds_per_elbow + 1):
            machine = machines[machine_index % len(machines)]
            start_time = (elbow - 1) * sum(global_durations.values()) + (weld - 1) * 10

            for step, duration in global_durations.items():
                records.append({
                    "Elbow": elbow,
                    "Weld": weld,
                    "Machine": machine,
                    "Step": step,
                    "Start": start_time,
                    "End": start_time + duration
                })
                start_time += duration

            machine_index += 1
    return pd.DataFrame(records)

# --- Timeline Chart ---
def plot_timeline(df, title="Weld Process Timeline"):
    colors = {"Set up": "orange", "Stamping": "green", "Cooling": "blue", "Weld": "red", "Waiting (Operator Busy)": "purple"}
    fig, ax = plt.subplots(figsize=(10, 6))

    for _, row in df.iterrows():
        ax.barh(row["Machine"], row["End"] - row["Start"], left=row["Start"], color=colors.get(row["Step"], "gray"), edgecolor="black")

    patches = [mpatches.Patch(color=c, label=s) for s, c in colors.items()]
    ax.legend(handles=patches, bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_xlabel("Time (minutes)")
    ax.set_title(title)
    st.pyplot(fig)

# --- Main Execution ---
df = generate_schedule()

st.subheader("📊 Weld Process Timeline")
plot_timeline(df)

# --- Overlap Detection ---
st.subheader("⚠️ Overlap Report")
overlap_records = []
total_overlap_time = 0

for m1 in machines:
    df1 = df[df["Machine"] == m1]
    for _, row1 in df1.iterrows():
        for m2 in machines:
            if m1 >= m2:  
                continue
            df2 = df[df["Machine"] == m2]
            for _, row2 in df2.iterrows():
                latest_start = max(row1["Start"], row2["Start"])
                earliest_end = min(row1["End"], row2["End"])
                overlap = max(0, earliest_end - latest_start)
                if overlap > 0:
                    overlap_type = f"{row1['Step']} vs {row2['Step']}"
                    overlap_records.append({
                        "Machines": f"{m1} & {m2}",
                        "Overlap Type": overlap_type,
                        "Overlap Time (min)": overlap
                    })
                    total_overlap_time += overlap

if overlap_records:
    overlap_df = pd.DataFrame(overlap_records)
    st.table(overlap_df)
else:
    st.success("No overlaps detected.")

# --- Smart Suggestions (Set up vs Set up) ---
st.subheader("💡 Smart Suggestions to Minimize Set up vs Set up Overlaps")

# Identify set up vs set up overlaps
setup_overlaps = [rec for rec in overlap_records if "Set up vs Set up" in rec["Overlap Type"]]

if setup_overlaps:
    st.write("Set up vs Set up overlaps detected. Suggesting minimal waiting times to resolve...")

    optimized_records = []
    added_waits = []

    machine_last_setup_end = {}

    for _, row in df.iterrows():
        if row["Step"] == "Set up":
            machine = row["Machine"]
            start, end = row["Start"], row["End"]

            if any(start < machine_last_setup_end.get(m, -1) for m in machines if m != machine):
                wait_start = row["End"]
                wait_end = wait_start + 10  # minimal wait placeholder
                optimized_records.append({**row, "Step": "Waiting (Operator Busy)", "Start": wait_start, "End": wait_end})
                added_waits.append({"Machine": machine, "Waiting Start": wait_start, "Waiting End": wait_end})
                machine_last_setup_end[machine] = wait_end
            else:
                machine_last_setup_end[machine] = end

        optimized_records.append(row)

    opt_df = pd.DataFrame(optimized_records)
    plot_timeline(opt_df, title="Optimized Weld Process Timeline (Reduced Set up vs Set up Overlaps)")

    if added_waits:
        st.write("Suggested Waiting Steps:")
        st.table(pd.DataFrame(added_waits))
else:
    st.success("No Set up vs Set up overlaps detected. No suggestions needed.")
