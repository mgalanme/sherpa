"""Solace mesh integration.

For the pilot, the orchestration runs in-process with LangGraph, and the Solace broker carries
governance and observability events: each agent step and each Human-in-the-Loop decision is
published to a topic, so the event mesh genuinely runs in the cloud (Solace Cloud) or locally
(PubSub+), giving an auditable, observable backbone. Publishing is best-effort and never blocks
the workflow.

TLS note (validated during setup): the bundled libsolclient does not resolve Solace Cloud's
intermediate CA chain, so the pilot uses without_certificate_validation(), which still gives an
encrypted TLS transport. Production should use a Solace-provided trust store.
"""

from __future__ import annotations

import json
from functools import lru_cache

from .config import get_settings

_TOPIC_PREFIX = "sherpa"


@lru_cache(maxsize=1)
def _service():
    s = get_settings()
    if not (s.mesh_enabled and s.solace_host):
        return None
    try:
        from solace.messaging.messaging_service import MessagingService

        props = {
            "solace.messaging.transport.host": s.solace_host,
            "solace.messaging.service.vpn-name": s.solace_vpn,
            "solace.messaging.authentication.scheme.basic.username": s.solace_username,
            "solace.messaging.authentication.scheme.basic.password": s.solace_password,
        }
        builder = MessagingService.builder().from_properties(props)
        if s.solace_host.startswith("tcps://") or ":55443" in s.solace_host:
            from solace.messaging.config.transport_security_strategy import TLS

            builder = builder.with_transport_security_strategy(
                TLS.create().without_certificate_validation()
            )
        service = builder.build()
        service.connect()
        return service
    except Exception:
        return None


@lru_cache(maxsize=1)
def _publisher():
    service = _service()
    if service is None:
        return None
    try:
        pub = service.create_direct_message_publisher_builder().build()
        pub.start()
        return pub
    except Exception:
        return None


def publish_event(plan_id: str, stage: str, payload: dict) -> None:
    """Best-effort publication of a governance/observability event to the mesh."""
    pub = _publisher()
    if pub is None:
        return
    try:
        from solace.messaging.resources.topic import Topic

        topic = Topic.of(f"{_TOPIC_PREFIX}/plan/{plan_id}/{stage}")
        pub.publish(
            destination=topic,
            message=json.dumps(payload, ensure_ascii=False, default=str),
        )
    except Exception:
        pass
