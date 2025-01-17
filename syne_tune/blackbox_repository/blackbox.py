# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.
from numbers import Number

import pandas as pd
from typing import Optional, Callable, List, Tuple, Union, Dict
import numpy as np


ObjectiveFunctionResult = Union[Dict[str, float], np.ndarray]


class Blackbox:
    def __init__(
        self,
        configuration_space: dict,
        fidelity_space: Optional[dict] = None,
        objectives_names: Optional[List[str]] = None,
    ):
        """
        Interface aiming at following [HPOBench](https://github.com/automl/HPOBench) for compatibility.
        """
        self.configuration_space = configuration_space
        self.fidelity_space = fidelity_space
        self.objectives_names = objectives_names

    def objective_function(
        self,
        configuration: dict,
        fidelity: Union[dict, Number] = None,
        seed: Optional[int] = None,
    ) -> ObjectiveFunctionResult:
        """Returns an evaluation of the blackbox.

        First perform data check and then call `_objective_function` that should
        be overriden in the child class.

        :param configuration: configuration to be evaluated, should belong to
            `self.configuration_space`
        :param fidelity: not passing a fidelity is possible if either the blackbox
            does not have a fidelity space or if it has a single fidelity in its
            fidelity space. In the latter case, all fidelities are returned in
            form of a tensor with shape `(num_fidelities, num_objectives)`.
        :param seed: Only used if the blackbox defines multiple seeds
        :return: dictionary of objectives evaluated or tensor with shape
            `(num_fidelities, num_objectives)` if no fidelity was given.
        """
        self._check_keys(config=configuration, fidelity=fidelity)
        if self.fidelity_space is None:
            assert fidelity is None
        else:
            if fidelity is None:
                assert (
                    len(self.fidelity_space) == 1
                ), "not passing a fidelity is only supported when only one fidelity is present."

        if isinstance(fidelity, Number):
            # allows to call
            # `objective_function(configuration=..., fidelity=2)`
            # instead of
            # `objective_function(configuration=..., {'num_epochs': 2})`
            fidelity_names = list(self.fidelity_space.keys())
            assert (
                len(fidelity_names) == 1
            ), "passing numeric value is only possible when there is a single fidelity in the fidelity space."
            fidelity = {fidelity_names[0]: fidelity}

        # todo check configuration/fidelity matches their space
        return self._objective_function(
            configuration=configuration,
            fidelity=fidelity,
            seed=seed,
        )

    def _objective_function(
        self,
        configuration: dict,
        fidelity: Optional[dict] = None,
        seed: Optional[int] = None,
    ) -> ObjectiveFunctionResult:
        """
        Override this function to provide your benchmark function.
        """
        pass

    def __call__(self, *args, **kwargs) -> ObjectiveFunctionResult:
        """
        Allows to call blackbox directly as a function rather than having to call the specific method.
        :return:
        """
        return self.objective_function(*args, **kwargs)

    def _check_keys(self, config, fidelity):
        if isinstance(fidelity, dict):
            for key in fidelity.keys():
                assert key in self.fidelity_space.keys(), (
                    f'The key "{key}" passed as fidelity is not present in the fidelity space keys: '
                    f"{self.fidelity_space.keys()}"
                )
        if isinstance(config, dict):
            for key in config.keys():
                assert key in self.configuration_space.keys(), (
                    f'The key "{key}" passed in the configuration is not present in the configuration space keys: '
                    f"{self.configuration_space.keys()}"
                )

    def hyperparameter_objectives_values(
        self, predict_curves: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        If `predict_curves` is False, the shape of X is
        `(num_evals * num_seeds * num_fidelities, num_hps + 1)`, the shape of y
        is `(num_evals * num_seeds * num_fidelities, num_objectives)`.
        This can be reshaped to `(num_fidelities, num_seeds, num_evals, *)`.
        The final column of X is the fidelity value (only a single fidelity
        attribute is supported).

        If `predict_curves` is True, the shape of X is
        `(num_evals * num_seeds, num_hps)`, the shape of y is
        `(num_evals * num_seeds, num_fidelities * num_objectives)`. The latter
        can be reshaped to `(num_seeds, num_evals, num_fidelities,
        num_objectives)`.

        :return: a tuple of two dataframes (X, y), where X contains
            hyperparameters values and y contains objective values, this is
            used when fitting a surrogate model.
        """
        pass

    @property
    def fidelity_values(self) -> Optional[np.array]:
        """
        :return: Fidelity values; or None if the blackbox has none
        """
        return None


def from_function(
    configuration_space: dict,
    eval_fun: Callable,
    fidelity_space: Optional[dict] = None,
    objectives_names: Optional[List[str]] = None,
):
    """
    Helper to create a blackbox from a function, useful for test or to wrap-up real blackbox functions.
    :param configuration_space:
    :param eval_fun: function that returns dictionary of objectives given configuration and fidelity
    :param fidelity_space:
    :param objectives_names:
    :return:
    """

    class BB(Blackbox):
        def __init__(self):
            super(BB, self).__init__(
                configuration_space=configuration_space,
                fidelity_space=fidelity_space,
                objectives_names=objectives_names,
            )

        def objective_function(
            self,
            configuration: dict,
            fidelity: Optional[dict] = None,
            seed: Optional[int] = None,
        ) -> ObjectiveFunctionResult:
            return eval_fun(configuration, fidelity, seed)

    return BB()
