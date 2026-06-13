import os, sys
from solace.messaging.messaging_service import MessagingService
from solace.messaging.resources.topic import Topic

target = os.environ.get("SHERPA_MESH_TARGET", "cloud")
if target == "local":
    host = os.environ.get("SOLACE_LOCAL_HOST", "tcp://localhost:55555")
    vpn = os.environ.get("SOLACE_LOCAL_VPN", "default")
    user = os.environ.get("SOLACE_LOCAL_USERNAME", "admin")
    pwd = os.environ.get("SOLACE_LOCAL_PASSWORD", "admin")
    use_tls = False
else:
    host = os.environ.get("SOLACE_HOST", "")
    vpn = os.environ.get("SOLACE_VPN", "")
    user = os.environ.get("SOLACE_USERNAME", "")
    pwd = os.environ.get("SOLACE_PASSWORD", "")
    use_tls = host.startswith("tcps://") or ":55443" in host

props = {
    "solace.messaging.transport.host": host,
    "solace.messaging.service.vpn-name": vpn,
    "solace.messaging.authentication.scheme.basic.username": user,
    "solace.messaging.authentication.scheme.basic.password": pwd,
}
try:
    builder = MessagingService.builder().from_properties(props)
    if use_tls:
        from solace.messaging.config.transport_security_strategy import TLS

        builder = builder.with_transport_security_strategy(
            TLS.create().without_certificate_validation()
        )
    service = builder.build()
    service.connect()
    pub = service.create_direct_message_publisher_builder().build()
    pub.start()
    pub.publish(destination=Topic.of("sherpa/smoke"), message="ready")
    pub.terminate()
    service.disconnect()
    note = " (TLS encrypted, cert validation disabled for pilot)" if use_tls else ""
    print(f"  [ OK ] Solace broker reachable ({target}) at {host}{note}")
except Exception as exc:
    print(f"  [FAIL] Solace mesh check failed ({target}): {exc}")
    sys.exit(1)
