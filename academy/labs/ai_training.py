"""微型线性回归：训练、验证选优、未见测试集及保存重载。"""
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path


def dataset(start, stop):
    return [(i / 10, 2 * (i / 10) + 1 + 0.04 * math.sin(i)) for i in range(start, stop)]


def fit_normalizer(rows):
    mean = sum(x for x, _ in rows) / len(rows)
    scale = math.sqrt(sum((x - mean) ** 2 for x, _ in rows) / len(rows))
    return mean, scale or 1.0


def predict(model, x):
    return model["weight"] * ((x - model["mean"]) / model["scale"]) + model["bias"]


def mse(model, rows):
    return sum((predict(model, x) - y) ** 2 for x, y in rows) / len(rows)


def train(train_rows, validation_rows, steps=300, learning_rate=0.05):
    if not train_rows or not validation_rows or steps < 1 or learning_rate <= 0:
        raise ValueError("nonempty splits, positive steps and rate required")
    mean, scale = fit_normalizer(train_rows)
    model = {"schema_version": 1, "mean": mean, "scale": scale, "weight": 0.0, "bias": 0.0}
    best = dict(model)
    best_loss = mse(model, validation_rows)
    best_step = 0
    history = []
    for step in range(1, steps + 1):
        errors = [(predict(model, x) - y, (x - mean) / scale) for x, y in train_rows]
        model["weight"] -= learning_rate * 2 * sum(error * x for error, x in errors) / len(errors)
        model["bias"] -= learning_rate * 2 * sum(error for error, _ in errors) / len(errors)
        validation_loss = mse(model, validation_rows)
        history.append({"step": step, "train_mse": mse(model, train_rows), "validation_mse": validation_loss})
        if validation_loss < best_loss:
            best, best_loss, best_step = dict(model), validation_loss, step
    best["selected_step"] = best_step
    return best, history


def main():
    training, validation, test = dataset(-20, 21), dataset(21, 31), dataset(31, 41)
    model, history = train(training, validation)
    with tempfile.TemporaryDirectory(prefix="fde-ai-training-") as directory:
        path = Path(directory) / "model.json"
        path.write_text(json.dumps(model), encoding="utf-8")
        restored = json.loads(path.read_text(encoding="utf-8"))
        delta = max(abs(predict(model, x) - predict(restored, x)) for x, _ in test)
        child = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                "--predict-model", str(path)], capture_output=True,
                               text=True, check=True, timeout=15)
        child_predictions = json.loads(child.stdout)
        child_delta = max(abs(predict(model, x) - value)
                          for (x, _), value in zip(test, child_predictions))
    print(json.dumps({"scope": "synthetic_cpu_linear_regression_not_llm", "model": model,
                      "first_train_mse": history[0]["train_mse"], "last_train_mse": history[-1]["train_mse"],
                      "test_mse": mse(restored, test), "reload_max_prediction_difference": delta,
                      "new_process_prediction_difference": child_delta}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--predict-model":
        loaded = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        print(json.dumps([predict(loaded, x) for x, _ in dataset(31, 41)]))
    else:
        main()
