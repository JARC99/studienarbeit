from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tabulate import tabulate

plt.rcParams["font.family"] = "serif"
plt.style.use('bmh')

if __name__ == "__main__":
    meshconv_dir = Path(r"..\cluster_batches\Mesh_Convergence")

    subfolder_list = [item.name for item in meshconv_dir.iterdir() if item.is_dir()]
    eta_s_f_list = []
    mesh_bsize_list = []

    fig, ax = plt.subplots(1, 1)
    for subfolder in subfolder_list[:]:
        df = pd.read_csv(meshconv_dir / subfolder / f"{subfolder}_eta_s.csv", skiprows=4)

        t_step_series = df["Accumulated Timestep"]
        eta_s_series = df["Total To Total Device Efficiency (Isentropic Expansion (%))"]
        eta_p_series = df["Total To Total Device Efficiency (Polytropic Expansion (%))"]

        ax.plot(t_step_series, eta_s_series)
        # ax.plot(t_step_series, eta_p_series, label=subfolder)

        mesh_bsize_list.append(float(subfolder.split("S")[-1]) * 10 / 10 ** len(subfolder.split("S")[-1]))
        eta_s_f_list.append(eta_s_series.iloc[-1])
    mesh_bsize_array = np.array(mesh_bsize_list)
    eta_s_f_array = np.array(eta_s_f_list)

headers = ["Name", "Mesh Body Sizing [mm]", "Isentropic Efficiency [%]"]
table_data = list(zip(subfolder_list, mesh_bsize_array, eta_s_f_array))
print(tabulate(table_data, headers, tablefmt="fancy_grid", numalign="right", floatfmt=(".s", ".2f",)))

ax.set_xlabel("Timestep")
ax.set_ylabel("Isentropic Efficiency [%]")
ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
ax.legend(labels=[f"{mesh_bsize:.2f}" for mesh_bsize in mesh_bsize_list], title="Mesh Body Sizing [mm]",
          alignment="left")

tol_val = 0.01  # %
fig1, ax1 = plt.subplots(1, 1)
ax1.errorbar(mesh_bsize_array, eta_s_f_array, yerr=eta_s_f_array * tol_val / 100, fmt="o", ecolor="gray",
             elinewidth=1.5,
             capsize=4, label=f" ± {tol_val} %")

ax1.set_xlabel("Mesh Body Sizing [mm]")
ax1.set_ylabel("Isentropic Efficiency [%]")
ax1.set_xticks(mesh_bsize_list)
ax1.legend(loc="lower right")

fig.tight_layout()
fig1.tight_layout()
plt.show()
