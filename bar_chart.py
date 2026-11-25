from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# plt.rcParams["font.family"] = "serif"
plt.style.use("bmh")
plt.rcParams["mathtext.fontset"] = "dejavusans"

DEFAULT_RESULTS_DIR = Path.home() / "Desktop" / "Studienarbeit" / "results"
DEFAULT_SEARCH_DIR = DEFAULT_RESULTS_DIR / "VBH_TH"
DEFAULT_SAVE_DIR = Path(
    r"C:\Users\PEY-YTF\Desktop\Studienarbeit\studienarbeit\halbzeit_besprechung\graphics"
)

# Map each VBH group to possible variable name patterns in table.csv
VBH_GROUPS = [
    ("VBH2", ("vbh2", "le2")),
    ("VBH3", ("vbh3", "le3")),
    ("VBH4", ("vbh4", "le4")),
]


def select_results_folder(initial_dir: Path) -> Path | None:
    """Prompt user to select the folder containing case subfolders with table.csv."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    init_path = str(initial_dir if initial_dir.exists() else DEFAULT_RESULTS_DIR)
    selected = filedialog.askdirectory(
        title="Select Results Folder Containing Case Subfolders",
        initialdir=init_path,
    )
    root.destroy()

    if not selected:
        return None

    folder = Path(selected)
    if not folder.exists():
        messagebox.showerror("Error", f"Folder does not exist:\n{folder}")
        return None
    return folder


def parse_numeric_value(raw_val: object) -> float:
    """Extract leading float from strings like '4.292e+01 [%]' or '42.92'."""
    if raw_val is None or (isinstance(raw_val, float) and np.isnan(raw_val)):
        return np.nan
    s = str(raw_val).strip()
    if not s:
        return np.nan
    s_no_unit = s.split("[")[0].strip()
    match = re.match(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", s_no_unit)
    return float(match.group(0)) if match else np.nan


def load_table_csv(table_path: Path) -> dict[str, float]:
    """Read table.csv and return a {variable_name_lower: float_value} mapping."""
    for sep in [",", ";", "\t"]:
        df = pd.read_csv(table_path, sep=sep, skipinitialspace=True)
        if df.shape[1] >= 2:
            break
    else:
        return {}

    var_col = df.columns[0]
    val_col = df.columns[1]

    values: dict[str, float] = {}
    for _, row in df.iterrows():
        var_name = str(row[var_col]).strip().lower()
        if not var_name or var_name == "nan":
            continue
        num = parse_numeric_value(row[val_col])
        if not np.isnan(num):
            values[var_name] = num
    return values


def extract_vbh_massflow_ratios(
    case_vars: dict[str, float],
) -> dict[str, float]:
    """Return {vbh_label: ratio} for VBH stations present in this case's table.csv."""
    found: dict[str, float] = {}
    for vbh_label, tokens in VBH_GROUPS:
        for var_name, val in case_vars.items():
            if "ratio" in var_name and "massflow" in var_name:
                if any(tok in var_name for tok in tokens):
                    found[vbh_label] = val
                    break
    return found


def collect_cases_from_folder(
    results_dir: Path,
) -> tuple[list[str], dict[str, dict[str, float]]]:
    """Scan subfolders (or results_dir itself) for table.csv files in alphabetical order."""
    case_names: list[str] = []
    case_ratios: dict[str, dict[str, float]] = {}

    subfolders = sorted([p for p in results_dir.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
    candidate_dirs = subfolders if subfolders else [results_dir]

    for cdir in candidate_dirs:
        table_file = cdir / "table.csv"
        if not table_file.exists():
            continue
        case_label = cdir.name
        case_vars = load_table_csv(table_file)
        ratios = extract_vbh_massflow_ratios(case_vars)
        case_names.append(case_label)
        case_ratios[case_label] = ratios

    case_names.sort(key=str.lower)
    return case_names, case_ratios


def plot_vbh_massflow_ratios(
    results_dir: Path, save_dir: Path | None = None
) -> None:
    case_names, case_ratios = collect_cases_from_folder(results_dir)

    if not case_names:
        messagebox.showwarning(
            "No table.csv Found",
            f"No case folders with table.csv were found in:\n{results_dir}",
        )
        return

    vbh_labels = [label for label, _ in VBH_GROUPS]
    prop_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    case_colors = {
        cname: prop_colors[i % len(prop_colors)] for i, cname in enumerate(case_names)
    }

    fig, ax = plt.subplots(1, 1)

    group_centers = np.arange(len(vbh_labels))
    bar_width = 0.14

    for g_idx, vbh in enumerate(vbh_labels):
        present_cases = [c for c in case_names if vbh in case_ratios.get(c, {})]
        n_bars = len(present_cases)
        if n_bars == 0:
            continue

        start_x = group_centers[g_idx] - (n_bars - 1) * bar_width / 2.0
        for j, cname in enumerate(present_cases):
            x_pos = start_x + j * bar_width
            y_val = case_ratios[cname][vbh]
            ax.bar(
                x_pos,
                y_val,
                width=bar_width * 0.9,
                color=case_colors[cname],
                edgecolor="none",
            )

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=case_colors[c], label=c)
        for c in case_names
    ]

    ax.set_xticks(group_centers)
    ax.set_xticklabels(vbh_labels)
    ax.set_ylabel("VBH-to-CAV Massenstrom Verhältnis [%]")
    ax.legend(handles=legend_handles, loc="best", frameon=True)

    fig.tight_layout()
    plt.show()

    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        out_file = save_dir / f"VBH_massflow_ratio_{results_dir.name}.png"
        fig.savefig(out_file, dpi=300)
        print(f"Saved plot to: {out_file.resolve()}")


if __name__ == "__main__":
    selected_folder = select_results_folder(DEFAULT_SEARCH_DIR)
    if selected_folder:
        plot_vbh_massflow_ratios(
            results_dir=selected_folder,
            save_dir=DEFAULT_SAVE_DIR,
        )