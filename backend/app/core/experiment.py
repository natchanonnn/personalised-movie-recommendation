import hashlib

from app.core.config import ExperimentVariant


def bucket_value(user_id: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()
    return int(digest[:16], 16) / 0xFFFFFFFFFFFFFFFF


def assign_variant(user_id: str, variants: list[ExperimentVariant], salt: str) -> str:
    if not variants:
        raise ValueError("No variants configured")

    ordered = sorted(variants, key=lambda v: v.name)
    total_weight = sum(v.weight for v in ordered)
    if total_weight <= 0:
        raise ValueError("Variant weights must sum to > 0")

    point = bucket_value(user_id, salt) * total_weight
    cumulative = 0.0
    for variant in ordered:
        cumulative += variant.weight
        if point < cumulative:
            return variant.name
    return ordered[-1].name