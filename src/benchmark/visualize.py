from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns

_DIFF_RE = re.compile(r"_(easy|medium|hard)", re.IGNORECASE)
_SIZE_RE = re.compile(r"_(\d+)x\d+")
_DIFF_ORDER = ["easy", "medium", "hard"]
_DIFF_RANK = {d: i for i, d in enumerate(_DIFF_ORDER)}
_DIFF_LABEL = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}

# Heatmap palette: smooth red (0) -> light neutral centre -> green (1)
# diverging_palette(h_neg, h_pos) uses HSL hue 10 (warm red) and 133 (mid green),
# routing through a near-white midpoint for a perceptually smooth gradient.
_HEATMAP_CMAP = sns.diverging_palette(10, 133, s=75, l=50, as_cmap=True)


# --- data loading / preparation -----------------------------------------------

def _extract_difficulty(filename: str) -> str:
    m = _DIFF_RE.search(filename)
    return m.group(1).lower() if m else "unknown"


def _extract_size(filename: str) -> int | None:
    m = _SIZE_RE.search(filename)
    return int(m.group(1)) if m else None


def _ops_count(row: pd.Series) -> float:
    """node_expansions for A* solvers, inference_count for everything else."""
    if "A*" in str(row["solver_name"]):
        return float(row["node_expansions"])
    return float(row["inference_count"])


def load_all_csvs(data_dir: Path) -> pd.DataFrame:
    frames = [pd.read_csv(p) for p in sorted(data_dir.glob("*.csv"))]
    if not frames:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    return pd.concat(frames, ignore_index=True)


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived columns, then average duplicate rows (e.g. two Medium puzzles
    per size) so each (solver, size, difficulty) maps to one data point.
    """
    df = df.copy()
    df["difficulty"] = df["input_file"].apply(_extract_difficulty)
    df["ops_count"] = df.apply(_ops_count, axis=1)
    df["diff_rank"] = df["difficulty"].map(_DIFF_RANK).fillna(99).astype(int)

    agg = (
        df.groupby(
            ["solver_name", "puzzle_size", "difficulty", "diff_rank"],
            as_index=False,
        )
        .agg(
            time_ms=("time_ms", "mean"),
            memory_kb=("memory_kb", "mean"),
            ops_count=("ops_count", "mean"),
            completion_ratio=("completion_ratio", "mean"),
        )
    )
    agg["x_label"] = agg.apply(
        lambda r: (
            f"{r['puzzle_size']}\u00d7{r['puzzle_size']}\n"
            f"{_DIFF_LABEL.get(r['difficulty'], r['difficulty'])}"
        ),
        axis=1,
    )
    return agg.sort_values(["puzzle_size", "diff_rank"]).reset_index(drop=True)


def _x_order(df: pd.DataFrame) -> list[str]:
    return list(
        dict.fromkeys(df.sort_values(["puzzle_size", "diff_rank"])["x_label"])
    )


# --- line charts --------------------------------------------------------------

def _plot_line_chart(
    df: pd.DataFrame,
    metric: str,
    title: str,
    ylabel: str,
    output_path: Path | None,
    log_scale: bool = False,
) -> None:
    x_order = _x_order(df)
    solvers = sorted(df["solver_name"].unique())
    palette = sns.color_palette("tab10", n_colors=len(solvers))

    fig, ax = plt.subplots(figsize=(16, 6))
    for solver, color in zip(solvers, palette):
        # reindex so missing puzzle configs become NaN -- matplotlib will
        # naturally break (stop) the line there instead of connecting gaps.
        sub = (
            df[df["solver_name"] == solver]
            .set_index("x_label")
            .reindex(x_order)
        )
        ax.plot(
            x_order,
            sub[metric].values,
            marker="o",
            label=solver,
            color=color,
            linewidth=1.8,
            markersize=5,
        )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("Puzzle Size & Difficulty", fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_xticks(range(len(x_order)))
    ax.set_xticklabels(x_order, fontsize=8)

    if log_scale:
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
    else:
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"{v:,.1f}")
        )

    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        borderaxespad=0,
        fontsize=8,
        framealpha=0.9,
    )
    plt.tight_layout()
    _save_or_show(fig, output_path)


# --- heatmap ------------------------------------------------------------------

def _plot_heatmap(df: pd.DataFrame, output_path: Path | None) -> None:
    x_order = _x_order(df)
    pivot = df.pivot_table(
        index="solver_name",
        columns="x_label",
        values="completion_ratio",
        aggfunc="mean",
    ).reindex(columns=x_order)

    missing_mask = pivot.isna()

    fig_w = max(14, len(x_order) * 0.85)
    fig_h = max(4, len(pivot) * 0.6)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    # Draw known cells only (NaN cells are left transparent by mask=).
    sns.heatmap(
        pivot,
        mask=missing_mask,
        annot=True,
        fmt=".2f",
        cmap=_HEATMAP_CMAP,
        vmin=0,
        vmax=1,
        linewidths=0.4,
        linecolor="white",
        ax=ax,
        cbar_kws={"label": "Completion Ratio"},
    )

    # Fill missing cells with light grey and annotate "N/A".
    n_rows, n_cols = pivot.shape
    for ri in range(n_rows):
        for ci in range(n_cols):
            if missing_mask.iloc[ri, ci]:
                ax.add_patch(
                    mpatches.Rectangle(
                        (ci, ri), 1, 1,
                        facecolor="#cccccc",
                        edgecolor="white",
                        linewidth=0.4,
                        zorder=2,
                    )
                )
                ax.text(
                    ci + 0.5, ri + 0.5, "N/A",
                    ha="center", va="center",
                    fontsize=8, color="#555555",
                    zorder=3,
                )

    ax.set_title("Completion Ratio", fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel("Puzzle Size & Difficulty", fontsize=11)
    ax.set_ylabel("Solver", fontsize=11)
    ax.tick_params(axis="x", labelsize=8)
    ax.tick_params(axis="y", labelsize=8, rotation=0)
    plt.tight_layout()
    _save_or_show(fig, output_path)


# --- LaTeX tables -------------------------------------------------------------

def _tex_escape(text: str) -> str:
    """Escape characters that are special in LaTeX."""
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("$",  r"\$"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("{",  r"\{"),
        ("}",  r"\}"),
        ("~",  r"\textasciitilde{}"),
        ("^",  r"\textasciicircum{}"),
    ]
    for char, repl in replacements:
        text = text.replace(char, repl)
    return text


def _build_latex_table(df: pd.DataFrame, caption: str, label: str) -> str:
    """
    Build a longtable LaTeX string from a raw single-solver DataFrame.

    Columns: Test Case | Size | Difficulty | Algorithm |
             Time (s)  | Memory (KB) | Exp./Inf. | Completion Ratio
    """
    col_spec = r"@{}lccl r r r c@{}"
    header_cells = [
        r"Test Case",
        r"Size",
        r"Difficulty",
        r"Algorithm",
        r"Time (s)",
        r"Memory (KB)",
        r"Exp./Inf.",
        r"Completion",
    ]
    header = " & ".join(r"\textbf{" + h + r"}" for h in header_cells)

    lines: list[str] = []
    lines += [
        r"\begin{longtable}{" + col_spec + r"}",
        r"  \caption{" + _tex_escape(caption) + r"} \label{" + label + r"} \\",
        r"  \toprule",
        f"  {header} \\\\",
        r"  \midrule",
        r"  \endfirsthead",
        r"  \multicolumn{8}{c}{\tablename\ \thetable{} -- continued} \\",
        r"  \toprule",
        f"  {header} \\\\",
        r"  \midrule",
        r"  \endhead",
        r"  \midrule",
        r"  \multicolumn{8}{r}{\textit{Continued on next page}} \\",
        r"  \endfoot",
        r"  \bottomrule",
        r"  \endlastfoot",
    ]

    df = df.copy()
    df["difficulty"] = df["input_file"].apply(_extract_difficulty)
    df["ops_count"] = df.apply(_ops_count, axis=1)
    df["diff_rank"] = df["difficulty"].map(_DIFF_RANK).fillna(99).astype(int)
    df = df.sort_values(["puzzle_size", "diff_rank", "input_file"]).reset_index(drop=True)

    for _, row in df.iterrows():
        stem = Path(str(row["input_file"])).stem          # puzzle_01_4x4_easy
        n = int(row["puzzle_size"])
        diff = _DIFF_LABEL.get(str(row["difficulty"]), str(row["difficulty"]))
        algo = _tex_escape(str(row["solver_name"]))
        time_s = float(row["time_ms"]) / 1000.0
        mem = float(row["memory_kb"])
        ops = int(row["ops_count"])
        ratio = float(row["completion_ratio"])

        cells = [
            r"\texttt{" + _tex_escape(stem) + r"}",
            f"${n}\\times{n}$",
            diff,
            algo,
            f"{time_s:.4f}",
            f"{mem:.2f}",
            f"{ops:,}".replace(",", r"\,"),
            f"{ratio:.2f}",
        ]
        lines.append("  " + " & ".join(cells) + r" \\")

    lines.append(r"\end{longtable}")
    return "\n".join(lines)


def _latex_document_wrap(body: str, solver_name: str) -> str:
    return (
        r"""\documentclass{article}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{geometry}
\geometry{margin=2cm, landscape}

\begin{document}

"""
        + body
        + "\n\n"
        + r"\end{document}"
        + "\n"
    )


def generate_latex_tables(data_dir: Path, output_dir: Path) -> None:
    """Write one .tex file per CSV found in data_dir."""
    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    for csv_path in csv_files:
        df = pd.read_csv(csv_path)
        if df.empty:
            continue

        solver_name = str(df["solver_name"].iloc[0])
        caption = f"Benchmark results -- {solver_name}"
        label = "tab:" + re.sub(r"[^a-z0-9]", "_", solver_name.lower()).strip("_")

        body = _build_latex_table(df, caption=caption, label=label)
        doc = _latex_document_wrap(body, solver_name)

        out_path = output_dir / csv_path.with_suffix(".tex").name
        out_path.write_text(doc, encoding="utf-8")
        print(f"Saved: {out_path}")


# --- helpers ------------------------------------------------------------------

def _save_or_show(fig: plt.Figure, output_path: Path | None) -> None:
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved: {output_path}")
    else:
        plt.show()
    plt.close(fig)


# --- public entry point -------------------------------------------------------

def visualize(data_dir: Path, output_dir: Path | None = None) -> None:
    df_raw = load_all_csvs(data_dir)
    df = prepare_data(df_raw)

    line_charts = [
        ("time_ms",   "Runtime (ms, log scale)", "Time (ms)",   True),
        ("memory_kb", "Memory Usage (KB)",        "Memory (KB)", False),
        (
            "ops_count",
            "Operations Count  (node_expansions for A*,  inference_count for others)",
            "Count",
            False,
        ),
    ]
    for metric, title, ylabel, log_scale in line_charts:
        out = (output_dir / f"benchmark_{metric}.png") if output_dir else None
        _plot_line_chart(df, metric, title, ylabel, out, log_scale=log_scale)

    out = (output_dir / "benchmark_completion_ratio.png") if output_dir else None
    _plot_heatmap(df, out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Visualize benchmark CSV results with line charts and a heatmap."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "resource" / "output",
        help="Directory containing benchmark CSV files (default: resource/output/).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Save PNGs here instead of displaying interactively.",
    )
    parser.add_argument(
        "--latex-dir",
        type=Path,
        default=None,
        help="Generate LaTeX tables and save .tex files to this directory.",
    )
    args = parser.parse_args(argv)

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    visualize(data_dir=args.data_dir, output_dir=args.output_dir)

    if args.latex_dir:
        generate_latex_tables(data_dir=args.data_dir, output_dir=args.latex_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
