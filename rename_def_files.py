from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# SLURM script template
SLURM_TEMPLATE = """#! /bin/bash -l
#SBATCH -J <NAME>
#SBATCH -oe
#SBATCH --ntasks=64
#SBATCH --time=20:00:00
#SBATCH --mem-per-cpu=4G
#SBATCH --mail-user=jose.alfredo.rosas.cordova@stud.uni-hannover.de
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --partition=amo,phd,taurus,mpp.share

cd $SLURM_SUBMIT_DIR

module load GCC/13.2.0
module load OpenMPI/4.1.6
module load ANSYS/2025.2

HOST=$(expand-slurm-nodelist --cfx)
echo $HOST
export ANSWAIT=1

cfx5solve -v -def <NAME>.def -par-dist $HOST -size-par 1.4 -size 1.4 -double -start-method 'Open MPI Distributed Parallel'
"""


def handle_bash_scripts(folder_path, new_name):
    """Updates job_script.bash if it exists, or creates a new job_script.bash with UNIX line endings."""
    script_path = folder_path / "job_script.bash"

    if script_path.exists():
        try:
            # Read content safely (handles whatever line endings are currently there)
            content = script_path.read_text(encoding="utf-8")
            updated_content = content.replace("<NAME>", new_name)

            # Force UNIX line endings (\n) upon writing
            script_path.write_text(updated_content, encoding="utf-8", newline="\n")
            print(f"  -> Updated existing: job_script.bash (forced UNIX line endings)")
            return 1
        except Exception as e:
            print(f"  -> Error updating job_script.bash: {e}")
            return 0
    else:
        try:
            script_content = SLURM_TEMPLATE.replace("<NAME>", new_name)

            # Force UNIX line endings (\n) upon writing
            script_path.write_text(script_content, encoding="utf-8", newline="\n")
            print(f"  -> Created new: job_script.bash with UNIX line endings")
            return 1
        except Exception as e:
            print(f"  -> Error creating job_script.bash in {folder_path.name}: {e}")
            return 0


def process_root_folder(root_directory):
    root_path = Path(root_directory)

    if not root_path.exists():
        print(f"Error: The directory '{root_directory}' does not exist.")
        return

    renamed_count = 0
    total_scripts_handled = 0

    all_folders = [p for p in root_path.rglob("*") if p.is_dir()]

    for folder in all_folders:
        folder_name = folder.name
        if not folder_name:
            continue

        print(f"\nProcessing folder: {folder_name}")
        primary_name = folder_name
        def_files = list(folder.glob("*.def"))

        if def_files:
            for def_file in def_files:
                new_name = folder_name + def_file.suffix
                target_path = folder / new_name

                if def_file != target_path:
                    current_target = target_path
                    counter = 1
                    while current_target.exists() and current_target != def_file:
                        current_target = folder / f"{folder_name}_{counter}{def_file.suffix}"
                        counter += 1

                    def_file.rename(current_target)
                    print(f"  -> Renamed .def: {def_file.name} -> {current_target.name}")
                    renamed_count += 1
                    primary_name = current_target.stem
                else:
                    print(f"  -> .def already matches folder name: {def_file.name}")
                    primary_name = def_file.stem
        else:
            print(f"  -> No .def file found. Using folder name '{folder_name}'.")

        total_scripts_handled += handle_bash_scripts(folder, primary_name)

    print(f"\nProcessing complete!")
    print(f"Total .def files renamed: {renamed_count}")
    print(f"Total job_script.bash files updated/created: {total_scripts_handled}")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    print("Opening folder selection dialog...")
    target_dir = filedialog.askdirectory(title="Select Root Folder Containing Subfolders")

    if target_dir:
        print(f"Selected directory: {target_dir}\n")
        process_root_folder(target_dir)
    else:
        print("No folder selected. Operation cancelled.")