import pytest

from app.agents.supervisor import classify_workflow


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("How can I grow revenue with a cross-sell campaign?", "growth"),
        ("Show me the attach rate for laptops", "growth"),
        ("Where is my order ORD-1002?", "support"),
        ("I want to return a damaged item", "support"),
        ("Track my delivery please", "support"),
        ("I need a laptop for software development", "shopping"),
        ("recommend a good wireless mouse", "shopping"),
        ("", "shopping"),  # empty -> safe default
    ],
)
def test_keyword_routing(text: str, expected: str) -> None:
    assert classify_workflow(text) == expected


def test_llm_refinement_is_optional_and_safe() -> None:
    class _BrokenClient:
        model = "broken"

        def complete(self, **_: object) -> object:
            raise RuntimeError("no network")

    # weak keyword signal + broken client must still return a valid default
    assert classify_workflow("hello there", chat_client=_BrokenClient()) == "shopping"  # type: ignore[arg-type]
