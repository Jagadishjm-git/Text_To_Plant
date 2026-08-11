import json
import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Set dark theme styling for matplotlib
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Segoe UI', 'Arial']

# Palette
PRIMARY_BG = '#0f172a'
CARD_BG = '#1e293b'
ACCENT_BLUE = '#38bdf8'
ACCENT_GREEN = '#4ade80'
ACCENT_RED = '#f87171'
ACCENT_PURPLE = '#c084fc'
ACCENT_AMBER = '#fbbf24'
TEXT_COLOR = '#f8fafc'

ARTIFACT_DIR = r"C:\Users\JAGADISH J M\.gemini\antigravity-ide\brain\08deffa1-ed3e-4684-8f97-267e2968b44f"

print("1. Loading benchmark_results.json...")
with open("benchmark_results.json", "r") as f:
    bench_data = json.load(f)

metrics = bench_data["metrics"]
test_cases = bench_data["test_cases"]

print("2. Generating benchmark_overview.png...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=PRIMARY_BG)
ax1.set_facecolor(CARD_BG)
ax2.set_facecolor(CARD_BG)

# Plot 1: Classification Performance Metrics
metric_names = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
metric_values = [
    metrics['Accuracy_Percentage'],
    metrics['Precision_Percentage'],
    metrics['Recall_Percentage'],
    metrics['F1_Score']
]
colors = [ACCENT_BLUE, ACCENT_GREEN, ACCENT_AMBER, ACCENT_PURPLE]

bars = ax1.bar(metric_names, metric_values, color=colors, width=0.55, edgecolor='#475569', linewidth=1.5)
ax1.set_ylim(0, 115)
ax1.set_ylabel('Percentage (%)', fontsize=12, fontweight='bold', color=TEXT_COLOR)
ax1.set_title('Plant Identification Model Performance Metrics', fontsize=14, fontweight='bold', pad=15, color=TEXT_COLOR)
ax1.grid(axis='y', linestyle='--', alpha=0.3, color='#64748b')

for bar, val in zip(bars, metric_values):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height + 3, f'{val:.1f}%',
             ha='center', va='bottom', fontsize=11, fontweight='bold', color=TEXT_COLOR)

# Plot 2: Confusion Matrix Heatmap
cm = np.array([
    [metrics['True_Positives'], metrics['False_Negatives']],
    [metrics['False_Positives'], metrics['True_Negatives']]
])
labels = np.array([
    [f"True Positive\n(Plant Identified)\n\nCount: {metrics['True_Positives']}", f"False Negative\n(Missed Plant)\n\nCount: {metrics['False_Negatives']}"],
    [f"False Positive\n(Wrong Plant)\n\nCount: {metrics['False_Positives']}", f"True Negative\n(Non-Plant Rejected)\n\nCount: {metrics['True_Negatives']}"]
])

im = ax2.imshow(cm, cmap='Blues', alpha=0.85)
ax2.set_xticks([0, 1])
ax2.set_yticks([0, 1])
ax2.set_xticklabels(['Predicted Botanical', 'Predicted Non-Plant'], fontsize=11, fontweight='bold', color=TEXT_COLOR)
ax2.set_yticklabels(['Actual Botanical', 'Actual Non-Plant'], fontsize=11, fontweight='bold', color=TEXT_COLOR)
ax2.set_title('Confusion Matrix Breakdown', fontsize=14, fontweight='bold', pad=15, color=TEXT_COLOR)

for i in range(2):
    for j in range(2):
        text_color = '#ffffff' if cm[i, j] > 2 else '#94a3b8'
        ax2.text(j, i, labels[i, j], ha='center', va='center', fontsize=11, fontweight='bold', color=text_color)

plt.tight_layout()
overview_path = "benchmark_overview.png"
plt.savefig(overview_path, dpi=300, bbox_inches='tight', facecolor=PRIMARY_BG)
plt.close()

print("3. Generating latency_analysis.png...")
fig, ax = plt.subplots(figsize=(12, 8), facecolor=PRIMARY_BG)
ax.set_facecolor(CARD_BG)

tc_ids = [tc["id"] + ": " + tc["name"] for tc in test_cases]
latencies = [tc["latency_ms"] for tc in test_cases]
statuses = [tc["status"] for tc in test_cases]
bar_colors = [ACCENT_GREEN if s == "PASS" else ACCENT_RED for s in statuses]

y_pos = np.arange(len(tc_ids))
bars = ax.barh(y_pos, latencies, color=bar_colors, edgecolor='#475569', height=0.65)
ax.set_yticks(y_pos)
ax.set_yticklabels(tc_ids, fontsize=10, fontweight='bold', color=TEXT_COLOR)
ax.invert_yaxis()  # top-down view
ax.set_xlabel('Latency (milliseconds)', fontsize=12, fontweight='bold', color=TEXT_COLOR)
ax.set_title('Inference Latency Per Benchmark Test Case', fontsize=14, fontweight='bold', pad=15, color=TEXT_COLOR)
ax.grid(axis='x', linestyle='--', alpha=0.3, color='#64748b')

# Annotate values
for bar, lat, status in zip(bars, latencies, statuses):
    width = bar.get_width()
    ax.text(width + 80, bar.get_y() + bar.get_height()/2., f'{lat} ms [{status}]',
            ha='left', va='center', fontsize=9, fontweight='bold',
            color=ACCENT_GREEN if status == "PASS" else ACCENT_RED)

plt.tight_layout()
latency_path = "latency_analysis.png"
plt.savefig(latency_path, dpi=300, bbox_inches='tight', facecolor=PRIMARY_BG)
plt.close()

print("4. Generating plant_dataset_analysis.png...")
plants_df = pd.read_csv("plants.csv")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), facecolor=PRIMARY_BG)
ax1.set_facecolor(CARD_BG)
ax2.set_facecolor(CARD_BG)

# Top Plant Families
family_counts = plants_df['Family'].value_counts().head(8)
ax1.barh(family_counts.index, family_counts.values, color=ACCENT_BLUE, edgecolor='#475569', height=0.6)
ax1.set_title('Top Plant Families in Dataset (plants.csv)', fontsize=13, fontweight='bold', pad=15, color=TEXT_COLOR)
ax1.set_xlabel('Count', fontsize=11, color=TEXT_COLOR)
ax1.invert_yaxis()
ax1.grid(axis='x', linestyle='--', alpha=0.3, color='#64748b')

for bar in ax1.patches:
    ax1.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2., f'{int(bar.get_width())}',
             ha='left', va='center', fontsize=10, fontweight='bold', color=TEXT_COLOR)

# Plant Types
type_counts = plants_df['Plant_Type'].value_counts().head(8)
ax2.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%',
        colors=[ACCENT_GREEN, ACCENT_AMBER, ACCENT_PURPLE, ACCENT_BLUE, '#ec4899', '#14b8a6', '#f97316', '#6366f1'],
        textprops={'color': TEXT_COLOR, 'fontsize': 10, 'weight': 'bold'}, wedgeprops={'edgecolor': '#1e293b', 'linewidth': 2})
ax2.set_title('Plant Type Composition', fontsize=13, fontweight='bold', pad=15, color=TEXT_COLOR)

plt.tight_layout()
dataset_path = "plant_dataset_analysis.png"
plt.savefig(dataset_path, dpi=300, bbox_inches='tight', facecolor=PRIMARY_BG)
plt.close()

# Copy all images to artifact directory
os.makedirs(ARTIFACT_DIR, exist_ok=True)
shutil.copy(overview_path, os.path.join(ARTIFACT_DIR, overview_path))
shutil.copy(latency_path, os.path.join(ARTIFACT_DIR, latency_path))
shutil.copy(dataset_path, os.path.join(ARTIFACT_DIR, dataset_path))

print("All plot images generated and saved successfully!")
