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

STATION = "LE2"  # Change to e.g. "LE3" or "LE4" if needed

RADIAL_STATIONS = [
    ("BL050", "50% Radius"),
    ("BL080", "80% Radius"),
    ("BL095", "95% Radius"),
]


def load_cfx_csv(filepath: Path) -> pd.DataFrame:
    """Load CFX chart CSV with [Data] header, or fall back to standard CSV."""
    lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return pd.DataFrame()

    data_idx = next(
        (i for i, line in enumerate(lines) if line.strip().lower() == "[data]"),
        None,
    )

    if data_idx is not None:
        if data_idx + 1 >= len(lines):
            return pd.DataFrame()
        df = pd.read_csv(filepath, skiprows=data_idx + 1, skipinitialspace=True)
    else:
        start_idx = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("["):
                continue
            if "," in stripped or ";" in stripped or "\t" in stripped:
                start_idx = i
                break
        if start_idx is None or start_idx >= len(lines):
            return pd.DataFrame()

        sample_line = lines[start_idx]
        sep = (
            ";"
            if ";" in sample_line
            else ("\t" if "\t" in sample_line else ",")
        )
        df = pd.read_csv(
            filepath, skiprows=start_idx, sep=sep, skipinitialspace=True
        )

    df.columns = [c.strip() for c in df.columns]
    return df


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


def find_bl_files(case_dir: Path, bl_code: str, station: str) -> list[Path]:
    """Find blade-loading CSV files matching e.g. *BL050*LE2*.csv in a case folder."""
    return sorted(case_dir.glob(f"*{bl_code}*{station}*.csv"))


def plot_blade_loading_by_radius(
    ref_dir: Path,
    cases: list[tuple[str, Path]],
    station: str = STATION,
    save_dir: Path | None = None,
) -> None:
    all_cases = [("Reference", ref_dir)] + cases
    case_names = "_vs_".join(label for label, _ in cases)

    for bl_code, radius_label in RADIAL_STATIONS:
        filenames: list[str] = []
        for _, case_dir in all_cases:
            for f in find_bl_files(case_dir, bl_code, station):
                if f.name not in filenames:
                    filenames.append(f.name)

        if not filenames:
            print(f"[Warning] No {bl_code} files found for station '{station}'.")
            continue

        for filename in filenames:
            is_pressure = (
                "ptot" in filename.lower() or "pressure" in filename.lower()
            )
            scale_factor = 1e5 if is_pressure else 1.0

            fig, ax = plt.subplots(1, 1)
            plotted = False
            x_col_name = "Streamwise (0-1)"
            y_col_name = filename.replace(".csv", "")

            for label, case_dir in all_cases:
                csv_path = case_dir / filename
                if not csv_path.exists():
                    print(f"[Warning] Missing '{filename}' in '{label}' ({case_dir})")
                    continue

                df = load_cfx_csv(csv_path)
                if df.shape[1] < 2:
                    print(f"[Warning] Empty or <2 columns in {csv_path}")
                    continue

                x_col = df.columns[0]
                y_col = df.columns[1]
                df[x_col] = pd.to_numeric(df[x_col], errors="coerce")
                df[y_col] = pd.to_numeric(df[y_col], errors="coerce")

                x_col_name = x_col
                y_col_name = (
                    "Total Pressure [$10^5$ Pa]"
                    if is_pressure
                    else y_col.split(" [")[0].strip()
                )

                df_clean = df.dropna(subset=[x_col, y_col])
                if df_clean.empty:
                    print(f"[Warning] No numeric data rows in {csv_path}")
                    continue

                linestyle = "--" if label == "Reference" else "-"
                linewidth = 2.2 if label == "Reference" else 1.8

                ax.plot(
                    df_clean[x_col],
                    df_clean[y_col] / scale_factor,
                    linestyle=linestyle,
                    linewidth=linewidth,
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
            plt.show()

            if save_dir:
                save_dir.mkdir(parents=True, exist_ok=True)
                base_stem = filename.replace(".csv", "")
                out_file = save_dir / f"{base_stem}_{case_names}.png"
                fig.savefig(out_file, dpi=300)
                print(f"Saved plot to: {out_file.resolve()}")


if __name__ == "__main__":
    ref_folder, comparison_folders = select_folders_dialog(
        ref_default=DEFAULT_REF_DIR,
        initial_search_dir=DEFAULT_SEARCH_DIR,
    )
    if ref_folder and comparison_folders:
        plot_blade_loading_by_radius(
            ref_dir=ref_folder,
            cases=comparison_folders,
            station=STATION,
            save_dir=DEFAULT_SAVE_DIR,
        )