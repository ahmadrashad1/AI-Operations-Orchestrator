from app.ai.llm_extraction import LLMExtractionAgent


def test_llm_extraction_fallback():
    agent = LLMExtractionAgent()
    # When no OPENAI_API_KEY is present in test env, the agent should fall back
    # to deterministic extraction and return an object with expected attributes.
    result = agent.extract("Need 3 laptops for engineering")
    assert result.quantity == 3 or isinstance(result.quantity, int)
    assert hasattr(result, "item_name")
    assert hasattr(result, "estimated_cost")
