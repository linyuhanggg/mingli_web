from ipaddress import (
    IPv4Address,
    IPv4Network,
    IPv6Address,
    IPv6Network,
    ip_address,
    ip_network,
)

from fastapi import Request

IpAddress = IPv4Address | IPv6Address
IpNetwork = IPv4Network | IPv6Network


def parse_trusted_proxy_cidrs(value: str) -> tuple[IpNetwork, ...]:
    return tuple(
        ip_network(item.strip(), strict=False)
        for item in value.split(",")
        if item.strip()
    )


def resolve_client_ip(
    request: Request,
    *,
    trusted_proxy_networks: tuple[IpNetwork, ...],
) -> str:
    """Resolve a stable client IP without trusting headers from arbitrary peers."""

    peer = _parse_address(request.client.host if request.client is not None else "")
    if peer is None:
        return "unknown"
    if not _is_trusted(peer, trusted_proxy_networks):
        return _canonical(peer)

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return _canonical(peer)

    parts = [item.strip() for item in forwarded.split(",")]
    if not parts or len(parts) > 20:
        return _canonical(peer)

    chain: list[IpAddress] = []
    for part in parts:
        address = _parse_address(part)
        if address is None:
            return _canonical(peer)
        chain.append(address)

    for address in reversed(chain):
        if not _is_trusted(address, trusted_proxy_networks):
            return _canonical(address)

    return _canonical(chain[0])


def _parse_address(value: str) -> IpAddress | None:
    try:
        return ip_address(value)
    except ValueError:
        return None


def _is_trusted(address: IpAddress, networks: tuple[IpNetwork, ...]) -> bool:
    return any(
        address.version == network.version and address in network
        for network in networks
    )


def _canonical(address: IpAddress) -> str:
    if isinstance(address, IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped.compressed
    return address.compressed
