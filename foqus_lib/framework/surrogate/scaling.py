import copy
import json
import logging
import math
from collections import OrderedDict

import numpy as np
import pandas as pd
from typing import Tuple


def validate_for_scaling(array_in, lo, hi) -> None:
    if not np.all(np.isfinite(array_in)):
        raise ValueError("Input data cannot contain NaN or inf values")
    if array_in.ndim != 1:
        raise ValueError("Only 1D arrays supported")
    if array_in.size < 2:
        raise ValueError("Array must have at least 2 values")
    if np.allclose(lo, hi):
        raise ValueError("Array must contain non-identical values")
    if not check_under_or_overflow(array_in):
        raise ValueError("Array contains under/overflow values for dtype")


def check_under_or_overflow(arr):
    if np.issubdtype(arr.dtype, np.integer):
        info = np.iinfo(arr.dtype)
    elif np.issubdtype(arr.dtype, np.floating):
        info = np.finfo(arr.dtype)
    else:
        raise ValueError("Unsupported data type")
    max_value = info.max
    min_value = info.min
    return np.all(arr < max_value) & np.all(arr > min_value)


def scale_linear(array_in, lo=None, hi=None):
    if lo is None:
        lo = np.min(array_in)
    if hi is None:
        hi = np.max(array_in)
    validate_for_scaling(array_in, lo, hi)
    if (hi - lo) == 0:
        result = 0
    else:
        result = (array_in - lo) / (hi - lo)
    return result


def scale_log(array_in, lo=None, hi=None):
    # need to account for log domain
    epsilon = 1e-8
    if np.any(array_in < epsilon):
        raise ValueError(f"All values must be greater than {epsilon}")
    if lo is None:
        lo = np.min(array_in)
    if hi is None:
        hi = np.max(array_in)
    validate_for_scaling(array_in, lo, hi)
    result = (np.log10(array_in) - np.log10(lo)) / (np.log10(hi) - np.log10(lo))
    return result


def scale_log2(array_in, lo=None, hi=None):
    if lo is None:
        lo = np.min(array_in)
    if hi is None:
        hi = np.max(array_in)
    validate_for_scaling(array_in, lo, hi)
    result = np.log10(9 * (array_in - lo) / (hi - lo) + 1)
    return result


def scale_power(array_in, lo=None, hi=None):
    if lo is None:
        lo = np.min(array_in)
    if hi is None:
        hi = np.max(array_in)
    validate_for_scaling(array_in, lo, hi)
    result = (np.power(10, array_in) - np.power(10, lo)) / (
        np.power(10, hi) - np.power(10, lo)
    )
    return result


def scale_power2(array_in, lo=None, hi=None):
    if lo is None:
        lo = np.min(array_in)
    if hi is None:
        hi = np.max(array_in)
    validate_for_scaling(array_in, lo, hi)
    result = 1 / 9 * (np.power(10, (array_in - lo) / (hi - lo)) - 1)
    return result


def unscale_linear(array_in, lo, hi):
    result = array_in * (hi - lo) / 1.0 + lo
    return result


def unscale_log(array_in, lo, hi):
    result = lo * np.power(hi / lo, array_in)
    return result


def unscale_log2(array_in, lo=None, hi=None):
    result = (np.power(10, array_in / 1.0) - 1) * (hi - lo) / 9.0 + lo
    return result


def unscale_power(array_in, lo, hi):
    result = np.log10(
        (array_in / 1.0) * (np.power(10, hi) - np.power(10, lo)) + np.power(10, lo)
    )
    return result


def unscale_power2(array_in, lo, hi):
    result = np.log10(9.0 * array_in / 1.0 + 1) * (hi - lo) + lo
    return result


class BaseScaler:
    """BaseScaler is the base class for the scaler classes defined
    below. It exposes the transformer interface from scikit-learn,
    and is not supposed to be instantiated directly."""

    def fit(self, X: np.ndarray):
        self.lo_ = np.min(X)
        self.hi_ = np.max(X)
        return self

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)

    def transform(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class LinearScaler(BaseScaler):
    def transform(self, X: np.ndarray) -> np.ndarray:
        return scale_linear(X, self.lo_, self.hi_)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        return unscale_linear(X, self.lo_, self.hi_)


class LogScaler(BaseScaler):
    def transform(self, X: np.ndarray) -> np.ndarray:
        return scale_log(X, self.lo_, self.hi_)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        return unscale_log(X, self.lo_, self.hi_)


class LogScaler2(BaseScaler):
    def transform(self, X: np.ndarray) -> np.ndarray:
        return scale_log2(X, self.lo_, self.hi_)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        return unscale_log2(X, self.lo_, self.hi_)


class PowerScaler(BaseScaler):
    def transform(self, X: np.ndarray) -> np.ndarray:
        return scale_power(X, self.lo_, self.hi_)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        return unscale_power(X, self.lo_, self.hi_)


class PowerScaler2(BaseScaler):
    def transform(self, X: np.ndarray) -> np.ndarray:
        return scale_power2(X, self.lo_, self.hi_)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        return unscale_power2(X, self.lo_, self.hi_)


map_name_to_scaler = {
    "Linear": LinearScaler(),
    "Log": LogScaler(),
    "Log2": LogScaler2(),
    "Power": PowerScaler(),
    "Power2": PowerScaler2(),
}


def scale_dataframe(df: pd.DataFrame, scaler: BaseScaler) -> Tuple[pd.DataFrame, dict]:
    scaled_df = pd.DataFrame(np.nan, columns=df.columns, index=df.index)
    bounds = {}

    for col_name in df:
        unscaled_col_data = df[col_name]
        scaled_col_data = scaler.fit_transform(unscaled_col_data)
        bounds[col_name] = scaler.lo_, scaler.hi_
        scaled_df.loc[:, col_name] = scaled_col_data

    return scaled_df, bounds