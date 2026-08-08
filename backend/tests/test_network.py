from app.network import parse_trusted_proxy_cidrs, resolve_client_ip
from fastapi import Request


def make_request(*, peer: str, forwarded_for: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/otp/request",
            "headers": [(b"x-forwarded-for", forwarded_for.encode("ascii"))],
            "client": (peer, 12345),
        }
    )


def test_untrusted_peer_cannot_spoof_the_client_ip() -> None:
    request = make_request(peer="198.51.100.8", forwarded_for="203.0.113.99")

    resolved = resolve_client_ip(
        request,
        trusted_proxy_networks=parse_trusted_proxy_cidrs("10.0.0.0/8"),
    )

    assert resolved == "198.51.100.8"


def test_trusted_chain_selects_the_nearest_untrusted_address() -> None:
    request = make_request(
        peer="10.0.0.5",
        forwarded_for="192.0.2.44, 203.0.113.3, 10.0.0.4",
    )

    resolved = resolve_client_ip(
        request,
        trusted_proxy_networks=parse_trusted_proxy_cidrs("10.0.0.0/8"),
    )

    assert resolved == "203.0.113.3"
