"""Default tests are offline, with credentials and tracing disabled."""

import socket

import pytest
from agents.tracing import set_trace_provider
from agents.tracing.provider import DefaultTraceProvider


@pytest.fixture(scope="session", autouse=True)
def tracing_without_exporters():
    # No default HTTP exporter: offline tests also work behind SOCKS proxies.
    provider = DefaultTraceProvider()
    provider.set_disabled(True)
    set_trace_provider(provider)
    yield
    provider.shutdown()


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_AGENTS_DISABLE_TRACING", "1")

    def deny_network(*args, **kwargs):
        raise AssertionError("Network access is forbidden in offline tests.")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_network)
    monkeypatch.setattr(socket, "getaddrinfo", deny_network)
