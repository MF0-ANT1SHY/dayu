import os
import sqlite3
import matplotlib.pyplot as plt
import numpy as np
import argparse

# 确保img目录存在
os.makedirs("img", exist_ok=True)

# 灰度颜色 + hatching patterns
colors = ["#D41A1A", "#DFAC3E", "#C5E02C", "#aaaaaa"]
hatches = ["/", "\\", "x", "//"]

def parse_args():
    parser = argparse.ArgumentParser(description="Plot metrics from SQLite database.")
    parser.add_argument("db", type=str, help="Path to the SQLite database file.")
    return parser.parse_args()

# === 数据处理函数 ===
def load_summary_metrics(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT r.run_id, r.abc_file,
               s.ratio_indirect, s.ratio_throw,
               s.ratio_opaque, s.ratio_external
        FROM summary_metrics s
        JOIN runs r ON s.run_id = r.run_id
        ORDER BY r.run_id
    """)
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return [], np.array([])
    run_names = [os.path.splitext(os.path.basename(row[1]))[0] for row in rows]
    ratios = np.array([[row[2], row[3], row[4], row[5]] for row in rows])
    return run_names, ratios

def load_dependency_metrics(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT dependency_name, SUM(call_count) as total_calls
        FROM external_dependency_metrics
        GROUP BY dependency_name
        ORDER BY total_calls DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

# === 绘图逻辑函数 ===
def clustered_bar_chart(run_names, ratios):
    if len(run_names) == 0:
        print("No data found for summary_metrics.")
        return

    n_runs = len(run_names)
    n_metrics = ratios.shape[1]

    x = np.arange(n_runs)
    bar_width = 0.18
    fig, ax = plt.subplots(figsize=(5, 3))  # IEEE S&P 单栏大小

    labels = ["Indirect", "Throw", "Opaque", "External"]

    for i in range(n_metrics):
        ax.bar(
            x + i * bar_width,
            ratios[:, i],
            width=bar_width,
            color=colors[i],
            hatch=hatches[i],
            edgecolor="black",
            label=labels[i]
        )
        # 平均值线
        avg_val = ratios[:, i].mean()
        ax.hlines(
            y=avg_val,
            xmin=-0.2,
            xmax=n_runs - 0.8 + n_metrics * bar_width,
            colors=colors[i],
            linestyles="dashed",
            linewidth=1.0,
            label=f"{labels[i]} Avg ({avg_val:.2f})"
        )

    ax.set_xticks(x + bar_width * (n_metrics - 1) / 2)
    ax.set_xticklabels(run_names, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Ratio", fontsize=9)
    ax.set_ylim(0, 1)

    ax.legend(fontsize=7, ncol=2, frameon=False)
    ax.tick_params(axis="y", labelsize=8)
    ax.tick_params(axis="x", labelsize=7)

    plt.tight_layout()
    plt.savefig("img/ratios_bar.png", dpi=900, bbox_inches="tight")
    plt.close()

def pie_chart(dep_rows):
    if not dep_rows:
        print("No data found for external_dependency_metrics.")
        return

    top10 = dep_rows[:10]
    others = dep_rows[10:]
    labels = [r[0] for r in top10]
    values = [r[1] for r in top10]
    if others:
        labels.append("Others")
        values.append(sum(r[1] for r in others))

    fig, ax = plt.subplots(figsize=(5, 3))
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        colors=["#444444", "#555555", "#666666", "#777777", "#888888",
                "#999999", "#aaaaaa", "#bbbbbb", "#cccccc", "#dddddd", "#eeeeee"],
        wedgeprops={"edgecolor": "black", "linewidth": 0.5}
    )

    for t in texts + autotexts:
        t.set_fontsize(7)

    ax.axis("equal")  # 保持圆形
    plt.tight_layout()
    plt.savefig("img/dependency_pie.png", dpi=900, bbox_inches="tight")
    plt.close()

# === 主程序 ===
if __name__ == "__main__":
    args = parse_args()
    if args.db is None or not os.path.isfile(args.db):
        print("Please provide a valid path to the SQLite database file.")
        exit(1)

    run_names, ratios = load_summary_metrics(args.db)
    clustered_bar_chart(run_names, ratios)

    dep_rows = load_dependency_metrics(args.db)
    pie_chart(dep_rows)

    print("Figures saved in img/ratios_bar.png and img/dependency_pie.png")