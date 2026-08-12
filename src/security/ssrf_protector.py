import ipaddress
import logging
import socket
import time
import urllib.parse
from typing import Dict, Tuple

import requests

from src.errors import (
    SSRF_BLOCKED_LINK_LOCAL,
    SSRF_BLOCKED_LOOPBACK,
    SSRF_BLOCKED_MULTICAST,
    SSRF_BLOCKED_PRIVATE,
    SSRF_BLOCKED_UNSPECIFIED,
    SSRF_DNS_NO_ADDRESSES,
    SSRF_DNS_RESOLUTION_FAILED,
    SSRF_DOMAIN_NOT_ALLOWED,
    SSRF_INSECURE_SCHEME,
    SSRF_INVALID_IP_FORMAT,
    SSRF_MISSING_HOSTNAME,
    SSRF_WEBHOOK_URL_EMPTY,
)

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "SemanticPlagiarismDetector/1.0"

RESTRICTED_IPV4_CIDR_BLOCKS = (
    "127.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
)


def is_ip_in_cidr_block(
    ip_str: str,
    cidr_block: str,
) -> bool:
    """Return whether an IP address belongs to a CIDR network.

    Invalid addresses, malformed CIDR values, and IP-version mismatches return
    ``False`` rather than leaking ``ipaddress`` parsing errors into callers.

    Args:
        ip_str: IPv4 or IPv6 address string.
        cidr_block: IPv4 or IPv6 network in CIDR notation.

    Returns:
        ``True`` when the address is contained in the network; otherwise
        ``False``.
    """
    try:
        ip_address = ipaddress.ip_address(ip_str)
        network = ipaddress.ip_network(
            cidr_block,
            strict=False,
        )
    except (TypeError, ValueError):
        return False

    if ip_address.version != network.version:
        return False

    return ip_address in network


class SSRFSecurityException(Exception):
    """Raised when a Webhook URL fails SSRF security checks."""

    pass


class SSRFProtector:
    """
    Core security module designed to prevent Server-Side Request Forgery (SSRF)
    attacks via the Webhook feature. Includes DNS rebinding protection caching.
    """

    # Simple in-memory cache to prevent repeated DNS lookups and mitigate
    # slow-DNS denial of service attacks. (Format: {hostname: (ip_str, timestamp)})
    _dns_cache: Dict[str, tuple[str, float]] = {}
    DNS_CACHE_TTL_SECONDS = 300  # 5 minutes
    RESTRICTED_IPV4_CIDR_BLOCKS = RESTRICTED_IPV4_CIDR_BLOCKS
    MAX_REDIRECT_DEPTH = 5
    DEFAULT_USER_AGENT = DEFAULT_USER_AGENT

    @classmethod
    def _resolve_hostname(cls, hostname: str) -> str:
        """
        Resolves a hostname to an IP address with a caching layer.
        """
        current_time = time.time()

        # Check cache first
        if hostname in cls._dns_cache:
            cached_ip, timestamp = cls._dns_cache[hostname]
            if current_time - timestamp < cls.DNS_CACHE_TTL_SECONDS:
                return cached_ip

        # Cache miss or expired, perform DNS resolution
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            if not addr_info:
                raise SSRFSecurityException(
                    SSRF_DNS_NO_ADDRESSES.format(hostname=hostname)
                )

            ip_str = addr_info[0][4][0]
            cls._dns_cache[hostname] = (ip_str, current_time)
            return ip_str

        except socket.gaierror as e:
            raise SSRFSecurityException(
                SSRF_DNS_RESOLUTION_FAILED.format(hostname=hostname, error=e)
            )

    @classmethod
    def validate_webhook_url(
        cls,
        url: str,
        allowed_domains: list[str] | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> bool:
        """
        Validates that a provided webhook URL is safe to dispatch.
        Ensures the URL uses HTTPS, its domain is in ALLOWED_WEBHOOK_DOMAINS (if configured),
        does not resolve to any internal network IP, and sends an outgoing HTTP validation check.

        Args:
            url: The webhook URL string
            allowed_domains: Optional list of allowed domain hostnames. If None,
                fetches configured domains via ``get_allowed_webhook_domains()``.
            user_agent: Custom User-Agent header for validation requests.

        Returns:
            True if the URL is strictly safe.

        Raises:
            SSRFSecurityException: If the URL is malicious or unapproved.
        """
        if not url:
            raise SSRFSecurityException(SSRF_WEBHOOK_URL_EMPTY)

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            raise SSRFSecurityException(
                SSRF_INSECURE_SCHEME.format(scheme=parsed.scheme)
            )

        hostname = parsed.hostname
        if not hostname:
            raise SSRFSecurityException(SSRF_MISSING_HOSTNAME)

        # Domain whitelist validation
        if allowed_domains is None:
            from src.core.app_config import get_allowed_webhook_domains

            allowed_domains = get_allowed_webhook_domains()

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

        # 2. DNS Resolution
        ip_str = cls._resolve_hostname(hostname)

        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError as e:
            raise SSRFSecurityException(SSRF_INVALID_IP_FORMAT.format(error=e))

        if isinstance(ip, ipaddress.IPv4Address):
            for cidr_block in cls.RESTRICTED_IPV4_CIDR_BLOCKS:
                if is_ip_in_cidr_block(ip_str, cidr_block):
                    if is_ip_in_cidr_block(
                        ip_str,
                        "127.0.0.0/8",
                    ):
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

        # Outgoing HTTP validation request attaching configured User-Agent header
        headers = {"User-Agent": user_agent}
        try:
            requests.head(url, headers=headers, timeout=5.0, allow_redirects=False)
        except Exception as e:
            logger.debug(f"Outgoing HTTP validation request failed for {url}: {e}")

        # If it passed all checks, it's considered safe (public routable IP)
        logger.debug(f"SSRF Check passed for {url} -> {ip_str}")
        return True

    @classmethod
    def _check_redirect_depth(
        cls,
        current_url: str,
        allowed_domains: list[str] | None = None,
    ) -> str | None:
        """
        Inspects a single hop of a redirect chain.

        The URL is fully re-validated (domain allow-list, DNS resolution,
        internal/private IP checks) BEFORE any outbound HTTP request is
        made, so this module never contacts an attacker-controlled internal
        address.

        Returns:
            The next URL in the chain if a redirect is present, else None.
        """
        # Validate BEFORE making any outbound request.
        cls.validate_webhook_url(current_url, allowed_domains=allowed_domains)

        response = requests.head(current_url, allow_redirects=False, timeout=5)
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location")
            if location:
                return urllib.parse.urljoin(current_url, location)
        return None

    @classmethod
    def validate_url_safety(
        cls,
        url: str,
        allowed_domains: list[str] | None = None,
        max_redirects: int | None = None,
    ) -> tuple[str, str]:
        """
        Validates a URL and any redirect chain it produces, ensuring every
        hop is checked for internal/private IPs before it is requested.

        Returns:
            A tuple of (final_validated_url, pinned_ip).
        """
        if max_redirects is None:
            max_redirects = cls.MAX_REDIRECT_DEPTH

        cls.validate_webhook_url(url, allowed_domains=allowed_domains)
        current_url = url
        pinned_ip = cls._resolve_hostname(urllib.parse.urlparse(current_url).hostname)

        for _ in range(max_redirects):
            next_url = cls._check_redirect_depth(current_url, allowed_domains)
            if next_url is None:
                break
            current_url = next_url
            pinned_ip = cls._resolve_hostname(
                urllib.parse.urlparse(current_url).hostname
            )

        return current_url, pinned_ip

    @classmethod
    def validate_url_safety(
        cls,
        url: str,
        allowed_domains: list[str] | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 5.0,
    ) -> Tuple[str, str]:
        """
        Validates URL safety against SSRF attacks, verifies host resolution,
        issues an HTTP validation HEAD request using the application User-Agent header,
        and returns the validated URL alongside its pinned IP address.

        Args:
            url: Target URL to validate.
            allowed_domains: Optional domain whitelist.
            user_agent: Custom User-Agent header string.
            timeout: Request timeout in seconds.

        Returns:
            Tuple of (validated_url, pinned_ip).
        """
        cls.validate_webhook_url(
            url, allowed_domains=allowed_domains, user_agent=user_agent
        )
        parsed = urllib.parse.urlparse(url)
        ip_str = cls._resolve_hostname(parsed.hostname)
        return url, ip_str
