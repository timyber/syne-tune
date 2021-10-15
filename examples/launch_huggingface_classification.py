"""
Example for how to fine-tune a DistilBERT model on the IMDB sentiment classification task using the Hugging Face SageMaker Framework.
"""
import logging
from pathlib import Path

from sagemaker.huggingface import HuggingFace

import sagemaker_tune
from sagemaker_tune.backend.sagemaker_backend.sagemaker_backend import SagemakerBackend
from sagemaker_tune.backend.sagemaker_backend.sagemaker_utils import get_execution_role
from sagemaker_tune.optimizer.schedulers.fifo import FIFOScheduler
from sagemaker_tune.tuner import Tuner
from sagemaker_tune.stopping_criterion import StoppingCriterion

from examples.training_scripts.distilbert_on_imdb.distilbert_on_imdb import \
    distilbert_imdb_benchmark, distilbert_imdb_default_params


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    
    # We pick the DistilBERT on IMDB benchmark
    # The 'benchmark' dict contains arguments needed by scheduler and
    # searcher (e.g., 'mode', 'metric'), along with suggested default values
    # for other arguments (which you are free to override)
    random_seed = 31415927
    n_workers = 4
    default_params = distilbert_imdb_default_params()
    benchmark = distilbert_imdb_benchmark(default_params)
    mode = benchmark['mode']
    metric = benchmark['metric']
    config_space = benchmark['config_space']

    # Define Hugging Face SageMaker estimator
    root = Path(sagemaker_tune.__path__[0]).parent
    huggingface_estimator = HuggingFace(
        entry_point=benchmark['script'],
        base_job_name='hpo-transformer',
        instance_type=default_params['instance_type'],
        instance_count=1,
        transformers_version='4.4',
        pytorch_version='1.6',
        py_version='py36',
        role=get_execution_role(),
        dependencies=[root / "benchmarks"],
    )

    # SageMaker backend
    backend = SagemakerBackend(
        sm_estimator=huggingface_estimator,
        metrics_names=[metric],
    )

    # Random search without stopping
    scheduler = FIFOScheduler(
        config_space,
        searcher='random',
        mode=mode,
        metric=metric,
        random_seed=random_seed
    )

    stop_criterion = StoppingCriterion(max_wallclock_time=3600)
    tuner = Tuner(
        backend=backend,
        scheduler=scheduler,
        stop_criterion=stop_criterion,
        n_workers=n_workers,
    )

    tuner.run()