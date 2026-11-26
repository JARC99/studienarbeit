from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.style.use("bmh")
plt.rcParams["font.family"] = "serif"

DEFAULT_RESULTS_DIR = Path.home() / "Desktop" / "Studienarbeit" / "results"
DEFAULT_REF_DIR = DEFAULT_RESULTS_DIR / "Reference_Setup"
DEFAULT_SEARCH_DIR = DEFAULT_RESULTS_DIR / "VBH_TH"
DEFAULT_SAVE_DIR = Path(
    r"C:\Users\PEY-YTF\Desktop\Studienarbeit\studienarbeit\halbzeit_besprechung\graphics"
)

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


def select_reference_folder(default_ref_dir: Path) -> Path | None:
    """Return default reference folder if table.csv exists there, else prompt user."""
    if (default_ref_dir / "table.csv").exists():
        return default_ref_dir

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    init_dir = str(
        default_ref_dir.parent if default_ref_dir.parent.exists() else Path.home()
    )
    selected = filedialog.askdirectory(
        title="Select Reference Case Folder (containing table.csv)",
        initialdir=init_dir,
    )
    root.destroy()

    if not selected:
        return None
    ref_path = Path(selected)
    if not (ref_path / "table.csv").exists():
        messagebox.showwarning(
            "Reference table.csv Missing",
            f"No table.csv found in:\n{ref_path}\nReference line will be omitted.",
        )
        return None
    return ref_path


def parse_numeric_value(raw_val: object) -> float:
    """Extract leading float from strings like '1.007e+00 [-]' or '9.131e-01'."""
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


def extract_vbh_massflow_ratios(case_vars: dict[str, float]) -> dict[str, float]:
    """Return {vbh_label: ratio} for VBH stations present in this case's table.csv."""
    found: dict[str, float] = {}
    for vbh_label, tokens in VBH_GROUPS:
        for var_name, val in case_vars.items():
            if (
                "ratio" in var_name
                and "massflow" in var_name
                and any(tok in var_name for tok in tokens)
            ):
                found[vbh_label] = val
                break
    return found


def extract_vbh_total_pressure_ratios(
    case_vars: dict[str, float],
) -> dict[str, float]:
    """Return {vbh_label: total_pressure_ratio} for VBH stations in table.csv."""
    found: dict[str, float] = {}
    for vbh_label, tokens in VBH_GROUPS:
        for var_name, val in case_vars.items():
            if "totalpressureratio" in var_name and any(
                tok in var_name for tok in tokens
            ):
                found[vbh_label] = val
                break
    return found


def extract_isentropic_efficiency(case_vars: dict[str, float]) -> float:
    """Return isentropic efficiency in [%] (converts 0-1 fraction to % if needed)."""
    for var_name, val in case_vars.items():
        if "isentropicefficiency" in var_name:
            return val * 100.0 if val <= 1.0 else val
    return np.nan


def collect_cases_from_folder(
    results_dir: Path,
) -> tuple[
    list[str],
    dict[str, dict[str, float]],
    dict[str, dict[str, float]],
    dict[str, float],
]:
    """Scan subfolders for table.csv and extract metrics in alphabetical case order."""
    raw_names: list[str] = []
    mf_by_case: dict[str, dict[str, float]] = {}
    tpr_by_case: dict[str, dict[str, float]] = {}
    eta_by_case: dict[str, float] = {}

    subfolders = [p for p in results_dir.iterdir() if p.is_dir()]
    candidate_dirs = subfolders if subfolders else [results_dir]

    for cdir in candidate_dirs:
        table_file = cdir / "table.csv"
        if not table_file.exists():
            continue
        case_label = cdir.name
        case_vars = load_table_csv(table_file)
        raw_names.append(case_label)
        mf_by_case[case_label] = extract_vbh_massflow_ratios(case_vars)
        tpr_by_case[case_label] = extract_vbh_total_pressure_ratios(case_vars)
        eta_by_case[case_label] = extract_isentropic_efficiency(case_vars)

    case_names = sorted(raw_names, key=str.lower)
    return case_names, mf_by_case, tpr_by_case, eta_by_case


def _plot_grouped_vbh_bars(
    case_names: list[str],
    metric_by_case: dict[str, dict[str, float]],
    case_colors: dict[str, str],
    legend_handles: list[plt.Rectangle],
    ylabel: str,
    save_path: Path | None = None,
    tight_ylim: bool = False,
) -> None:
    vbh_labels = [label for label, _ in VBH_GROUPS]
    fig, ax = plt.subplots(1, 1)

    group_centers = np.arange(len(vbh_labels))
    bar_width = 0.14
    all_vals: list[float] = []

    for g_idx, vbh in enumerate(vbh_labels):
        present_cases = [c for c in case_names if vbh in metric_by_case.get(c, {})]
        n_bars = len(present_cases)
        if n_bars == 0:
            continue

        start_x = group_centers[g_idx] - (n_bars - 1) * bar_width / 2.0
        for j, cname in enumerate(present_cases):
            x_pos = start_x + j * bar_width
            y_val = metric_by_case[cname][vbh]
            all_vals.append(y_val)
            ax.bar(
                x_pos,
                y_val,
                width=bar_width * 0.9,
                color=case_colors[cname],
                edgecolor="none",
            )

    if tight_ylim and all_vals:
        y_min, y_max = min(all_vals), max(all_vals)
        pad = max((y_max - y_min) * 0.25, 0.0005)
        ax.set_ylim(y_min - pad, y_max + pad)

    ax.set_xticks(group_centers)
    ax.set_xticklabels(vbh_labels)
    ax.set_ylabel(ylabel)
    ax.legend(handles=legend_handles, title="CASES", loc="best", frameon=True)

    fig.tight_layout()
    plt.show()

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300)
        print(f"Saved plot to: {save_path.resolve()}")


def _plot_efficiency_by_case(
    case_names: list[str],
    eta_by_case: dict[str, float],
    case_colors: dict[str, str],
    legend_handles: list[plt.Rectangle],
    ref_eta: float = np.nan,
    save_path: Path | None = None,
) -> None:
    valid_cases = [c for c in case_names if not np.isnan(eta_by_case.get(c, np.nan))]
    if not valid_cases:
        print("[Warning] No isentropicEfficiency values found in table.csv files.")
        return

    fig, ax = plt.subplots(1, 1)
    x_pos = np.arange(len(valid_cases))
    vals = [eta_by_case[c] for c in valid_cases]
    colors = [case_colors[c] for c in valid_cases]

    ax.bar(x_pos, vals, width=0.55, color=colors, edgecolor="none")

    handles_with_ref = list(legend_handles)
    y_candidates = list(vals)
    if not np.isnan(ref_eta):
        ax.axhline(
            ref_eta,
            color="black",
            linestyle="--",
            linewidth=1.8,
            label="Reference",
        )
        handles_with_ref.append(
            plt.Line2D(
                [0],
                [0],
                color="black",
                linestyle="--",
                linewidth=1.8,
                label="Reference",
            )
        )
        y_candidates.append(ref_eta)

    y_min, y_max = min(y_candidates), max(y_candidates)
    pad = max((y_max - y_min) * 0.25, 0.05)
    ax.set_ylim(y_min - pad, y_max + pad)

    ax.set_xticks(x_pos)
    ax.set_xticklabels(valid_cases, rotation=20, ha="right")
    ax.set_ylabel("Isentropic Efficiency [%]")
    ax.legend(handles=handles_with_ref, title="CASES", loc="best", frameon=True)

    fig.tight_layout()
    plt.show()

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300)
        print(f"Saved plot to: {save_path.resolve()}")


def plot_all_table_summaries(
    results_dir: Path,
    ref_dir: Path | None = None,
    save_dir: Path | None = None,
) -> None:
    case_names, mf_by_case, tpr_by_case, eta_by_case = collect_cases_from_folder(
        results_dir
    )

    if not case_names:
        messagebox.showwarning(
            "No table.csv Found",
            f"No case folders with table.csv were found in:\n{results_dir}",
        )
        return

    ref_eta = np.nan
    if ref_dir and (ref_dir / "table.csv").exists():
        ref_vars = load_table_csv(ref_dir / "table.csv")
        ref_eta = extract_isentropic_efficiency(ref_vars)

    prop_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    case_colors = {
        cname: prop_colors[i % len(prop_colors)] for i, cname in enumerate(case_names)
    }
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=case_colors[c], label=c)
        for c in case_names
    ]

    _plot_grouped_vbh_bars(
        case_names=case_names,
        metric_by_case=mf_by_case,
        case_colors=case_colors,
        legend_handles=legend_handles,
        ylabel="VBH-to-CAV Mass Flow Ratio [%]",
        save_path=(
            save_dir / f"VBH_massflow_ratio_{results_dir.name}.png"
            if save_dir
            else None
        ),
        tight_ylim=False,
    )

    _plot_grouped_vbh_bars(
        case_names=case_names,
        metric_by_case=tpr_by_case,
        case_colors=case_colors,
        legend_handles=legend_handles,
        ylabel="Total Pressure Ratio [-]",
        save_path=(
            save_dir / f"VBH_total_pressure_ratio_{results_dir.name}.png"
            if save_dir
            else None
        ),
        tight_ylim=True,
    )

    _plot_efficiency_by_case(
        case_names=case_names,
        eta_by_case=eta_by_case,
        case_colors=case_colors,
        legend_handles=legend_handles,
        ref_eta=ref_eta,
        save_path=(
            save_dir / f"isentropic_efficiency_{results_dir.name}.png"
            if save_dir
            else None
        ),
    )


if __name__ == "__main__":
    selected_folder = select_results_folder(DEFAULT_SEARCH_DIR)
    if selected_folder:
        ref_folder = select_reference_folder(DEFAULT_REF_DIR)
        plot_all_table_summaries(
            results_dir=selected_folder,
            ref_dir=ref_folder,
            save_dir=DEFAULT_SAVE_DIR,
        )