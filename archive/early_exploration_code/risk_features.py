"""Extract black-box risk features from API log-probability records."""
from __future__ import annotations

import math


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1 + exp_value)


def extract_risk_features(record: dict) -> dict:
    """Return auditable uncertainty features for one logged answer.

    The current prompts demand a concise answer, so the first generated token
    is the decision token. For longer answers, this remains a conservative
    proxy; the raw logprob object is retained in the run log for later audit.
    """
    content = (record.get("api_logprobs") or {}).get("content") or []
    parsed = record.get("parsed_option")
    features = {
        "format_risk": 1.0 if parsed is None else 0.0,
        "token_logprob": None,
        "margin": None,
        "probability_risk": None,
        "margin_risk": None,
        "risk": None,
        "risk_source": "missing_logprobs",
    }
    if not content:
        features["risk"] = features["format_risk"]
        return features

    first = content[0]
    selected_logprob = first.get("logprob")
    alternatives = [
        candidate.get("logprob")
        for candidate in first.get("top_logprobs") or []
        if candidate.get("token") != first.get("token") and candidate.get("logprob") is not None
    ]
    if selected_logprob is None or not alternatives:
        features["risk"] = features["format_risk"]
        return features

    margin = float(selected_logprob) - max(float(value) for value in alternatives)
    probability_risk = 1 - math.exp(max(float(selected_logprob), -30.0))
    margin_risk = 1 - _sigmoid(margin)
    # A format violation is always routed to verification. Otherwise use the
    # mean of token surprise and ambiguity; calibration learns the threshold.
    risk = max(features["format_risk"], (probability_risk + margin_risk) / 2)
    features.update({
        "token_logprob": float(selected_logprob),
        "margin": margin,
        "probability_risk": probability_risk,
        "margin_risk": margin_risk,
        "risk": risk,
        "risk_source": "first_token_logprobs",
    })
    return features
