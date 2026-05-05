"""Shared polite HTTP client utilities for scrapers."""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_USER_AGENT = "CodeCollectiveBot/1.0 (+https://github.com/juliancoy/CodeCollective)"
DEFAULT_TIMEOUT = 30
DEFAULT_MIN_INTERVAL_SECONDS = 1.0
DEFAULT_ROBOTS_TTL_SECONDS = 3600
HOST_POLICY_PATH = Path(
    os.environ.get("CODECOLLECTIVE_HOST_POLICY_PATH", "data/scrape_host_policy.json")
)

_host_lock = threading.Lock()
_last_request_by_host: dict[str, float] = {}
_host_policy_cache: dict[str, object] | None = None
_robots_cache: dict[str, tuple[float, urllib.robotparser.RobotFileParser | None]] = {}


def _load_host_policy() -> dict[str, object]:
    global _host_policy_cache
    if _host_policy_cache is not None:
        return _host_policy_cache
    try:
        payload = json.loads(HOST_POLICY_PATH.read_text())
        if isinstance(payload, dict):
            _host_policy_cache = payload
            return payload
    except Exception:
        pass
    _host_policy_cache = {"defaults": {"min_interval_seconds": DEFAULT_MIN_INTERVAL_SECONDS}, "hosts": {}}
    return _host_policy_cache


def _match_host_policy(host: str) -> dict[str, object]:
    policy = _load_host_policy()
    defaults = policy.get("defaults") if isinstance(policy, dict) else {}
    hosts = policy.get("hosts") if isinstance(policy, dict) else {}
    if not isinstance(defaults, dict):
        defaults = {}
    if not isinstance(hosts, dict):
        hosts = {}

    matched = dict(defaults)
    if host in hosts and isinstance(hosts[host], dict):
        matched.update(hosts[host])
    else:
        for suffix, values in hosts.items():
            if not isinstance(values, dict):
                continue
            suffix = str(suffix).lstrip(".")
            if host == suffix or host.endswith(f".{suffix}"):
                matched.update(values)
                break
    return matched


def _pace_host(url: str, min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS) -> None:
    host = (urlsplit(url).hostname or "").lower()
    if not host:
        return
    with _host_lock:
        now = time.monotonic()
        last = _last_request_by_host.get(host)
        if last is not None:
            wait = min_interval_seconds - (now - last)
            if wait > 0:
                time.sleep(wait)
        _last_request_by_host[host] = time.monotonic()


def _load_robots_parser(
    session: requests.Session,
    scheme: str,
    host: str,
    *,
    timeout: int,
    ttl_seconds: int,
) -> urllib.robotparser.RobotFileParser | None:
    now = time.time()
    cached = _robots_cache.get(host)
    if cached and (now - cached[0] < ttl_seconds):
        return cached[1]

    robots_url = f"{scheme}://{host}/robots.txt"
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        resp = session.get(robots_url, timeout=timeout)
        if resp.status_code >= 400:
            _robots_cache[host] = (now, None)
            return None
        parser.parse((resp.text or "").splitlines())
        _robots_cache[host] = (now, parser)
        return parser
    except Exception:
        _robots_cache[host] = (now, None)
        return None


def _enforce_robots(
    session: requests.Session,
    url: str,
    *,
    timeout: int,
    user_agent: str,
    robots_ttl_seconds: int = DEFAULT_ROBOTS_TTL_SECONDS,
) -> None:
    parsed = urlsplit(url)
    scheme = parsed.scheme or "https"
    host = (parsed.hostname or "").lower()
    if not host:
        return
    policy = _match_host_policy(host)
    robots_enabled = bool(policy.get("robots_preflight", True))
    if not robots_enabled:
        return

    parser = _load_robots_parser(
        session=session,
        scheme=scheme,
        host=host,
        timeout=min(timeout, 10),
        ttl_seconds=robots_ttl_seconds,
    )
    if parser is None:
        return
    if not parser.can_fetch(user_agent, url):
        raise PermissionError(f"Blocked by robots.txt policy: {url}")


def build_session(
    user_agent: str = DEFAULT_USER_AGENT,
    retries: int = 3,
    backoff_factor: float = 1.0,
) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
    )
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def polite_get(
    session: requests.Session,
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
    respect_robots: bool = True,
    **kwargs,
) -> requests.Response:
    host = (urlsplit(url).hostname or "").lower()
    policy = _match_host_policy(host) if host else {}
    effective_interval = float(policy.get("min_interval_seconds", min_interval_seconds))
    if policy.get("disabled", False):
        raise PermissionError(f"Host disabled by scrape policy: {host}")

    if respect_robots:
        _enforce_robots(
            session,
            url,
            timeout=timeout,
            user_agent=str(session.headers.get("User-Agent") or DEFAULT_USER_AGENT),
        )

    _pace_host(url, min_interval_seconds=effective_interval)
    return session.get(url, timeout=timeout, **kwargs)
