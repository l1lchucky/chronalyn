from concurrent.futures import ThreadPoolExecutor

from hermes_memory_router.store import RouterStore


def test_store_is_namespace_scoped(tmp_path):
    store = RouterStore(tmp_path / "router.db")
    a, _ = store.create_record(
        namespace="a",
        environment="production",
        kind="checkpoint",
        content="same",
        metadata={},
        backends=["hindsight"],
    )
    b, _ = store.create_record(
        namespace="b",
        environment="production",
        kind="checkpoint",
        content="same",
        metadata={},
        backends=["hindsight"],
    )
    assert a != b
    store.close()


def test_concurrent_idempotency(tmp_path):
    path = tmp_path / "router.db"
    store = RouterStore(path)

    def create():
        return store.create_record(
            namespace="a",
            environment="staging",
            kind="checkpoint",
            content="same",
            metadata={"x": 1},
            backends=["hindsight", "mnemosyne"],
        )[0]

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda _: create(), range(20)))
    assert len(set(ids)) == 1
    store.close()
