import socket
from unittest.mock import patch

import pytest

from src.security.ssrf_protector import SSRFProtector, SSRFSecurityException


@pytest.fixture(autouse=True)
def clear_cache():
    """Ensure the DNS cache is cleared before every test."""
    SSRFProtector._dns_cache.clear()


def test_validate_webhook_url_empty():
    with pytest.raises(SSRFSecurityException, match="cannot be empty"):
        SSRFProtector.validate_webhook_url("")


def test_validate_webhook_url_insecure_scheme():
    with pytest.raises(SSRFSecurityException, match="must use 'https'"):
        SSRFProtector.validate_webhook_url("http://example.com/webhook")


def test_validate_webhook_url_missing_hostname():
    with pytest.raises(SSRFSecurityException, match="missing hostname"):
        SSRFProtector.validate_webhook_url("https://")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_dns_failure(mock_getaddrinfo):
    mock_getaddrinfo.side_effect = socket.gaierror("Name or service not known")
    with pytest.raises(SSRFSecurityException, match="DNS resolution failed"):
        SSRFProtector.validate_webhook_url("https://nonexistent.domain.local/api")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_loopback(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(2, 1, 6, "", ("127.0.0.1", 443))]
    with pytest.raises(SSRFSecurityException, match="Blocked loopback IP: 127.0.0.1"):
        SSRFProtector.validate_webhook_url("https://localhost:8080/hook")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
@pytest.mark.parametrize(
    "blocked_ip",
    [
        "10.0.0.1",
        "10.0.0.5",
        "172.16.5.10",
        "192.168.1.1",
        "192.168.1.25",
    ],
)
def test_validate_webhook_url_private_ipv4_subnet_blocklist(
    mock_getaddrinfo, blocked_ip
):
    mock_getaddrinfo.return_value = [(2, 1, 6, "", (blocked_ip, 443))]
    with pytest.raises(SSRFSecurityException, match="Blocked private network IP"):
        SSRFProtector.validate_webhook_url("https://internal.corp.network/webhook")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_link_local(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(2, 1, 6, "", ("169.254.169.254", 443))]
    with pytest.raises(
        SSRFSecurityException, match="Blocked link-local IP: 169.254.169.254"
    ):
        SSRFProtector.validate_webhook_url("https://aws-metadata-service.local/data")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_multicast(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(2, 1, 6, "", ("224.0.0.1", 443))]
    with pytest.raises(SSRFSecurityException, match="Blocked multicast IP: 224.0.0.1"):
        SSRFProtector.validate_webhook_url("https://multicast.local/data")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_ipv6_loopback(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(10, 1, 6, "", ("::1", 443, 0, 0))]
    with pytest.raises(SSRFSecurityException, match="Blocked loopback IP: ::1"):
        SSRFProtector.validate_webhook_url("https://ipv6-localhost.local/hook")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_ipv6_private(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(10, 1, 6, "", ("fd00::1", 443, 0, 0))]
    with pytest.raises(
        SSRFSecurityException, match="Blocked private network IP: fd00::1"
    ):
        SSRFProtector.validate_webhook_url("https://ipv6-internal.local/hook")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_ipv6_link_local(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(10, 1, 6, "", ("fe80::1", 443, 0, 0))]
    with pytest.raises(SSRFSecurityException, match="Blocked link-local IP: fe80::1"):
        SSRFProtector.validate_webhook_url("https://ipv6-link-local.local/hook")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_ipv6_multicast(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(10, 1, 6, "", ("ff00::1", 443, 0, 0))]
    with pytest.raises(SSRFSecurityException, match="Blocked multicast IP: ff00::1"):
        SSRFProtector.validate_webhook_url("https://ipv6-multicast.local/hook")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_ipv6_unspecified(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(10, 1, 6, "", ("::", 443, 0, 0))]
    with pytest.raises(SSRFSecurityException, match="Blocked unspecified IP"):
        SSRFProtector.validate_webhook_url("https://unspecified.local/hook")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_ipv6_mapped_ipv4_loopback(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(10, 1, 6, "", ("::ffff:127.0.0.1", 443, 0, 0))]
    with pytest.raises(SSRFSecurityException, match="Blocked loopback IP"):
        SSRFProtector.validate_webhook_url("https://mapped-ipv6-loopback.local/hook")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_ipv6_mapped_ipv4_private(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(10, 1, 6, "", ("::ffff:10.0.0.1", 443, 0, 0))]
    with pytest.raises(SSRFSecurityException, match="Blocked private network IP"):
        SSRFProtector.validate_webhook_url("https://mapped-ipv6-private.local/hook")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_invalid_ip_format(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(2, 1, 6, "", ("not_an_ip", 443))]
    with pytest.raises(SSRFSecurityException, match="invalid IP address format"):
        SSRFProtector.validate_webhook_url("https://invalid-ip.local/hook")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_validate_webhook_url_safe(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(2, 1, 6, "", ("142.250.190.46", 443))]
    result = SSRFProtector.validate_webhook_url(
        "https://discord.com/api/webhooks/123/abc"
    )
    assert result is True


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_dns_caching_behavior(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(2, 1, 6, "", ("142.250.190.46", 443))]
    SSRFProtector.validate_webhook_url("https://discord.com/api/webhooks/123/abc")
    assert mock_getaddrinfo.call_count == 1
    SSRFProtector.validate_webhook_url("https://discord.com/api/webhooks/123/abc")
    assert mock_getaddrinfo.call_count == 1


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_dns_cache_expired(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(2, 1, 6, "", ("142.250.190.46", 443))]
    SSRFProtector.validate_webhook_url("https://discord.com/api/webhooks/123/abc")
    assert mock_getaddrinfo.call_count == 1
    hostname = "discord.com"
    cached_ip, _ = SSRFProtector._dns_cache[hostname]
    SSRFProtector._dns_cache[hostname] = (cached_ip, 0)
    SSRFProtector.validate_webhook_url("https://discord.com/api/webhooks/123/abc")
    assert mock_getaddrinfo.call_count == 2


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_empty_dns_resolution(mock_getaddrinfo):
    mock_getaddrinfo.return_value = []
    with pytest.raises(SSRFSecurityException, match="No addresses found for hostname"):
        SSRFProtector.validate_webhook_url("https://empty.domain.local/api")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_resolve_hostname_success(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(2, 1, 6, "", ("8.8.8.8", 53))]
    ip = SSRFProtector._resolve_hostname("dns.google")
    assert ip == "8.8.8.8"


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_resolve_hostname_dns_failure(mock_getaddrinfo):
    mock_getaddrinfo.side_effect = socket.gaierror("DNS error")
    with pytest.raises(SSRFSecurityException, match="DNS resolution failed"):
        SSRFProtector._resolve_hostname("nonexistent.domain.local")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_resolve_hostname_empty_list(mock_getaddrinfo):
    mock_getaddrinfo.return_value = []
    with pytest.raises(SSRFSecurityException, match="No addresses found"):
        SSRFProtector._resolve_hostname("empty.domain.local")


@patch("src.security.ssrf_protector.socket.getaddrinfo")
def test_resolve_hostname_cache_hit(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(2, 1, 6, "", ("1.2.3.4", 53))]
    SSRFProtector._resolve_hostname("cached.host")
    assert mock_getaddrinfo.call_count == 1
    SSRFProtector._resolve_hostname("cached.host")
    assert mock_getaddrinfo.call_count == 1
