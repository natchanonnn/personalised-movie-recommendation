"""Per-recommendation explanations, transcribed from CF.ipynb / CBF.ipynb /
HBF.ipynb's own explain_recommendation()/format_explanation() cells.

All three functions skip history items whose title matches the recommended
item's title before picking a citation. The catalog has ~1,300 titles that
map to more than one item id (remakes/re-releases with genuinely different
genres/embeddings, not accidental duplicates); without this skip, citing the
history item reads as a confusing self-citation ("Because you watched X, ...
you'll like X") even though the two are distinct catalog entries.

explain_hybrid is new: hybrid_content is the only variant whose embedder
keeps a real item-id embedding (pure_content zeroes it out), so it's also
the only one that can honestly cite a collaborative-filtering reason
alongside the content-based ones.

All lookups operate on ENCODED item ids, matching how item_embeddings and
item_metadata are indexed — call this before decoding predictions back to
raw ids.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F


def cosine_sim(a, b) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


def explain_collaborative(
    user_history_item_ids: list[int],
    user_ratings: list[float],
    recommended_item_id: int,
    item_embeddings: torch.Tensor,
    item_titles: dict[int, str],
    recommended_title: str,
    top_n: int = 3,
) -> str | None:
    if not user_history_item_ids:
        return None

    rec_vec = item_embeddings[recommended_item_id]
    hist_vecs = item_embeddings[user_history_item_ids]
    sims = F.cosine_similarity(rec_vec.unsqueeze(0), hist_vecs)
    top_idx = sims.topk(min(top_n, len(user_history_item_ids))).indices

    def bucket(sim: float) -> str | None:
        if sim > 0.8:
            return "very similar to"
        if sim > 0.6:
            return "similar to"
        if sim > 0.4:
            return "related to"
        return None

    lines = []
    for i in top_idx:
        sim = sims[i].item()
        if bucket(sim) is None:
            continue
        hist_item_id = user_history_item_ids[i]
        title = item_titles.get(hist_item_id, "an unknown title")
        if title == recommended_title:
            # Same title under a different item id (e.g. a remake/re-release in the
            # catalog) -- citing it reads as a confusing self-citation, so skip it.
            continue
        lines.append(f'{title} (your rating: {user_ratings[i]})')

    if not lines:
        return f'"{recommended_title}" is broadly similar to your recent viewing.'
    return f'Because you enjoyed {", ".join(lines)}, we think you\'ll like "{recommended_title}".'


def explain_content(
    user_history_item_ids: list[int],
    recommended_item_id: int,
    item_metadata,
    recommended_title: str,
    desc_weight: float = 0.5,
    genre_weight: float = 0.2,
    keyword_weight: float = 0.3,
) -> str | None:
    if not user_history_item_ids:
        return None

    candidate = item_metadata.loc[recommended_item_id]
    candidate_desc = candidate["embeddings"]
    candidate_kw = candidate["keyword_embedding"]
    candidate_genres = set(candidate["genre_names"])
    candidate_title = candidate["title"]

    scored = []
    for hist_id in user_history_item_ids[-20:]:
        hist = item_metadata.loc[hist_id]
        if hist["title"] == candidate_title:
            # Same title under a different item id (e.g. a remake/re-release in the
            # catalog) -- citing it reads as a confusing self-citation, so skip it.
            continue

        desc_sim = cosine_sim(candidate_desc, hist["embeddings"])
        keyword_sim = cosine_sim(candidate_kw, hist["keyword_embedding"])
        hist_genres = set(hist["genre_names"])
        overlap = candidate_genres & hist_genres
        genre_sim = len(overlap) / max(len(candidate_genres | hist_genres), 1)
        combined = desc_weight * desc_sim + genre_weight * genre_sim + keyword_weight * keyword_sim
        scored.append(
            {
                "title": hist["title"],
                "desc_sim": desc_sim,
                "keyword_sim": keyword_sim,
                "genre_overlap": overlap,
                "combined": combined,
            }
        )

    if not scored:
        # Every history item shared the candidate's title -- nothing left to cite.
        return None

    best = max(scored, key=lambda x: x["combined"])

    reasons = []
    if best["genre_overlap"]:
        reasons.append(f"shares the {', '.join(sorted(best['genre_overlap']))} genre(s)")
    if best["desc_sim"] > 0.6:
        reasons.append("has a similar theme/plot")
    if best["keyword_sim"] > 0.5:
        reasons.append("touches on similar story elements")
    if not reasons:
        reasons.append("is broadly similar in style")

    return (
        f'Because you watched "{best["title"]}", which {" and ".join(reasons)}, '
        f'we think you\'ll like "{recommended_title}".'
    )


def explain_hybrid(
    user_history_item_ids: list[int],
    recommended_item_id: int,
    item_metadata,
    item_collab_embeddings,
    recommended_title: str,
    desc_weight: float = 0.35,
    genre_weight: float = 0.15,
    keyword_weight: float = 0.2,
    collab_weight: float = 0.3,
) -> str | None:
    """hybrid_content variant only. Combines the same content signals as
    explain_content with a collaborative signal (similarity of the model's
    own learned item-id embeddings -- item_collab_embeddings, indexed by
    encoded item id, as returned by HybridContentAwareEmbedder.get_item_weights()).
    That embedding table is the collaborative-filtering component of the
    hybrid embedder: it's trained end-to-end from interaction sequences,
    separately from the content projections added in forward(). Mirrors
    HBF.ipynb's updated explain_recommendation()/format_explanation() cells.
    """
    if not user_history_item_ids:
        return None

    candidate = item_metadata.loc[recommended_item_id]
    candidate_desc = candidate["embeddings"]
    candidate_kw = candidate["keyword_embedding"]
    candidate_genres = set(candidate["genre_names"])
    candidate_title = candidate["title"]
    candidate_collab = item_collab_embeddings[recommended_item_id]

    scored = []
    for hist_id in user_history_item_ids[-20:]:
        hist = item_metadata.loc[hist_id]
        if hist["title"] == candidate_title:
            continue  # same-titled catalog entry (e.g. a remake) -- would read as a self-citation

        desc_sim = cosine_sim(candidate_desc, hist["embeddings"])
        keyword_sim = cosine_sim(candidate_kw, hist["keyword_embedding"])
        hist_genres = set(hist["genre_names"])
        overlap = candidate_genres & hist_genres
        genre_sim = len(overlap) / max(len(candidate_genres | hist_genres), 1)
        collab_sim = cosine_sim(candidate_collab, item_collab_embeddings[hist_id])

        combined = (
            desc_weight * desc_sim
            + genre_weight * genre_sim
            + keyword_weight * keyword_sim
            + collab_weight * collab_sim
        )
        scored.append(
            {
                "title": hist["title"],
                "desc_sim": desc_sim,
                "keyword_sim": keyword_sim,
                "genre_overlap": overlap,
                "collab_sim": collab_sim,
                "combined": combined,
            }
        )

    if not scored:
        return None

    best = max(scored, key=lambda x: x["combined"])

    reasons = []
    if best["genre_overlap"]:
        reasons.append(f"shares the {', '.join(sorted(best['genre_overlap']))} genre(s)")
    if best["desc_sim"] > 0.6:
        reasons.append("has a similar theme/plot")
    if best["keyword_sim"] > 0.5:
        reasons.append("touches on similar story elements")
    if best["collab_sim"] > 0.5:
        reasons.append("is often watched by users with similar taste to yours")
    if not reasons:
        reasons.append("is broadly similar in style")

    return (
        f'Because you watched "{best["title"]}", which {" and ".join(reasons)}, '
        f'we think you\'ll like "{recommended_title}".'
    )
