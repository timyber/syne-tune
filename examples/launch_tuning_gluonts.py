"""
This launches an HPO tuning several hyperparameters of a gluonts model.
To run this example locally, you need to have installed dependencies in `requirements.txt` in your current interpreter.
"""
import logging
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from sagemaker.mxnet import MXNet

from sagemaker_tune.backend.local_backend import LocalBackend
from sagemaker_tune.backend.sagemaker_backend.sagemaker_backend import SagemakerBackend
from sagemaker_tune.backend.sagemaker_backend.sagemaker_utils import get_execution_role
from sagemaker_tune.optimizer.schedulers.hyperband import HyperbandScheduler
from sagemaker_tune.tuner import Tuner
from sagemaker_tune.search_space import loguniform, lograndint
from sagemaker_tune.tuner_callback import StoreResultsCallback


if __name__ == '__main__':

    logging.getLogger().setLevel(logging.INFO)
    np.random.seed(0)
    epochs = 50

    config_space = {
        "lr": loguniform(1e-4, 1e-1),
        "epochs": epochs,
        "num_cells": lograndint(lower=1, upper=80),
        "num_layers": lograndint(lower=1, upper=10),
        "dataset": "electricity"
        # "dataset": "m4_hourly"
    }

    mode = "min"
    metric = "mean_wQuantileLoss"
    entry_point = Path(__file__).parent / "training_scripts" / "gluonts" / "train_gluonts.py"

    evaluate_trials_on_sagemaker = False

    if evaluate_trials_on_sagemaker:
        # evaluate trials on Sagemaker
        backend = SagemakerBackend(
            sm_estimator=MXNet(
                entry_point=entry_point.name,
                source_dir=str(entry_point.parent),
                instance_type="ml.c5.2xlarge",
                instance_count=1,
                role=get_execution_role(),
                max_run=10 * 60,
                framework_version='1.7',
                py_version='py3',
                base_job_name='hpo-gluonts',
            ),
            # names of metrics to track. Each metric will be detected by Sagemaker if it is written in the
            # following form: "[RMSE]: 1.2", see in train_main_example how metrics are logged for an example
            metrics_names=[metric],
        )
    else:
        # evaluate trials locally, replace with SagemakerBackend to evaluate trials on Sagemaker
        backend = LocalBackend(entry_point=str(entry_point))

    # see examples to see other schedulers, mobster, Raytune, multiobjective, etc...
    scheduler = HyperbandScheduler(
        config_space,
        searcher='random',
        max_t=epochs,
        resource_attr='epoch_no',
        mode='min',
        metric=metric
    )

    wallclock_time_budget = 3600 if evaluate_trials_on_sagemaker else 60
    dollar_cost_budget = 20.0

    tuner = Tuner(
        backend=backend,
        scheduler=scheduler,
        # stops if wallclock time or dollar-cost exceeds budget,
        # dollar-cost is only available when running on Sagemaker
        stop_criterion=lambda status: status.wallclock_time > wallclock_time_budget or status.cost > dollar_cost_budget,
        n_workers=4,
        # some failures may happen when SGD diverges with NaNs
        max_failures=10,
    )

    # save results continuously
    callback = StoreResultsCallback(
        csv_file=str(Path(__file__).parent / "tuning-results-gluonts-sagemaker-hyperband.csv")
    )

    # launch the tuning
    tuner.run(
        custom_callback=callback,
    )

    # plot best result found over time
    df = callback.dataframe()
    if "time" in df:
        df = df.sort_values("time")
        df.loc[:, 'best'] = df.loc[:, metric].cummin()
        df.plot(x="time", y="best")
        plt.xlabel("wallclock time")
        plt.ylabel(metric)
        plt.show()