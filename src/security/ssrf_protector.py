"""
src/security/ssrf_protector.py
------------------------------
Server-Side Request Forgery (SSRF) protection module for webhook validation.

Provides comprehensive URL validation including:
- HTTPS scheme enforcement
- Domain allowlist verification
- DNS resolution with caching
- Private/loopback/link-local IP blocking
- Redirect chain validation with depth limits
- Explicit User-Agent header attachment (Issue #2212)
- Strict MyPy type checking compliance (Issue #3250)
"""

from __future__ import annotations

import ipaddress
import logging
import socket
import time
import idna
import urllib.parse
from collections import OrderedDict
from typing import Optional, Tuple, List, Dict

import requests

from src.errors import (
    SSRF_BLOCKED_LINK_LOCAL,
    SSRF_BLOCKED_LOOPBACK,
    SSRF_BLOCKED_MULTICAST,
    SSRF_BLOCKED_PRIVATE,
    SSRF_BLOCKED_UNSPECIFIED,
    SSRF_CIRCULAR_REDIRECT_LOOP,
    SSRF_DNS_NO_ADDRESSES,
    SSRF_DNS_RESOLUTION_FAILED,
    SSRF_DOMAIN_NOT_ALLOWED,
    SSRF_INSECURE_SCHEME,
    SSRF_INVALID_IP_FORMAT,
    SSRF_MAX_REDIRECTS_EXCEEDED,
    SSRF_MISSING_HOSTNAME,
    SSRF_WEBHOOK_URL_EMPTY,
)

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT: str = "SemanticPlagiarismDetector/1.0"
DEFAULT_REQUEST_TIMEOUT: float = 5.0
REDIRECT_STATUS_CODES: Tuple[int, ...] = (301, 302, 303, 307, 308)
HEAD_REJECTION_STATUS_CODES: Tuple[int, ...] = (405, 501)

RESTRICTED_IPV4_CIDR_BLOCKS: Tuple[str, ...] = (
    "127.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
)


def is_ip_in_cidr_block(ip_str: str, cidr_block: str) -> bool:
    """Return whether an IP address belongs to a CIDR network under strict typing."""
    ip_str = ip_str.strip()

    try:
        ip_address = ipaddress.ip_address(ip_str)
        network = ipaddress.ip_network(cidr_block, strict=False)
    except (TypeError, ValueError):
        return False

    if ip_address.version != network.version:
        if network.version == 4 and ip_address.version == 6:
            mapped = getattr(ip_address, "ipv4_mapped", None)
            if mapped is not None:
                ip_address = mapped
            else:
                return False
        else:
            return False

    return ip_address in network


class SSRFSecurityException(Exception):
    """Raised when a Webhook URL fails SSRF security checks."""

    pass


class SSRFProtector:
    """Core security module designed to prevent SSRF attacks under strict typing."""

    _dns_cache: "OrderedDict[str, tuple[str, float]]" = OrderedDict()
    DNS_CACHE_TTL_SECONDS: int = 300
    DNS_CACHE_MAX_SIZE: int = 1000
    RESTRICTED_IPV4_CIDR_BLOCKS: Tuple[str, ...] = RESTRICTED_IPV4_CIDR_BLOCKS
    MAX_REDIRECT_DEPTH: int = 5
    DEFAULT_USER_AGENT: str = DEFAULT_USER_AGENT

    @classmethod
    def _resolve_hostname(cls, hostname: str) -> str:
        current_time = float(time.time())

        if hostname in cls._dns_cache:
            cached_ip, timestamp = cls._dns_cache[hostname]
            if current_time - timestamp < cls.DNS_CACHE_TTL_SECONDS:
                cls._dns_cache.move_to_end(hostname)
                return cached_ip
            del cls._dns_cache[hostname]

        try:
            addr_info = socket.getaddrinfo(hostname, None)
            if not addr_info:
                raise SSRFSecurityException(
                    SSRF_DNS_NO_ADDRESSES.format(hostname=hostname)
                )

            ip_str = str(addr_info[0][4][0])
            cls._dns_cache[hostname] = (ip_str, current_time)
            cls._dns_cache.move_to_end(hostname)
            if len(cls._dns_cache) > cls.DNS_CACHE_MAX_SIZE:
                cls._dns_cache.popitem(last=False)
            return ip_str

        except socket.gaierror as e:
            raise SSRFSecurityException(
                SSRF_DNS_RESOLUTION_FAILED.format(hostname=hostname, error=e)
            )

    @classmethod
    def _validate_url_target(
        cls,
        url: str,
        allowed_domains: Optional[List[str]] = None,
    ) -> str:
        if not url:
            raise SSRFSecurityException(SSRF_WEBHOOK_URL_EMPTY)

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            raise SSRFSecurityException(
                SSRF_INSECURE_SCHEME.format(scheme=parsed.scheme)
            )

        hostname: Optional[str] = parsed.hostname
        if not hostname:
            raise SSRFSecurityException(SSRF_MISSING_HOSTNAME)

        # Encode hostname to ASCII (Punycode) to prevent IDN homograph attacks
        try:
            hostname = idna.encode(hostname).decode("ascii")
        except idna.IDNAError:
            raise SSRFSecurityException(SSRF_INVALID_HOSTNAME)

        # Normalize allowed domains to Punycode as well
        normalized_allowed_domains = []
        for domain in allowed_domains or []:
            try:
                normalized_allowed_domains.append(idna.encode(domain).decode("ascii"))
            except idna.IDNAError:
                continue

        if hostname in normalized_allowed_domains:
            try:
                from src.core.app_config import get_allowed_webhook_domains

                allowed_domains = get_allowed_webhook_domains()
            except ImportError:
                allowed_domains = []

        if allowed_domains:
            host_lower = hostname.lower()
            allowed = False
            for domain in allowed_domains:
                dom_lower = domain.lower()
                if host_lower == dom_lower or host_lower.endswith("." + dom_lower):
                    allowed = True
                    break
            if not allowed:
                raise SSRFSecurityException(
                    SSRF_DOMAIN_NOT_ALLOWED.format(hostname=hostname)
                )
        else:
            logger.debug(
                "Domain allowlist is empty. Permitting all external domains for %s.",
                hostname,
            )

        ip_str = cls._resolve_hostname(hostname)

        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError as e:
            raise SSRFSecurityException(SSRF_INVALID_IP_FORMAT.format(error=e))

        if ip.version == 6:
            mapped = getattr(ip, "ipv4_mapped", None)
            if mapped is not None:
                ip = mapped
                ip_str = str(ip)

        if isinstance(ip, ipaddress.IPv4Address):
            for cidr_block in cls.RESTRICTED_IPV4_CIDR_BLOCKS:
                if is_ip_in_cidr_block(ip_str, cidr_block):
                    if is_ip_in_cidr_block(ip_str, "127.0.0.0/8"):
                        raise SSRFSecurityException(
                            SSRF_BLOCKED_LOOPBACK.format(ip=ip_str)
                        )
                    raise SSRFSecurityException(SSRF_BLOCKED_PRIVATE.format(ip=ip_str))

        if ip.is_loopback:
            raise SSRFSecurityException(SSRF_BLOCKED_LOOPBACK.format(ip=ip_str))
        if ip.is_link_local:
            raise SSRFSecurityException(SSRF_BLOCKED_LINK_LOCAL.format(ip=ip_str))
        if ip.is_multicast:
            raise SSRFSecurityException(SSRF_BLOCKED_MULTICAST.format(ip=ip_str))
        if ip.is_unspecified:
            raise SSRFSecurityException(SSRF_BLOCKED_UNSPECIFIED.format(ip=ip_str))
        if ip.is_private:
            raise SSRFSecurityException(SSRF_BLOCKED_PRIVATE.format(ip=ip_str))

        logger.debug(f"SSRF Check passed for {url} -> {ip_str}")
        return ip_str

    @classmethod
    def _make_validation_request(
        cls,
        url: str,
        user_agent: str,
        timeout: float,
    ) -> requests.Response:
        headers: Dict[str, str] = {"User-Agent": user_agent}

        logger.debug(
            "Making validation request to %s with User-Agent: %s", url, user_agent
        )

        try:
            response = requests.head(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=False,
            )

            if response.status_code in HEAD_REJECTION_STATUS_CODES:
                logger.debug(
                    "Server rejected HEAD with %d, falling back to GET for %s",
                    response.status_code,
                    url,
                )
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=False,
                    stream=True,
                )

            return response

        except requests.RequestException as exc:
            logger.debug(f"Validation request failed for {url}: {exc}")
            raise

    @classmethod
    def validate_webhook_url(
        cls,
        url: str,
        allowed_domains: Optional[List[str]] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_REQUEST_TIMEOUT,
    ) -> bool:
        cls._validate_url_target(url, allowed_domains=allowed_domains)

        try:
            cls._make_validation_request(url, user_agent, timeout)
        except Exception as e:
            logger.debug(f"Outgoing HTTP validation request failed for {url}: {e}")

        return True

    @classmethod
    def _check_redirect_depth(
        cls,
        current_url: str,
        allowed_domains: Optional[List[str]] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_REQUEST_TIMEOUT,
    ) -> Optional[str]:
        cls._validate_url_target(current_url, allowed_domains=allowed_domains)
        response = cls._make_validation_request(current_url, user_agent, timeout)

        if response.status_code in REDIRECT_STATUS_CODES:
            location = response.headers.get("Location")
            if location:
                return str(urllib.parse.urljoin(current_url, location))
        return None

    @classmethod
    def validate_url_safety(
        cls,
        url: str,
        allowed_domains: Optional[List[str]] = None,
        max_redirects: Optional[int] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_REQUEST_TIMEOUT,
    ) -> Tuple[str, str]:
        if max_redirects is None:
            max_redirects = cls.MAX_REDIRECT_DEPTH

        current_url = url
        pinned_ip = cls._validate_url_target(url, allowed_domains=allowed_domains)

        hops = 0
        seen_urls = {current_url}
        while True:
            next_url = cls._check_redirect_depth(
                current_url,
                allowed_domains=allowed_domains,
                user_agent=user_agent,
                timeout=timeout,
            )
            if next_url is None:
                break

            hops += 1
            if hops > max_redirects:
                raise SSRFSecurityException(SSRF_MAX_REDIRECTS_EXCEEDED)

            if next_url in seen_urls:
                raise SSRFSecurityException(SSRF_CIRCULAR_REDIRECT_LOOP)
            seen_urls.add(next_url)

            current_url = next_url
            pinned_ip = cls._validate_url_target(
                current_url,
                allowed_domains=allowed_domains,
            )

        return current_url, pinned_ip
