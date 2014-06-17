#!/usr/bin/python

from pid_controller import PIDController
from power import OutPower, InPower
from thermal import Thermal, ThermalGovernor
from results import CR2, get_results, combine_results

def summary_plots(**kwords):
    """A summary of plots as similar as possible to what CompareRuns plots"""

    if "path" in kwords:
        path = kwords["path"]
        del kwords["path"]
    else:
        path = None

    gov_data = ThermalGovernor(path=path)
    pid_data = PIDController(path=path)

    if "width" not in kwords:
        kwords["width"] = 20
    if "height" not in kwords:
        kwords["height"] = 5

    gov_data.plot_temperature(**kwords)
    pid_data.plot_controller(**kwords)
    gov_data.plot_input_power(**kwords)
    gov_data.plot_output_power(**kwords)
