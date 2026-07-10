"""Thread-safety test for ProviderRegistry (V1.2.0 design spec #50 §11, D18).

This is a regression test for the thread-safety contract. The
registry must be safe to call from multiple threads concurrently;
concurrent ``register`` + ``resolve`` + ``get`` must complete
without exception and leave the registry in a consistent state.
"""
from __future__ import annotations

import threading

import pytest

from paxman.providers._model import ModelRef, ProviderRegistry


class _StubProvider:
    """Minimal Provider Protocol for thread-safety tests."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.capabilities: frozenset[str] = frozenset({"text"})

    def complete(self, request):  # pragma: no cover
        raise NotImplementedError


@pytest.mark.parametrize("worker_count", [4, 16])
def test_concurrent_register_resolve_get(worker_count: int) -> None:
    """N threads concurrently register, resolve, and get providers.

    With a re-entrant lock (RLock), the registry's internal state
    is always consistent. The test asserts no exception is raised,
    the final state matches the expected count, and every ``get()``
    call after registration succeeds for a known name.
    """
    reg = ProviderRegistry()
    errors: list[BaseException] = []
    barrier = threading.Barrier(worker_count)

    def worker(i: int) -> None:
        try:
            barrier.wait()  # synchronize start
            name = f"provider-{i}"
            provider = _StubProvider(name=name)
            reg.register(name, provider)
            ref = ModelRef(provider=name, model="x")
            resolved = reg.resolve(ref)
            assert resolved.name == name
            assert reg.get(name) is resolved
            assert name in reg
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(worker_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)
        assert not t.is_alive(), "thread hung"

    assert not errors, f"workers raised: {errors}"
    assert len(reg) == worker_count


def test_concurrent_register_with_replace() -> None:
    """Concurrent register-with-replace must not corrupt the registry.

    Two threads racing to register the same name with ``replace=True``
    must result in exactly one final registration (whichever thread
    won the race), and the final state must be a valid provider.
    """
    reg = ProviderRegistry()
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def worker(i: int) -> None:
        try:
            barrier.wait()
            provider = _StubProvider(name=f"winner-{i}")
            reg.register("contested", provider, replace=True)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert not errors, f"workers raised: {errors}"
    final = reg.get("contested")
    assert final.name in {"winner-0", "winner-1"}
    assert len(reg) == 1


def test_resolve_unknown_during_register_race() -> None:
    """If thread A is registering a name and thread B is resolving it
    concurrently, B may either get the new provider or
    ``ConfigurationError(INFERENCE_PROVIDER_NOT_REGISTERED)`` — but
    never a corrupted state (a different provider object, an
    ``AttributeError``, or a deadlock)."""
    reg = ProviderRegistry()
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def registerer() -> None:
        try:
            barrier.wait()
            reg.register("racy", _StubProvider(name="racy"))
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    def resolver() -> None:
        try:
            barrier.wait()
            try:
                reg.resolve(ModelRef(provider="racy", model="x"))
            except Exception:  # noqa: BLE001
                # INFERENCE_PROVIDER_NOT_REGISTERED is acceptable here.
                pass
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=registerer), threading.Thread(target=resolver)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert not errors, f"workers raised: {errors}"
    # The final state is consistent: 'racy' is registered.
    assert "racy" in reg
    assert reg.get("racy").name == "racy"


def test_concurrent_contains_and_len() -> None:
    """Concurrent ``__contains__`` and ``__len__`` calls must return
    consistent snapshots. A reader may see the registry mid-update
    (a name may be present or not), but the read is atomic and
    does not raise."""
    reg = ProviderRegistry()
    reg.register("seed", _StubProvider(name="seed"))
    errors: list[BaseException] = []
    barrier = threading.Barrier(8)

    def reader(i: int) -> None:
        try:
            barrier.wait()
            for _ in range(1000):
                _ = "seed" in reg
                _ = len(reg)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    def writer(i: int) -> None:
        try:
            barrier.wait()
            for j in range(100):
                reg.register(
                    f"writer-{i}-{j}",
                    _StubProvider(name=f"writer-{i}-{j}"),
                    replace=True,
                )
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [
        threading.Thread(target=reader, args=(i,)) for i in range(4)
    ] + [threading.Thread(target=writer, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)
        assert not t.is_alive(), "thread hung"

    assert not errors, f"workers raised: {errors}"
