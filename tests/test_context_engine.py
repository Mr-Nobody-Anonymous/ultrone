# Copyright (c) Ultrone Contributors. All rights reserved.
from packages.core.context import (
    ContextBudget,
    ContextCompactor,
    ContextManager,
    RelevanceRanker,
    TokenCounter,
)


def test_token_counter_estimation():
    text = "This is a simple sample sentence for testing token counting."
    tokens = TokenCounter.count_tokens(text)
    assert tokens > 5
    assert TokenCounter.count_tokens("") == 0


def test_compaction_truncates_large_text():
    long_text = "\n".join([f"Line {i}: some logging information that goes on" for i in range(200)])
    compacted = ContextCompactor.compact_text(long_text, max_tokens=50)
    assert TokenCounter.count_tokens(compacted) <= 80
    assert "compacted" in compacted or "truncated" in compacted


def test_relevance_ranker():
    query = "satellite imagery detection"
    items = [
        "Unrelated recipe for baking bread",
        "Autonomous land rover navigation algorithms",
        "Satellite image preprocessing and object detection",
        "Cyber threat intrusion detection logs",
    ]
    ranked = RelevanceRanker.rank_items(query, items, top_k=2)
    assert len(ranked) == 2
    assert "Satellite image" in ranked[0]


def test_context_manager_assembly():
    cm = ContextManager(ContextBudget(total_window=4000))
    prompt = cm.assemble_context(
        system_instructions="You are an autonomous air defense agent.",
        goal="Intercept target UAV within designated corridor",
        user_request="Provide flight vector plan",
        memories=["Previous encounter in sector 4 had crosswinds", "Terrain elevation is 450m"],
        observations=["Radar track #218 acquired at bearing 045"],
    )
    assert "### SYSTEM INSTRUCTIONS" in prompt
    assert "### ACTIVE GOAL" in prompt
    assert "### RELEVANT MEMORY" in prompt
    assert "### RECENT OBSERVATIONS" in prompt
    assert "### USER REQUEST" in prompt
    assert cm.estimate_tokens(prompt) < 4000
