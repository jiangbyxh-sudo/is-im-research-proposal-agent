"""Advisory discovery saturation metrics; never a P1 acceptance threshold."""
from __future__ import annotations

from dataclasses import dataclass


SATURATION_VERSION = "retrieval-saturation-1.0.0"


@dataclass(frozen=True)
class SaturationConfig:
    version: str = SATURATION_VERSION
    window_rounds: int = 2
    max_new_direct_per_round: int = 1
    min_repeat_ratio: float = 0.80


def _ids(round_record: dict, key: str) -> list[str]:
    values = round_record.get(key) or []
    return list(dict.fromkeys(str(value) for value in values if str(value)))


def evaluate_retrieval_saturation(rounds: list[dict], config: SaturationConfig | None = None) -> dict:
    config = config or SaturationConfig()
    seen_candidates: set[str] = set()
    seen_direct: set[str] = set()
    metrics = []
    for index, round_record in enumerate(rounds, start=1):
        candidates = set(_ids(round_record, "candidate_ids"))
        direct = set(_ids(round_record, "direct_ids"))
        new_candidates = candidates - seen_candidates
        new_direct = direct - seen_direct
        repeat_ratio = 0.0 if not candidates else len(candidates & seen_candidates) / len(candidates)
        metrics.append({
            "round": index,
            "source": str(round_record.get("source") or f"round_{index}"),
            "candidate_count": len(candidates),
            "new_candidate_count": len(new_candidates),
            "direct_count": len(direct),
            "new_direct_count": len(new_direct),
            "repeat_ratio": round(repeat_ratio, 6),
        })
        seen_candidates.update(candidates)
        seen_direct.update(direct)

    window = metrics[-max(1, config.window_rounds):]
    enough_rounds = len(metrics) >= max(2, config.window_rounds)
    low_direct_yield = bool(window) and all(item["new_direct_count"] <= config.max_new_direct_per_round for item in window)
    high_repetition = bool(window) and all(item["repeat_ratio"] >= config.min_repeat_ratio for item in window)
    if not enough_rounds:
        status = "SATURATION_INSUFFICIENT_ROUNDS"
    elif low_direct_yield and high_repetition:
        status = "SATURATION_CANDIDATE"
    else:
        status = "CONTINUE_DISCOVERY"
    return {
        "status": status,
        "version": config.version,
        "rounds": metrics,
        "unique_candidate_count": len(seen_candidates),
        "unique_direct_count": len(seen_direct),
        "window_rounds": config.window_rounds,
        "low_direct_yield": low_direct_yield,
        "high_repetition": high_repetition,
        "advisory_only": True,
        "changes_p1_thresholds": False,
    }
