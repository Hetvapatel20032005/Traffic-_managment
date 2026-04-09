from fastapi import FastAPI
import uvicorn
import numpy as np
import os
import requests
import traceback
import joblib
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow import keras
import psutil  # New: for benchmarking
import time
import statistics  # For risk metrics

# ────────────────────────────────────────────────
# CONFIG - ABSOLUTE PATHS
# ────────────────────────────────────────────────
app = FastAPI(title="BTC NextGen Forecast API")

# Change if your project path is different
BASE_DIR = r"C:\Users\djroc\Desktop\btc-nextgen-final"
MODEL_PATH  = os.path.join(BASE_DIR, "models", "transformer.h5")
SCALER_PATH = os.path.join(BASE_DIR, "models", "scaler.pkl")

SEQUENCE_LENGTH = 60
DEFAULT_THRESHOLD = 10.0

# Global variables
model = None
scaler = None

# ────────────────────────────────────────────────
# CUSTOM LAYERS (copied from model.py for self-contained loading)
# ────────────────────────────────────────────────
class PositionalEncoding(layers.Layer):
    def __init__(self, seq_len, embed_dim, **kwargs):
        super().__init__(**kwargs)
        self.seq_len = seq_len
        self.embed_dim = embed_dim

    def call(self, x):
        position = tf.range(self.seq_len, dtype=tf.float32)[:, tf.newaxis]
        i = tf.range(self.embed_dim, dtype=tf.float32)[tf.newaxis, :]

        angle_rates = 1 / tf.pow(
            tf.cast(10000.0, tf.float32),
            (2 * (i // 2)) / tf.cast(self.embed_dim, tf.float32),
        )

        angle_rads = position * angle_rates

        sines = tf.sin(angle_rads[:, 0::2])
        cosines = tf.cos(angle_rads[:, 1::2])

        pos_encoding = tf.concat([sines, cosines], axis=-1)
        pos_encoding = pos_encoding[tf.newaxis, ...]

        return x + pos_encoding

    def get_config(self):
        config = super().get_config()
        config.update({"seq_len": self.seq_len, "embed_dim": self.embed_dim})
        return config


class TransformerBlock(layers.Layer):
    def __init__(self, embed_dim, num_heads, ff_dim, rate=0.1, **kwargs):
        super().__init__(**kwargs)
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.ff_dim = ff_dim
        self.rate = rate

        self.att = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)
        self.ffn = keras.Sequential([
            layers.Dense(ff_dim, activation="relu"),
            layers.Dense(embed_dim),
        ])
        self.layernorm1 = layers.LayerNormalization(epsilon=1e-6)
        self.layernorm2 = layers.LayerNormalization(epsilon=1e-6)
        self.dropout1 = layers.Dropout(rate)
        self.dropout2 = layers.Dropout(rate)

    def call(self, inputs, training=False):
        attn_output = self.att(inputs, inputs)
        attn_output = self.dropout1(attn_output, training=training)
        out1 = self.layernorm1(inputs + attn_output)
        ffn_output = self.ffn(out1)
        ffn_output = self.dropout2(ffn_output, training=training)
        return self.layernorm2(out1 + ffn_output)

    def get_config(self):
        config = super().get_config()
        config.update({
            "embed_dim": self.embed_dim,
            "num_heads": self.num_heads,
            "ff_dim": self.ff_dim,
            "rate": self.rate,
        })
        return config


# ────────────────────────────────────────────────
# LOAD RESOURCES
# ────────────────────────────────────────────────
def load_resources():
    global model, scaler

    print("╔════════════════════════════════════════════╗")
    print("║          MODEL & SCALER LOADING            ║")
    print("╚════════════════════════════════════════════╝")
    print(f"Model path:  {MODEL_PATH} (exists: {os.path.exists(MODEL_PATH)})")
    print(f"Scaler path: {SCALER_PATH} (exists: {os.path.exists(SCALER_PATH)})")

    try:
        if os.path.exists(MODEL_PATH):
            print("→ Loading model...")
            model = keras.models.load_model(
                MODEL_PATH,
                custom_objects={
                    "PositionalEncoding": PositionalEncoding,
                    "TransformerBlock": TransformerBlock,
                },
                compile=False
            )
            print("→ MODEL LOADED SUCCESSFULLY")
        else:
            print("→ MODEL FILE NOT FOUND")

        if os.path.exists(SCALER_PATH):
            print("→ Loading scaler...")
            scaler = joblib.load(SCALER_PATH)
            print("→ SCALER LOADED SUCCESSFULLY")
        else:
            print("→ SCALER FILE NOT FOUND")

    except Exception as e:
        print("→ LOADING FAILED:")
        traceback.print_exc()

    print(f"Status → Model: {'LOADED' if model else 'FAILED'} | Scaler: {'LOADED' if scaler else 'FAILED'}")
    print("╚════════════════════════════════════════════╝")


load_resources()


# ────────────────────────────────────────────────
# DATA FETCHING
# ────────────────────────────────────────────────
def fetch_data(days: int = 90) -> np.ndarray:
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}&interval=daily"
    resp = requests.get(url, timeout=12)
    resp.raise_for_status()
    data = resp.json()
    prices = [p[1] for p in data.get("prices", [])]
    return np.array(prices, dtype=np.float32)


# ────────────────────────────────────────────────
# BENCHMARKING WITH PSUTIL
# ────────────────────────────────────────────────
def run_benchmark(num_runs=10):
    """Run multiple predictions and measure performance"""
    if model is None or scaler is None:
        return {"error": "Model/scaler not loaded"}

    times = []
    cpu_usages = []
    memory_usages = []
    process = psutil.Process()

    for i in range(num_runs):
        start_time = time.time()
        start_cpu = psutil.cpu_percent(interval=None)
        start_mem = process.memory_info().rss / 1024 / 1024  # MB

        # Run prediction
        raw_data = fetch_data(SEQUENCE_LENGTH + 30)
        input_data = raw_data[-SEQUENCE_LENGTH:].reshape(-1, 1)
        scaled_input = scaler.transform(input_data)
        scaled_input = scaled_input.reshape(1, SEQUENCE_LENGTH, 1)
        _ = model.predict(scaled_input, verbose=0)

        end_time = time.time()
        end_cpu = psutil.cpu_percent(interval=None)
        end_mem = process.memory_info().rss / 1024 / 1024  # MB

        times.append(end_time - start_time)
        cpu_usages.append(end_cpu - start_cpu)
        memory_usages.append(end_mem - start_mem)

    avg_time = np.mean(times) * 1000  # ms
    avg_cpu = np.mean(cpu_usages)
    avg_mem = np.mean(memory_usages)

    return {
        "runs": num_runs,
        "avg_inference_time_ms": avg_time,
        "avg_cpu_usage_%": avg_cpu,
        "avg_memory_delta_mb": avg_mem,
        "system_cpu_%": psutil.cpu_percent(),
        "system_memory_%": psutil.virtual_memory().percent,
        "recommendation": "Efficient" if avg_time < 100 else "Optimize model"
    }


# ────────────────────────────────────────────────
# RISK METRICS
# ────────────────────────────────────────────────
def compute_risk_metrics(prices: np.ndarray, risk_free_rate=0.02):
    """Compute volatility and Sharpe ratio"""
    returns = np.diff(prices) / prices[:-1]
    volatility = np.std(returns) * np.sqrt(252)  # Annualized
    sharpe = (np.mean(returns) - risk_free_rate/252) / np.std(returns) * np.sqrt(252)
    return {"volatility": volatility, "sharpe_ratio": sharpe}


# ────────────────────────────────────────────────
# ENDPOINTS
# ────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "running",
        "model_loaded": model is not None,
        "scaler_loaded": scaler is not None
    }


@app.get("/predict")
def predict(threshold: float = DEFAULT_THRESHOLD, horizon: int = 1):
    """Predict for 1/7/30 day horizons"""
    if model is None or scaler is None:
        return {"error": "Model/scaler not loaded"}

    try:
        raw_data = fetch_data(SEQUENCE_LENGTH + horizon * 7)  # Extra data for longer horizons
        if len(raw_data) < SEQUENCE_LENGTH:
            raise ValueError("Insufficient data")

        predictions = {}
        for h in [1, 7, 30][:horizon if horizon > 3 else horizon]:
            # Rolling prediction for horizon
            input_data = raw_data[-(SEQUENCE_LENGTH + h):-(h)].reshape(-1, 1)
            scaled_input = scaler.transform(input_data)
            scaled_input = scaled_input.reshape(1, SEQUENCE_LENGTH, 1)
            pred_scaled = model.predict(scaled_input, verbose=0)
            pred_price = scaler.inverse_transform(pred_scaled)[0][0]
            predictions[f"{h}_day"] = float(pred_price)

        current_price = float(raw_data[-1])
        difference = predictions["1_day"] - current_price
        signal = "BUY" if difference > threshold else "SELL" if difference < -threshold else "HOLD"

        # Risk metrics
        risk = compute_risk_metrics(raw_data[-30:])  # Last 30 days

        return {
            "current_price": current_price,
            "predictions": predictions,
            "difference_1d": float(difference),
            "signal": signal,
            "threshold_used": threshold,
            "risk_metrics": risk
        }

    except Exception as e:
        return {"error": str(e), "details": traceback.format_exc()[:800]}


@app.get("/backtest")
def backtest(days: int = 30):
    """Simulate trading on historical data"""
    if model is None or scaler is None:
        return {"error": "Model/scaler not loaded"}

    try:
        raw_data = fetch_data(days + SEQUENCE_LENGTH)
        portfolio = 10000  # Starting capital
        signals = []
        returns = []

        for i in range(SEQUENCE_LENGTH, len(raw_data) - 1):
            seq = raw_data[i-SEQUENCE_LENGTH:i].reshape(-1, 1)
            scaled_seq = scaler.transform(seq)
            scaled_seq = scaled_seq.reshape(1, SEQUENCE_LENGTH, 1)
            pred = model.predict(scaled_seq, verbose=0)
            pred_price = scaler.inverse_transform(pred)[0][0]
            actual_next = raw_data[i]

            diff = pred_price - raw_data[i-1]
            signal = "BUY" if diff > DEFAULT_THRESHOLD else "SELL" if diff < -DEFAULT_THRESHOLD else "HOLD"

            # Simple simulation: BUY/SELL 10% of portfolio
            if signal == "BUY":
                portfolio *= (actual_next / raw_data[i-1])
            elif signal == "SELL":
                portfolio *= (raw_data[i-1] / actual_next)

            signals.append(signal)
            returns.append((actual_next - raw_data[i-1]) / raw_data[i-1])

        total_return = (portfolio - 10000) / 10000 * 100
        win_rate = sum(1 for r in returns if r > 0) / len(returns) * 100

        return {
            "days": days,
            "total_return_%": total_return,
            "win_rate_%": win_rate,
            "signals": signals[-10:],  # Last 10 signals
            "recommendation": "Profitable" if total_return > 0 else "Needs tuning"
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/benchmark")
def benchmark(num_runs: int = 10):
    """Generate performance report"""
    return run_benchmark(num_runs)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)