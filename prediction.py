import numpy as np
from sklearn.linear_model import LinearRegression


def predict_future_congestion(history, graph, steps_ahead=5):
    """
    Predict future congestion for all nodes based on historical counts.
    Returns:
        predictions: dict mapping node_id -> list of predictions for the next N steps.
        risks: dict mapping node_id -> 'Risk message'
        trends: dict mapping node_id -> 'up' | 'down' | 'stable'
    """
    predictions = {}
    risks = {}
    trends = {}

    if len(history) < 3:
        current = history[-1] if history else {n: 0 for n in graph.nodes()}
        for n in graph.nodes():
            predictions[n] = [current.get(n, 0)] * steps_ahead
            risks[n] = "Pending Data"
            trends[n] = "stable"
        return predictions, risks, trends

    X = np.arange(len(history)).reshape(-1, 1)
    future_X = np.arange(len(history), len(history) + steps_ahead).reshape(-1, 1)

    for n in graph.nodes():
        y = np.array([step_counts.get(n, 0) for step_counts in history])

        # Use Simple Linear Regression
        model = LinearRegression()
        model.fit(X, y)
        preds = model.predict(future_X)
        preds = np.maximum(0, preds)

        predictions[n] = [int(p) for p in preds]

        capacity = graph.nodes[n]['capacity']
        max_pred = max(preds)
        ratio = max_pred / capacity if capacity > 0 else 1.0

        # Predict future risk
        if ratio > 0.9:
            risks[n] = "Critical Overcrowding Risk"
        elif ratio > 0.7:
            risks[n] = "High Density Warning"
        else:
            risks[n] = "Normal"

        # Trend direction, based on recent slope vs. current level
        last_actual = y[-1]
        projected = preds[-1]
        if last_actual == 0 and projected == 0:
            trends[n] = "stable"
        elif projected > last_actual * 1.05:
            trends[n] = "up"
        elif projected < last_actual * 0.95:
            trends[n] = "down"
        else:
            trends[n] = "stable"

    return predictions, risks, trends
