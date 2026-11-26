from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

# plt.rcParams["font.family"] = "serif"
plt.style.use("bmh")
plt.rcParams["mathtext.fontset"] = "dejavusans"

DEFAULT_RESULTS_DIR = Path.home() / "Desktop" / "Studienarbeit" / "results"
DEFAULT_REF_DIR = DEFAULT_RESULTS_DIR / "Reference_Setup"
DEFAULT_SEARCH_DIR = DEFAULT_RESULTS_DIR / "VBH_TH"
DEFAULT_SAVE_DIR = Path(
    r"C:\Users\PEY-YTF\Desktop\Studienarbeit\studienarbeit\halbzeit_besprechung\graphics"
)

# Each entry: (candidate_filenames_tuple, xlabel, title, scale_factor, max_xticks)
METRICS = [
    (
        ("alpha_out_H2S_LE2.csv",),
        "Flow Angle [°]",
        "Velocity Flow Angle ACA",
        1.0,
        None,
    ),
    (
        ("Ma_out_H2S_LE2.csv",),
        "Mach Number",
        "Mach Number ACA",
        1.0,
        None,
    ),
    (
        ("Ptot_out_H2S_LE2.csv",),
        "Total Pressure [$10^5$ Pa]",
        "Total Pressure ACA",
        1e5,
        3,
    ),
    (
        (
            "TurbKE_out_H2S_LE2.csv",
            "TurbKE_in_H2S_LE2.csv",
            "tke_out_H2S_LE2.csv",
            "TKE_out_H2S_LE2.csv",
        ),
        "Turbulent Kinetic Energy [m²/s²]",
        "Turbulence Kinetic Energy ACA",
        1.0,
        3,
    ),
]


def load_cfx_csv(filepath: Path) -> pd.DataFrame:
    """Load CFX chart CSV starting after the [Data] section header."""
    lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    data_idx = next(i for i, line in enumerate(lines) if line.strip().lower() == "[data]")
    df = pd.read_csv(filepath, skiprows=data_idx + 1, skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]
    return df


def resolve_metric_file(case_dir: Path, candidates: tuple[str, ...]) -> Path | None:
    """Return the first existing CSV path from candidate names in case_dir."""
    for name in candidates:
        candidate_path = case_dir / name
        if candidate_path.exists():
            return candidate_path
    return None


def select_folders_dialog(
    ref_default: Path, initial_search_dir: Path
) -> tuple[Path | None, list[tuple[str, Path]]]:
    """Prompt user for the Reference folder and one or more comparison folders."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    ref_initial = str(ref_default if ref_default.exists() else DEFAULT_RESULTS_DIR)
    ref_selected = filedialog.askdirectory(
        title="Select Reference Case Folder (Cancel to use default)",
        initialdir=ref_initial,
    )
    ref_dir = Path(ref_selected) if ref_selected else ref_default
    if not ref_dir.exists():
        messagebox.showerror("Error", f"Reference folder does not exist:\n{ref_dir}")
        root.destroy()
        return None, []

    search_initial = str(
        initial_search_dir if initial_search_dir.exists() else ref_dir.parent
    )
    selected_cases: list[tuple[str, Path]] = []

    while True:
        folder_str = filedialog.askdirectory(
            title=f"Select a Case Folder to Compare ({len(selected_cases)} selected) — Cancel when done",
            initialdir=search_initial,
        )
        if not folder_str:
            break

        case_path = Path(folder_str)
        search_initial = str(case_path.parent)
        selected_cases.append((case_path.name, case_path))

    root.destroy()

    if not selected_cases:
        messagebox.showwarning(
            "No Cases Selected", "No comparison folders were selected. Exiting."
        )
        return None, []

    return ref_dir, selected_cases


def plot_comparison_1x4(
    ref_dir: Path, cases: list[tuple[str, Path]], save_path: Path | None = None
) -> None:
    all_cases = [("Reference", ref_dir)] + cases
    fig, axes = plt.subplots(1, 4, sharey=True, figsize=(12.5, 4.5))

    for ax, (candidates, xlabel, title, scale_factor, max_xticks) in zip(
        axes, METRICS
    ):
        for label, case_dir in all_cases:
            csv_path = resolve_metric_file(case_dir, candidates)
            if csv_path is None:
                print(
                    f"[Warning] Missing {candidates[0]} in '{label}' ({case_dir})"
                )
                continue

            df = load_cfx_csv(csv_path)
            val_col = [c for c in df.columns if c != "Span Normalized"][0]
            df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
            df["Span Normalized"] = pd.to_numeric(
                df["Span Normalized"], errors="coerce"
            )
            df = df.dropna(subset=["Span Normalized", val_col]).sort_values(
                by="Span Normalized"
            )

            linestyle = "--" if label == "Reference" else "-"
            linewidth = 2.2 if label == "Reference" else 1.8
            ax.plot(
                df[val_col] / scale_factor,
                df["Span Normalized"],
                linestyle=linestyle,
                linewidth=linewidth,
                label=label,
            )

        ax.set_xlabel(xlabel)
        # ax.set_title(title)
        if max_xticks is not None:
            ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=max_xticks))

    axes[-1].legend(loc="lower right")
    axes[0].set_ylabel("Relative Channel Height")

    fig.tight_layout()
    plt.show()

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300)
        print(f"Saved plot to: {save_path.resolve()}")


if __name__ == "__main__":
    ref_folder, comparison_folders = select_folders_dialog(
        ref_default=DEFAULT_REF_DIR,
        initial_search_dir=DEFAULT_SEARCH_DIR,
    )
    if ref_folder and comparison_folders:
        case_names = "_vs_".join(label for label, _ in comparison_folders)
        out_file = DEFAULT_SAVE_DIR / f"LE2_outlet_H2S_{case_names}.png"
        plot_comparison_1x4(
            ref_dir=ref_folder,
            cases=comparison_folders,
            save_path=out_file,
        )