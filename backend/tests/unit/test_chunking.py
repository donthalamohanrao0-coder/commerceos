from app.knowledge.chunking import chunk_markdown, estimate_tokens

FAQ = """# Customer Support FAQ
Q: How do I track an order?
A: Open Orders and select the order.

Q: What if an item arrived damaged?
A: Report it within 48 hours with photos.
"""

POLICY = """# Returns Policy
Eligible products can be returned within 7 calendar days. Final-sale products are excluded.
"""

GUIDE = """# Product Recommendation Guide
For coding:
- prioritize RAM and storage.

For students:
- prioritize value and battery.
"""


def test_faq_splits_one_chunk_per_qa() -> None:
    chunks = chunk_markdown(FAQ)
    assert len(chunks) == 2
    assert chunks[0].heading == "How do I track an order?"
    assert "damaged" not in chunks[0].text  # answers never bleed together
    assert all(c.text.startswith("# Customer Support FAQ") for c in chunks)


def test_flat_policy_is_single_chunk() -> None:
    chunks = chunk_markdown(POLICY)
    assert len(chunks) == 1
    assert "7 calendar days" in chunks[0].text


def test_guide_splits_per_label_group() -> None:
    chunks = chunk_markdown(GUIDE)
    assert {c.heading for c in chunks} == {"For coding", "For students"}


def test_oversized_unit_is_sentence_split() -> None:
    big = "# Doc\n" + " ".join(f"Sentence number {i} here." for i in range(400))
    chunks = chunk_markdown(big, target_tokens=120, max_tokens=200, overlap_tokens=20)
    assert len(chunks) > 1
    assert all(estimate_tokens(c.text) <= 260 for c in chunks)


def test_chunk_indexes_are_sequential() -> None:
    chunks = chunk_markdown(GUIDE)
    assert [c.index for c in chunks] == list(range(len(chunks)))
