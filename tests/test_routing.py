from hermes_memory_router.models import MemoryHit


def test_primary_recall_wins(router):
    instance, primary, checkpoint = router
    primary.hits = [MemoryHit("primary", source="hindsight")]
    checkpoint.hits = [MemoryHit("fallback", source="mnemosyne")]
    result = instance.recall(query="q")
    assert [h.content for h in result.hits] == ["primary"]
    assert not result.fallback_used


def test_empty_primary_uses_checkpoint(router):
    instance, primary, checkpoint = router
    checkpoint.hits = [MemoryHit("checkpoint", source="mnemosyne")]
    result = instance.recall(query="q")
    assert result.fallback_used
    assert result.backend == "mnemosyne"


def test_primary_error_uses_checkpoint(router):
    instance, primary, checkpoint = router
    primary.fail_recall = 1
    checkpoint.hits = [MemoryHit("checkpoint")]
    result = instance.recall(query="q")
    assert result.fallback_used
    assert "failure" in result.primary_error


def test_fallback_context_is_bounded(router):
    instance, primary, checkpoint = router
    instance.config.routing.fallback_max_chars = 256
    checkpoint.hits = [MemoryHit("a" * 400), MemoryHit("b" * 400)]
    result = instance.recall(query="q")
    assert sum(len(hit.content) for hit in result.hits) <= 256


def test_reflect_goes_only_to_primary(router):
    instance, primary, checkpoint = router
    assert instance.reflect(query="why")["query"] == "why"
