from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

import bar_chart
import blade_loading
import result_plotter

DEFAULT_RESULTS_DIR = Path.home() / "Desktop" / "Studienarbeit" / "results"
DEFAULT_REF_DIR = DEFAULT_RESULTS_DIR / "Reference_Setup"
DEFAULT_SEARCH_DIR = DEFAULT_RESULTS_DIR / "VBH_TH"
DEFAULT_RESULTS_GRAPHICS_DIR = (
    Path.home() / "Desktop" / "Studienarbeit" / "results_graphics"
)
STATIONS = ("LE2", "LE3", "LE4")


def select_case_folder(initial_dir: Path) -> Path | None:
    """Prompt user to select a single case folder (e.g., VBH_TH)."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    init_path = str(initial_dir if initial_dir.exists() else DEFAULT_RESULTS_DIR)
    selected = filedialog.askdirectory(
        title="Select Case Folder to Plot (e.g. VBH_TH)",
        initialdir=init_path,
    )
    root.destroy()

    if not selected:
        return None

    case_dir = Path(selected)
    if not case_dir.exists():
        messagebox.showerror("Error", f"Case folder does not exist:\n{case_dir}")
        return None
    return case_dir


def resolve_reference_folder(default_ref_dir: Path) -> Path | None:
    """Use default Reference_Setup if present, otherwise prompt user."""
    if default_ref_dir.exists():
        return default_ref_dir

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    init_dir = str(
        default_ref_dir.parent if default_ref_dir.parent.exists() else Path.home()
    )
    selected = filedialog.askdirectory(
        title="Select Reference Case Folder (Cancel to skip reference)",
        initialdir=init_dir,
    )
    root.destroy()

    return Path(selected) if selected and Path(selected).exists() else None


def discover_comparison_subfolders(case_dir: Path) -> list[tuple[str, Path]]:
    """Return sorted [(subfolder_name, subfolder_path), ...] inside case_dir."""
    subfolders = sorted(
        [p for p in case_dir.iterdir() if p.is_dir()],
        key=lambda p: p.name.lower(),
    )
    return [(p.name, p) for p in subfolders]


def _save_and_close_current(out_path: Path, show_plots: bool = False) -> None:
    """Save the active matplotlib figure as PDF and close it cleanly."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.gcf()
    fig.savefig(out_path, format="pdf", bbox_inches="tight")
    print(f"Saved: {out_path.resolve()}")
    if show_plots:
        plt.show()
    plt.close(fig)


def run_h2s_for_station(
    ref_dir: Path | None,
    cases: list[tuple[str, Path]],
    station: str,
    out_pdf: Path,
    show_plots: bool = False,
) -> None:
    """Plot 1x4 hub-to-shroud comparison (including TKE) for a given station."""
    plt.style.use("bmh")
    plt.rcParams["mathtext.fontset"] = "dejavusans"

    metrics = [
        (
            (f"alpha_out_H2S_{station}.csv", f"alpha_in_H2S_{station}.csv"),
            "Flow Angle [°]",
            1.0,
            None,
        ),
        (
            (f"Ma_out_H2S_{station}.csv", f"Ma_in_H2S_{station}.csv"),
            "Mach Number",
            1.0,
            None,
        ),
        (
            (f"Ptot_out_H2S_{station}.csv", f"Ptot_in_H2S_{station}.csv"),
            "Total Pressure [$10^5$ Pa]",
            1e5,
            3,
        ),
        (
            (
                f"TurbKE_in_H2S_{station}.csv",
                f"TurbKE_out_H2S_{station}.csv",
                f"tke_out_H2S_{station}.csv",
                f"TKE_out_H2S_{station}.csv",
            ),
            "Turbulent Kinetic Energy [m²/s²]",
            1.0,
            3,
        ),
    ]

    all_cases = ([("Reference", ref_dir)] if ref_dir else []) + cases
    fig, axes = plt.subplots(1, 4, sharey=True, figsize=(12.5, 4.5))
    any_data = False

    for ax, (candidates, xlabel, scale_factor, max_xticks) in zip(axes, metrics):
        for label, cdir in all_cases:
            csv_path = result_plotter.resolve_metric_file(cdir, candidates)
            if csv_path is None:
                continue
            df = result_plotter.load_cfx_csv(csv_path)
            if "Span Normalized" not in df.columns or df.shape[1] < 2:
                continue
            val_col = [c for c in df.columns if c != "Span Normalized"][0]
            df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
            df["Span Normalized"] = pd.to_numeric(
                df["Span Normalized"], errors="coerce"
            )
            df_clean = df.dropna(subset=["Span Normalized", val_col]).sort_values(
                by="Span Normalized"
            )
            if df_clean.empty:
                continue

            is_ref = label == "Reference"
            ax.plot(
                df_clean[val_col] / scale_factor,
                df_clean["Span Normalized"],
                linestyle="--" if is_ref else "-",
                linewidth=2.2 if is_ref else 1.8,
                label=label,
            )
            any_data = True

        ax.set_xlabel(xlabel)
        if max_xticks is not None:
            ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=max_xticks))

    if not any_data:
        plt.close(fig)
        print(
            f"[Info] No H2S data found for station '{station}', skipping {out_pdf.name}."
        )
        return

    axes[-1].legend(loc="lower right")
    axes[0].set_ylabel("Relative Channel Height")
    fig.tight_layout()
    _save_and_close_current(out_pdf, show_plots=show_plots)


def run_blade_loading_for_station(
    ref_dir: Path | None,
    cases: list[tuple[str, Path]],
    station: str,
    station_out_dir: Path,
    show_plots: bool = False,
) -> None:
    """Plot blade loading (050, 080, 095) for a given station into station_out_dir."""
    plt.style.use("bmh")
    plt.rcParams["mathtext.fontset"] = "dejavusans"

    all_cases = ([("Reference", ref_dir)] if ref_dir else []) + cases

    for bl_code, radius_label in blade_loading.RADIAL_STATIONS:
        suffix_num = re.search(r"(\d+)$", bl_code)
        file_tag = suffix_num.group(1) if suffix_num else bl_code.lower()
        out_pdf = station_out_dir / f"blade_laod_{file_tag}.pdf"

        filenames: list[str] = []
        for _, cdir in all_cases:
            for f in blade_loading.find_bl_files(cdir, bl_code, station):
                if f.name not in filenames:
                    filenames.append(f.name)

        if not filenames:
            print(
                f"[Info] No {bl_code} files for '{station}', skipping {out_pdf.name}."
            )
            continue

        filename = filenames[0]
        is_pressure = "ptot" in filename.lower() or "pressure" in filename.lower()
        scale_factor = 1e5 if is_pressure else 1.0

        fig, ax = plt.subplots(1, 1)
        plotted = False
        x_col_name = "Streamwise (0-1)"
        y_col_name = filename.replace(".csv", "")

        for label, cdir in all_cases:
            csv_path = cdir / filename
            if not csv_path.exists():
                continue
            df = blade_loading.load_cfx_csv(csv_path)
            if df.shape[1] < 2:
                continue

            x_col, y_col = df.columns[0], df.columns[1]
            x_vals = pd.to_numeric(df[x_col], errors="coerce")
            y_vals = pd.to_numeric(df[y_col], errors="coerce")
            mask = np.isfinite(x_vals) & np.isfinite(y_vals)
            if not np.any(mask):
                continue

            x_col_name = x_col
            y_col_name = (
                "Total Pressure [$10^5$ Pa]"
                if is_pressure
                else y_col.split(" [")[0].strip()
            )

            is_ref = label == "Reference"
            ax.plot(
                x_vals[mask],
                y_vals[mask] / scale_factor,
                linestyle="--" if is_ref else "-",
                linewidth=2.2 if is_ref else 1.8,
                label=label,
            )
            plotted = True

        if not plotted:
            plt.close(fig)
            continue

        ax.set_xlabel(x_col_name)
        ax.set_ylabel(y_col_name)
        ax.set_title(f"{station} — {radius_label} ({bl_code})")
        if is_pressure:
            ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=5))
        ax.legend(loc="best")
        fig.tight_layout()
        _save_and_close_current(out_pdf, show_plots=show_plots)


def run_table_summaries(
    case_dir: Path,
    ref_dir: Path | None,
    case_out_dir: Path,
    show_plots: bool = False,
) -> None:
    """Plot VBH massflow ratio, VBH total pressure ratio, and isentropic efficiency."""
    plt.style.use("bmh")
    plt.rcParams["font.family"] = "serif"

    case_names, mf_by_case, tpr_by_case, eta_by_case = (
        bar_chart.collect_cases_from_folder(case_dir)
    )
    if not case_names:
        print(f"[Info] No table.csv found in '{case_dir}', skipping bar charts.")
        return

    ref_eta = np.nan
    if ref_dir and (ref_dir / "table.csv").exists():
        ref_vars = bar_chart.load_table_csv(ref_dir / "table.csv")
        ref_eta = bar_chart.extract_isentropic_efficiency(ref_vars)

    prop_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    case_colors = {
        cname: prop_colors[i % len(prop_colors)] for i, cname in enumerate(case_names)
    }
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=case_colors[c], label=c)
        for c in case_names
    ]

    vbh_labels = [label for label, _ in bar_chart.VBH_GROUPS]
    group_centers = np.arange(len(vbh_labels))
    bar_width = 0.14

    # 1. VBH-to-CAV mass flow ratio
    fig, ax = plt.subplots(1, 1)
    for g_idx, vbh in enumerate(vbh_labels):
        present = [c for c in case_names if vbh in mf_by_case.get(c, {})]
        if not present:
            continue
        start_x = group_centers[g_idx] - (len(present) - 1) * bar_width / 2.0
        for j, cname in enumerate(present):
            ax.bar(
                start_x + j * bar_width,
                mf_by_case[cname][vbh],
                width=bar_width * 0.9,
                color=case_colors[cname],
                edgecolor="none",
            )
    ax.set_xticks(group_centers)
    ax.set_xticklabels(vbh_labels)
    ax.set_ylabel("VBH-to-CAV Mass Flow Ratio [%]")
    ax.legend(handles=legend_handles, title="CASES", loc="best", frameon=True)
    fig.tight_layout()
    _save_and_close_current(
        case_out_dir / "VBH-to-CAV_m_dot_rat.pdf", show_plots=show_plots
    )

    # 2. VBH total pressure ratio (tightened y-axis)
    fig, ax = plt.subplots(1, 1)
    all_tpr: list[float] = []
    for g_idx, vbh in enumerate(vbh_labels):
        present = [c for c in case_names if vbh in tpr_by_case.get(c, {})]
        if not present:
            continue
        start_x = group_centers[g_idx] - (len(present) - 1) * bar_width / 2.0
        for j, cname in enumerate(present):
            val = tpr_by_case[cname][vbh]
            all_tpr.append(val)
            ax.bar(
                start_x + j * bar_width,
                val,
                width=bar_width * 0.9,
                color=case_colors[cname],
                edgecolor="none",
            )
    if all_tpr:
        y_min, y_max = min(all_tpr), max(all_tpr)
        pad = max((y_max - y_min) * 0.25, 0.0005)
        ax.set_ylim(y_min - pad, y_max + pad)
    ax.set_xticks(group_centers)
    ax.set_xticklabels(vbh_labels)
    ax.set_ylabel("Total Pressure Ratio [-]")
    ax.legend(handles=legend_handles, title="CASES", loc="best", frameon=True)
    fig.tight_layout()
    _save_and_close_current(case_out_dir / "VBH_p_tot_rat.pdf", show_plots=show_plots)

    # 3. Isentropic efficiency with reference line & tightened y-axis
    valid_cases = [c for c in case_names if not np.isnan(eta_by_case.get(c, np.nan))]
    if valid_cases:
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
        _save_and_close_current(case_out_dir / "eta_iso.pdf", show_plots=show_plots)


def generate_all_for_case(
    case_dir: Path,
    ref_dir: Path | None = DEFAULT_REF_DIR,
    graphics_root: Path = DEFAULT_RESULTS_GRAPHICS_DIR,
    show_plots: bool = False,
) -> None:
    case_out_dir = graphics_root / case_dir.name
    cases = discover_comparison_subfolders(case_dir)

    for station in STATIONS:
        station_dir = case_out_dir / station
        run_h2s_for_station(
            ref_dir=ref_dir,
            cases=cases,
            station=station,
            out_pdf=station_dir / "hub-to-shroud.pdf",
            show_plots=show_plots,
        )
        run_blade_loading_for_station(
            ref_dir=ref_dir,
            cases=cases,
            station=station,
            station_out_dir=station_dir,
            show_plots=show_plots,
        )

    run_table_summaries(
        case_dir=case_dir,
        ref_dir=ref_dir,
        case_out_dir=case_out_dir,
        show_plots=show_plots,
    )


if __name__ == "__main__":
    selected_case = select_case_folder(DEFAULT_SEARCH_DIR)
    if selected_case:
        ref_folder = resolve_reference_folder(DEFAULT_REF_DIR)
        generate_all_for_case(
            case_dir=selected_case,
            ref_dir=ref_folder,
            graphics_root=DEFAULT_RESULTS_GRAPHICS_DIR,
            show_plots=False,
        )