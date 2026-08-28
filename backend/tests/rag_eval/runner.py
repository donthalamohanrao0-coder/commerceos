"""Score the knowledge retriever against ``dataset.CASES``.

Metrics
-------
hit@k        fraction of questions where an expected doc is in the top k
MRR          mean reciprocal rank of the first expected doc (0 if not in top k)
grounded@1   fraction where the top chunk contains the expected phrase
             (only counted for cases that specify a phrase)

Run it directly (needs the corpus ingested + real Pinecone/OpenAI creds):

    uv run python -m tests.rag_eval.runner
"""

from __future__ import annotations

from dataclasses import dataclass

from app.knowledge.retrieval.retriever import KnowledgeRetriever
from tests.rag_eval.dataset import CASES, EvalCase

NAMESPACE = "merchant_mrc_novatech_001"
KS = (1, 3, 5)


@dataclass
class Scored:
    case: EvalCase
    ranked_docs: list[str]
    first_rank: int | None  # 1-based rank of the first expected doc, else None
    grounded: bool | None  # None when the case has no phrase


def _first_expected_rank(ranked: list[str], expected: tuple[str, ...]) -> int | None:
    for i, doc in enumerate(ranked, start=1):
        if doc in expected:
            return i
    return None


def score_case(case: EvalCase, retriever: KnowledgeRetriever, top_k: int = 5) -> Scored:
    chunks = retriever.retrieve(namespace=NAMESPACE, query=case.question, top_k=top_k)
    ranked = [c.document_id for c in chunks]
    rank = _first_expected_rank(ranked, case.docs)
    grounded: bool | None = None
    if case.phrase:
        top_text = chunks[0].text.lower() if chunks else ""
        grounded = case.phrase.lower() in top_text
    return Scored(case=case, ranked_docs=ranked, first_rank=rank, grounded=grounded)


@dataclass
class Report:
    n: int
    hit_at: dict[int, float]
    mrr: float
    grounded_at_1: float
    grounded_n: int
    misses: list[Scored]


def run(retriever: KnowledgeRetriever | None = None) -> tuple[Report, list[Scored]]:
    retriever = retriever or KnowledgeRetriever()
    scored = [score_case(c, retriever) for c in CASES]

    hit_at = {
        k: sum(1 for s in scored if s.first_rank is not None and s.first_rank <= k) / len(scored)
        for k in KS
    }
    mrr = sum((1.0 / s.first_rank) if s.first_rank else 0.0 for s in scored) / len(scored)
    with_phrase = [s for s in scored if s.grounded is not None]
    grounded_at_1 = (
        sum(1 for s in with_phrase if s.grounded) / len(with_phrase) if with_phrase else 0.0
    )
    misses = [s for s in scored if s.first_rank is None or s.first_rank > 3]

    return (
        Report(
            n=len(scored),
            hit_at=hit_at,
            mrr=mrr,
            grounded_at_1=grounded_at_1,
            grounded_n=len(with_phrase),
            misses=misses,
        ),
        scored,
    )


def _fmt(report: Report) -> str:
    lines = [
        f"cases:        {report.n}",
        *[f"hit@{k}:       {report.hit_at[k]:.2%}" for k in KS],
        f"MRR:          {report.mrr:.3f}",
        f"grounded@1:   {report.grounded_at_1:.2%}  (of {report.grounded_n} phrase-checked)",
    ]
    if report.misses:
        lines.append("")
        lines.append(f"below top-3 ({len(report.misses)}):")
        for s in report.misses:
            got = ", ".join(s.ranked_docs[:3]) or "(nothing)"
            lines.append(f"  - {s.case.question}")
            lines.append(f"      want {s.case.docs} | got [{got}]")
    return "\n".join(lines)


if __name__ == "__main__":
    report, _ = run()
    print(_fmt(report))
