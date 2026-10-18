from dataclasses import dataclass, field
from typing import Any
from pathlib import Path

import json
import pickle
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC, SVC

from stream_analyzer import StreamAnalyzer

MODEL_B_PIPELINE = "B: log1p <=8kHz + scaler + LinearSVC"
MODEL_LINEAR_SVC = "LinearSVC"
MODEL_POLY_SVC = "SVC poly degree 1"
MODEL_OPTIONS = [MODEL_B_PIPELINE, MODEL_LINEAR_SVC, MODEL_POLY_SVC]
DEFAULT_MODEL_TYPE = MODEL_B_PIPELINE

N_FFT_FEATURES = 1200  # frozen 48 kHz / 50 ms profile; bin i ~ 20*(i+1) Hz
FFT_BIN_HZ = 20.0
B_MAX_HZ = 8000.0  # chosen by grouped CV on corrected train.npz
B_SVM_C = 0.001


def get_ear(device: int) -> StreamAnalyzer:
    """Gets a stream analyzer object to capture the FFT of inputted audio waves.
    Investigate configurations here for different preprocessing options.

    Args:
        device (int): device index for input audio device to use.

    Returns:
        StreamAnalyzer: Class for capture and FFT processing of audio signals.
    """
    # Frozen UM2 profile: preserve the established 48 kHz / 50 ms FFT pipeline.
    # Input 2 is the second column of interleaved stereo int16 samples.
    # Fail explicitly rather than silently switching backend, channel or scale.
    return StreamAnalyzer(device=device, rate=48000, channels=2, input_channel=1,
                          allow_fallback=False, n_frequency_bins=512, FFT_window_size_ms=50)


def make_dummy_spectrum(
    n_bins: int = 512, peaks: list[int] = [50, 150, 300], rate: int = 1000
) -> tuple[list[float], list[float]]:
    """Generates a dummy FFT spectrum.

    Args:
        n_bins (int, optional): Number of frequency bins to generate. Defaults to 512.
        peaks (list[int], optional): Specific bin locations for a peak. Defaults to [50, 150, 300].
        rate (int, optional): Rate of sampling for bins. Defaults to 1000.

    Returns:
        tuple[list[float],list[float]]: _description_
    """
    freqs = np.linspace(0, rate / 2, n_bins)
    amps = np.zeros_like(freqs)
    for p in peaks:
        amps += np.exp(-0.5 * ((freqs - p) / 5) ** 2) * 5
    amps += 0.2 * np.random.rand(n_bins)
    return freqs, amps


def get_audio_features(ear: StreamAnalyzer) -> tuple[list[float], list[float]]:
    """Function called every frame which retrieves the audio features generated
    from a given StreamAnalyzer class. Intended for students to make preprocessing
    changes. The visualizer plots the full FFT as frequency in Hz on the x axis
    and FFT amplitude on the y axis.

    Args:
        ear (StreamAnalyzer): Class for capture and FFT processing of audio signals

    Returns:
        tuple[list[float], list[float]]: List of frequency bin values and corresponding amplitudes
    """
    if ear is None:
        return make_dummy_spectrum()
    else:
        freqs, amps, _frequency_bin_centres, _frequency_bin_energies = ear.get_audio_features()
        return freqs, amps


class LogSpectrum(BaseEstimator, TransformerMixin):
    """B's feature preprocessing, stored INSIDE the model Pipeline so training and
    inference always match: keep bins up to max_hz, then log1p.

    Input is always the raw 1200 FFT amplitudes; recorded data is never changed.
    shape_norm=True (experimental, off by default) subtracts each frame's mean log
    amplitude and appends that mean as one explicit level feature.
    """

    def __init__(self, max_hz=B_MAX_HZ, shape_norm=False):
        self.max_hz = max_hz
        self.shape_norm = shape_norm

    def fit(self, X, y=None):
        X = np.asarray(X)
        if X.shape[1] != N_FFT_FEATURES:
            raise ValueError(f"Expected {N_FFT_FEATURES} FFT features, got {X.shape[1]}")
        self.n_features_in_ = X.shape[1]
        return self

    def transform(self, X):
        X = np.asarray(X, dtype=np.float64)
        if X.shape[1] != N_FFT_FEATURES:
            raise ValueError(f"Expected {N_FFT_FEATURES} FFT features, got {X.shape[1]}")
        n_keep = N_FFT_FEATURES if self.max_hz is None else int(self.max_hz // FFT_BIN_HZ)
        L = np.log1p(X[:, :n_keep])
        if not self.shape_norm:
            return L
        level = L.mean(axis=1, keepdims=True)
        return np.hstack([L - level, level])


# model training
def preprocess_data(X: np.ndarray) -> np.ndarray:
    """Preprocessing before training and prediction. Data will not be visualized
    but will enable specific normalizations/preprocessing techniques for machine learning.

    Kept as identity on purpose: B's preprocessing (LogSpectrum + StandardScaler)
    lives inside the model Pipeline built by train_model(), so the model always
    receives the raw 1200 features and the GUI's 1200-feature load check holds.

    Args:
        X (np.ndarray): (N,D) Array of data with N total trials for D bins in each trial.
        Collected from either the collected data in training or individual frames from prediction

    Returns:
        np.ndarray: (N, D) the preprocessed array in the same shape.
    """
    return X


def train_model(
    X: np.ndarray,
    y: list[int] | np.ndarray,
    class_names: list[str],
    model_type: str = DEFAULT_MODEL_TYPE,
) -> tuple[Any, list[str]]:
    """Interface to train a specific model. Students should choose a model
    and then train it using the data from preprocess data sent in. Models can consist of interfaces
    from sklearn, pytorch, or other modules (from scratch or libraries).

    Args:
        X (np.ndarray): (N, D) Preprocessed data for N trials with D bin.
        y (list[int] | np.ndarray): (N,) Array of labels for each trial of X. Should be in integer form.
        class_names (list[str]): Decoded y values for a string name for each class.

    Returns:
        tuple[Any, list[str]]: The model and the list of class names for decoding later.
    """
    if model_type == MODEL_B_PIPELINE:
        model = Pipeline([
            ("feat", LogSpectrum(max_hz=B_MAX_HZ)),
            ("scale", StandardScaler()),
            ("svm", LinearSVC(C=B_SVM_C, class_weight="balanced", max_iter=20_000,
                              dual="auto", random_state=1)),
        ])
    elif model_type == MODEL_LINEAR_SVC:
        model = LinearSVC(
            C=1.0,
            tol=0.001,
            random_state=1,
            max_iter=10_000,
            dual="auto",
        )
    elif model_type == MODEL_POLY_SVC:
        # Port from Java Weka.
        model = SVC(
            C=1.0,  # the same complexity parameter
            kernel="poly",  # polynomial kernel
            degree=1,  # exponent E = 1.0
            coef0=0.0,  # kernel constant term C = 0
            tol=0.001,  # stopping tolerance L = 0.001
            shrinking=True,  # use shrinking heuristics (Weka's SMO always uses it)
            probability=False,  # disable probability estimates (-V -1 in Weka)
            break_ties=False,  # no direct Weka equivalent; default is fine
            random_state=1,  # seed for any randomized parts (-W 1)
            max_iter=-1,  # no limit on iterations (-V -1 / -N 0 implies full optimization)
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    model.fit(X, y)
    return model, class_names


def predict(model: Any, X: np.ndarray) -> np.ndarray:
    """Interface for using the model to predict some given data.

    Args:
        model (Any): Some model. Same model as one you trained in train_model
        X (np.ndarray): (N, D) N captures of D bins of data.

    Returns:
        np.ndarray: (N, ) Array of predicted labels for each trial. Array should have only integers.
    """

    # returns the index of some class name
    y_pred = model.predict(X)
    return y_pred


# B's decision layer: energy gate + prediction-label smoothing + bakeoff trial rules.
# This is separate from the starter's FEATURE smoothing, which is already inside
# every recorded/live FFT frame. Per frame:
#   gate inactive -> 'neutral' (model not consulted); gate active -> model label;
#   then Decoder changes its output only after K consecutive agreeing frames.
NEUTRAL = "neutral"
TRIAL_TYPES = ("knock+", "knock-", "rub+", "rub-")


@dataclass
class GateConfig:
    """Frame is active if PCM RMS or peak exceeds its threshold.
    Units are 0..1 FS as stored in rms_fs/peak_fs (0.00119 == 0.119% FS)."""
    rms_fs: float
    peak_fs: float
    enabled: bool = True

    def is_active(self, rms, peak):
        rms, peak = np.asarray(rms), np.asarray(peak)
        if not self.enabled:
            return np.ones(rms.shape, dtype=bool)
        return (rms > self.rms_fs) | (peak > self.peak_fs)


def calibrate_gate(quiet_rms, quiet_peak, scale=1.0, percentile=95.0) -> GateConfig:
    """Thresholds = scale x quiet percentile. scale <= 0 disables the gate."""
    if scale <= 0:
        return GateConfig(0.0, 0.0, enabled=False)
    if len(quiet_rms) == 0:
        raise ValueError("Gate calibration needs quiet frames")
    return GateConfig(float(scale * np.percentile(quiet_rms, percentile)),
                      float(scale * np.percentile(quiet_peak, percentile)))


@dataclass
class StabilityConfig:
    """k_frames[label]: consecutive raw frames needed to emit that label (~21 frames/s).
    release_frames: consecutive neutral frames needed to return to neutral."""
    k_frames: dict = field(default_factory=lambda: {"knock": 2, "rub": 4})
    release_frames: int = 3
    default_k: int = 3

    def need(self, label):
        if label == NEUTRAL:
            return self.release_frames
        return self.k_frames.get(label, self.default_k)


class Decoder:
    """Causal label smoother: output changes to L once L was the raw label K[L] frames in a row.
    Call reset() at the start of every trial."""

    def __init__(self, config: StabilityConfig):
        self.config = config
        self.reset()

    def reset(self):
        self.current = NEUTRAL
        self.run_label = None
        self.run_len = 0

    def step(self, raw_label):
        if raw_label == self.run_label:
            self.run_len += 1
        else:
            self.run_label, self.run_len = raw_label, 1
        if self.run_len >= self.config.need(raw_label):
            self.current = raw_label
        return self.current


def decode_sequence(raw_labels, config: StabilityConfig):
    decoder = Decoder(config)
    return [decoder.step(label) for label in raw_labels]


def trial_passes(trial_type, label_set):
    """Bakeoff rule. 'X+' passes iff set is {X} or {neutral, X}; 'X-' passes iff X not in set."""
    target, sign = trial_type[:-1], trial_type[-1]
    label_set = set(label_set)
    if sign == "+":
        return label_set in ({target}, {NEUTRAL, target})
    return target not in label_set


def _format_c_float(value: float) -> str:
    value = float(np.float32(value))
    if not np.isfinite(value):
        raise ValueError("Cannot export non-finite model value to C header")
    return f"{value:.9g}f"


def _format_c_float_rows(rows: np.ndarray, indent: str = "    ") -> str:
    formatted_rows = []
    for row in rows:
        values = [_format_c_float(value) for value in row]
        lines = []
        for i in range(0, len(values), 8):
            lines.append(f"{indent}    " + ", ".join(values[i : i + 8]))
        formatted_rows.append(f"{indent}{{\n" + ",\n".join(lines) + f"\n{indent}}}")
    return ",\n".join(formatted_rows)


def _class_names_for_export(model_classes: np.ndarray, classes: list[str]) -> list[str]:
    names = []
    for class_id in model_classes:
        try:
            class_index = int(class_id)
        except (TypeError, ValueError):
            names.append(str(class_id))
            continue

        if 0 <= class_index < len(classes):
            names.append(str(classes[class_index]))
        else:
            names.append(str(class_id))
    return names


def export_model_header(model: Any, classes: list[str], save_path: Path):
    """Export a trained linear scikit-learn model to an ESP32-friendly C++ header.

    The generated header includes float32 weights, biases, class labels, and
    prediction helpers. It supports LinearSVC-style models with coef_,
    intercept_, and classes_ attributes.
    """
    if not all(hasattr(model, attr) for attr in ("coef_", "intercept_", "classes_")):
        raise ValueError("Header export currently supports LinearSVC-style models only")

    weights = np.asarray(model.coef_, dtype=np.float32)
    biases = np.asarray(model.intercept_, dtype=np.float32)
    model_classes = np.asarray(model.classes_)

    if weights.ndim != 2:
        raise ValueError("Expected model.coef_ to be a 2D array")
    if biases.ndim != 1:
        raise ValueError("Expected model.intercept_ to be a 1D array")
    if len(biases) != len(weights):
        raise ValueError("Model weights and biases have incompatible shapes")

    is_binary_linear = len(model_classes) == 2 and len(weights) == 1
    is_multiclass_linear = len(model_classes) == len(weights)
    if not (is_binary_linear or is_multiclass_linear):
        raise ValueError("Unsupported linear model shape for header export")

    class_ids = [int(class_id) for class_id in model_classes]
    class_names = _class_names_for_export(model_classes, classes)

    num_score_rows, num_features = weights.shape
    class_names_literal = ", ".join(json.dumps(name) for name in class_names)
    class_ids_literal = ", ".join(str(class_id) for class_id in class_ids)
    biases_literal = ", ".join(_format_c_float(value) for value in biases)
    weights_literal = _format_c_float_rows(weights)

    if is_binary_linear:
        predict_index_body = """    float score = vibration_model_score_row(0, features);
    return score >= 0.0f ? 1 : 0;"""
    else:
        predict_index_body = """    int best_index = 0;
    float best_score = vibration_model_score_row(0, features);

    for (int class_index = 1; class_index < VIBRATION_MODEL_NUM_CLASSES; class_index++) {
        float score = vibration_model_score_row(class_index, features);
        if (score > best_score) {
            best_score = score;
            best_index = class_index;
        }
    }

    return best_index;"""

    header = f"""#pragma once

#ifndef PROGMEM
#define PROGMEM
#endif

// Generated from a scikit-learn linear model.
// The feature vector must match the Python FFT preprocessing exactly.
#define VIBRATION_MODEL_NUM_CLASSES {len(class_names)}
#define VIBRATION_MODEL_NUM_FEATURES {num_features}
#define VIBRATION_MODEL_NUM_SCORE_ROWS {num_score_rows}

static const int VIBRATION_MODEL_CLASS_IDS[VIBRATION_MODEL_NUM_CLASSES] PROGMEM = {{
    {class_ids_literal}
}};

static const char *const VIBRATION_MODEL_CLASS_NAMES[VIBRATION_MODEL_NUM_CLASSES] = {{
    {class_names_literal}
}};

static const float VIBRATION_MODEL_BIASES[VIBRATION_MODEL_NUM_SCORE_ROWS] PROGMEM = {{
    {biases_literal}
}};

static const float VIBRATION_MODEL_WEIGHTS[VIBRATION_MODEL_NUM_SCORE_ROWS][VIBRATION_MODEL_NUM_FEATURES] PROGMEM = {{
{weights_literal}
}};

static inline float vibration_model_score_row(
    int row,
    const float features[VIBRATION_MODEL_NUM_FEATURES]
) {{
    float score = VIBRATION_MODEL_BIASES[row];

    for (int feature_index = 0; feature_index < VIBRATION_MODEL_NUM_FEATURES; feature_index++) {{
        score += VIBRATION_MODEL_WEIGHTS[row][feature_index] * features[feature_index];
    }}

    return score;
}}

static inline int vibration_model_predict_index(
    const float features[VIBRATION_MODEL_NUM_FEATURES]
) {{
{predict_index_body}
}}

static inline int vibration_model_predict_id(
    const float features[VIBRATION_MODEL_NUM_FEATURES]
) {{
    return VIBRATION_MODEL_CLASS_IDS[vibration_model_predict_index(features)];
}}

static inline const char *vibration_model_predict_name(
    const float features[VIBRATION_MODEL_NUM_FEATURES]
) {{
    return VIBRATION_MODEL_CLASS_NAMES[vibration_model_predict_index(features)];
}}
"""

    with open(save_path, "w") as f:
        f.write(header)


def save_model(model: Any, classes: list[str], save_path: Path):
    """Interface to save your generated model.

    Args:
        model (Any): Model created from train_model
        classes (list[str]): List of class names that are used to decode model prediction integers.
        save_path (Path): File path to save the model. Can only end in .model.
    """

    payload = {
        "model": model,
        "classes": classes,
        "model_type": type(model).__name__,
    }

    with open(save_path, "wb") as f:
        pickle.dump(payload, f)


def load_model(file_path: Path) -> tuple[Any, list[str]]:
    """Interface to load your model.

    Args:
        file_path (Path): Path of the model file to load. Can only end in .model

    Returns:
        tuple[Any, list[str]]: Model loaded and the list of class names for decoding
    """

    with open(file_path, "rb") as f:
        payload = pickle.load(f)
    return payload["model"], payload["classes"]
