# RAG retrieval evaluation

How well does `knowledge_search` surface the right passage for a real customer
question? This is a **retrieval** eval (is the answer in what we hand the model),
not an end-to-end answer-quality eval.

## Method

- **Corpus:** the NovaTech knowledge base — 10 documents (`demo-data/knowledge/`,
  listed in `knowledge_index.json`), ~44 semantic chunks, indexed into Pinecone
  namespace `merchant_mrc_novatech_001` by `db/seeds/ingest_novatech_knowledge.py`.
- **Test set:** `backend/tests/rag_eval/dataset.py` — 38 questions phrased the way
  a shopper would ask (not the way the doc is written), each labelled with the
  `document_id`(s) a correct retrieval must return and, for most, a phrase the
  top chunk should contain.
- **Retriever under test:** `KnowledgeRetriever.retrieve` (OpenAI
  `text-embedding-3-small` → Pinecone top-k), exactly what the agent tool calls.

### Metrics

| Metric | Meaning |
|---|---|
| **hit@k** | fraction of questions where an expected doc is in the top *k* chunks |
| **MRR** | mean reciprocal rank of the first expected doc (0 if not in top 5) |
| **grounded@1** | fraction where the **top** chunk literally contains the expected answer phrase |

## Results — 2026-08-29

```
cases:        38
hit@1:        89.47%
hit@3:       100.00%
hit@5:       100.00%
MRR:          0.943
grounded@1:   83.33%   (of 36 phrase-checked)
```

**Read:** for every question the correct document is in the top 3, and ~90% of
the time it's the #1 result. The 17% `grounded@1` gap is questions where the
right document ranks first but the specific number/phrase lives in that
document's 2nd or 3rd chunk — the agent still receives it (it gets top-5), so the
answer is available; it's just not in the single best chunk.

## Running it

Needs live Pinecone + OpenAI creds (`backend/.env`) and the corpus ingested:

```bash
uv run --project backend python -m db.seeds.ingest_novatech_knowledge   # once
uv run --project backend python -m tests.rag_eval.runner
```

The runner also prints every question that fell below top-3 (none, currently).

It is **not** a pytest test: the test harness forces the Fake embedding/vector
clients for determinism, which would make a real-retrieval assertion meaningless.
Re-run it by hand after changing the chunker, the embedding model, the retrieval
`top_k`, or the corpus, and update the numbers above.
