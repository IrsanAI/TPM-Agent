from __future__ import annotations

import importlib.util
import math
from collections import Counter

import numpy as np


class EntropySignalEngine:
    """Windowed Shannon entropy + coarse compression helpers."""

    def __init__(self, bins: int = 20):
        self.bins = max(4, bins)

    def shannon_entropy(self, seq: list[float]) -> float:
        if len(seq) < 2:
            return 0.0
        hist, _ = np.histogram(np.asarray(seq, dtype=float), bins=self.bins)
        probs = hist / max(1, hist.sum())
        probs = probs[probs > 0]
        return float(-(probs * np.log2(probs)).sum())

    def sliding_entropy(self, seq: list[float], window: int = 1000, stride: int = 50) -> list[float]:
        if len(seq) < 2:
            return []
        if len(seq) <= window:
            return [self.shannon_entropy(seq)]
        out: list[float] = []
        for i in range(0, len(seq) - window + 1, max(1, stride)):
            out.append(self.shannon_entropy(seq[i : i + window]))
        return out

    def bottleneck_compress(self, seq: list[float], out_points: int = 20) -> list[float]:
        if not seq:
            return []
        if len(seq) <= out_points:
            return [float(v) for v in seq]
        buckets = np.array_split(np.asarray(seq, dtype=float), out_points)
        return [float(np.mean(b)) for b in buckets if len(b)]

    def black_hole_filter(
        self,
        seq: list[float],
        window: int = 40,
        stride: int = 10,
        entropy_quantile: float = 0.70,
        out_points: int = 20,
    ) -> dict[str, list[float] | float]:
        """Filter noisy regions, keep high-entropy signal windows, then compress.

        Pipeline: sliding entropy -> threshold gate -> concatenate selected windows -> bottleneck compress.
        """
        if not seq:
            return {"filtered": [], "compressed": [], "threshold": 0.0}
        series = [float(v) for v in seq]
        if len(series) <= window:
            compressed = self.bottleneck_compress(series, out_points=out_points)
            return {"filtered": series, "compressed": compressed, "threshold": 0.0}

        entropies: list[float] = []
        windows: list[list[float]] = []
        step = max(1, stride)
        for i in range(0, len(series) - window + 1, step):
            chunk = series[i : i + window]
            windows.append(chunk)
            entropies.append(self.shannon_entropy(chunk))

        threshold = float(np.quantile(np.asarray(entropies, dtype=float), min(1.0, max(0.0, entropy_quantile))))
        selected: list[float] = []
        for chunk, h in zip(windows, entropies):
            if h >= threshold:
                selected.extend(chunk)
        if not selected:
            selected = series[-window:]
        compressed = self.bottleneck_compress(selected, out_points=out_points)
        return {"filtered": selected, "compressed": compressed, "threshold": threshold}


class TransferEntropyEngine:
    """Transfer entropy estimator plus histogram-based mutual information."""

    def __init__(self, bins: int = 12, lag: int = 1):
        self.bins = bins
        self.lag = lag
        self._has_scipy = importlib.util.find_spec("scipy") is not None

    def _digitize(self, seq: list[float]) -> list[int]:
        if not seq:
            return []
        lo, hi = min(seq), max(seq)
        if hi == lo:
            return [0] * len(seq)
        step = (hi - lo) / self.bins
        return [min(self.bins - 1, max(0, int((v - lo) / step))) for v in seq]

    def mutual_information_hist(self, x: list[float], y: list[float]) -> float:
        n = min(len(x), len(y))
        if n < 4:
            return 0.0
        xd = self._digitize(x[:n])
        yd = self._digitize(y[:n])
        px = Counter(xd)
        py = Counter(yd)
        pxy = Counter(zip(xd, yd))
        mi = 0.0
        for (xi, yi), cxy in pxy.items():
            pxy_v = cxy / n
            denom = (px[xi] / n) * (py[yi] / n)
            if denom <= 0:
                continue
            mi += pxy_v * math.log2(pxy_v / denom)
        return max(0.0, float(mi))

    def calculate_transfer_entropy(self, x: list[float], y: list[float], normalized: bool = False) -> float:
        """Estimate transfer entropy TE(X→Y) = Σ p(y_t+1,y_t,x_t) log2( p(y_t+1|y_t,x_t)/p(y_t+1|y_t) )."""
        n = min(len(x), len(y))
        if n < self.lag + 3:
            return 0.0
        xd = self._digitize(x[:n])
        yd = self._digitize(y[:n])

        c_xyz: dict[tuple[int, int, int], int] = {}
        c_yz: dict[tuple[int, int], int] = {}
        c_xy: dict[tuple[int, int], int] = {}
        c_y: dict[int, int] = {}

        for t in range(self.lag, n - 1):
            yt1, yt, xt = yd[t + 1], yd[t], xd[t]
            c_xyz[(yt1, yt, xt)] = c_xyz.get((yt1, yt, xt), 0) + 1
            c_yz[(yt, xt)] = c_yz.get((yt, xt), 0) + 1
            c_xy[(yt1, yt)] = c_xy.get((yt1, yt), 0) + 1
            c_y[yt] = c_y.get(yt, 0) + 1

        total = n - self.lag - 1
        te = 0.0
        for (yt1, yt, xt), count in c_xyz.items():
            p_xyz = count / total
            p_yt1_yt_xt = count / c_yz[(yt, xt)]
            p_yt1_yt = c_xy[(yt1, yt)] / c_y[yt]
            ratio = p_yt1_yt_xt / max(p_yt1_yt, 1e-12)
            te += p_xyz * math.log(ratio + 1e-12, 2)
        te = max(0.0, te)
        if normalized:
            h_y = self.mutual_information_hist(y[:-1], y[1:]) if len(y) > 1 else 0.0
            if h_y > 1e-12:
                return min(1.0, te / h_y)
        return te

    def score(self, x: list[float], y: list[float]) -> float:
        return self.calculate_transfer_entropy(x, y)

    def correlation_graph(self, series_by_agent: dict[str, list[float]]) -> dict[str, float]:
        names = list(series_by_agent.keys())
        graph: dict[str, float] = {}
        for i, src in enumerate(names):
            for dst in names[i + 1 :]:
                score = self.score(series_by_agent[src], series_by_agent[dst])
                graph[f"{src}->{dst}"] = score
        return graph
