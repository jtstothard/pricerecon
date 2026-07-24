"""Unit tests for browser_client: is_blocked() helper and BrowserSessionConfig env loading."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pricerecon.connectors.browser_client import (
    BrowserClient,
    BrowserSessionConfig,
    CloakBrowserBridgeUnavailable,
    is_blocked,
    resolve_cloakbrowser_binary,
    run_cloakbrowser_bridge,
)

# ---------------------------------------------------------------------------
# is_blocked — detection signals
# ---------------------------------------------------------------------------


class TestIsBlocked:
    def test_clean_page_not_blocked(self) -> None:
        html = "<html><body><h1>Welcome</h1></body></html>"
        assert not is_blocked(html, "Welcome", 200)

    def test_http_403(self) -> None:
        assert is_blocked("<html></html>", "Forbidden", 403)

    def test_http_401(self) -> None:
        assert is_blocked("<html></html>", "Unauthorized", 401)

    def test_http_200_not_blocked_by_status(self) -> None:
        # Status alone is not enough
        assert not is_blocked("<html><body>ok</body></html>", "OK", 200)

    def test_cloudflare_cf_challenge(self) -> None:
        html = '<html><body class="cf-challenge">verify</body></html>'
        assert is_blocked(html, "Just a moment...", 200)

    def test_cloudflare_cf_turnstile(self) -> None:
        html = "<html><script src='cf-turnstile.js'></script></html>"
        assert is_blocked(html, "Check", 200)

    def test_cloudflare_challenge_platform(self) -> None:
        html = "<html><div id='challenge-platform'></div></html>"
        assert is_blocked(html, "Checking", 200)

    def test_cloudflare_jschl_answer(self) -> None:
        html = "<html><input name='jschl_answer' /></html>"
        assert is_blocked(html, "One moment", 200)

    def test_datadome(self) -> None:
        html = "<html><script>datadome.protection()</script></html>"
        assert is_blocked(html, "Checking your browser", 200)

    def test_error_page_title(self) -> None:
        html = "<html><body>Some error occurred</body></html>"
        assert is_blocked(html, "Error Page", 200)

    def test_error_page_title_case_insensitive(self) -> None:
        html = "<html><body>oops</body></html>"
        assert is_blocked(html, "ERROR PAGE", 200)

    def test_something_went_wrong(self) -> None:
        html = "<html><body>Something went wrong on our end. Please try again.</body></html>"
        assert is_blocked(html, "eBay", 200)

    def test_access_denied(self) -> None:
        html = "<html><body>Access denied. Contact support.</body></html>"
        assert is_blocked(html, "Error", 200)

    def test_you_have_been_blocked(self) -> None:
        html = "<html><body>You have been blocked from accessing this page.</body></html>"
        assert is_blocked(html, "Blocked", 200)

    def test_captcha(self) -> None:
        html = "<html><body>Please solve the CAPTCHA to continue.</body></html>"
        assert is_blocked(html, "Security check", 200)

    def test_verify_it(self) -> None:
        html = "<html><body>Please verify it to continue.</body></html>"
        assert is_blocked(html, "Verify", 200)

    def test_verify_you_are_human(self) -> None:
        html = "<html><body>Please verify you are human.</body></html>"
        assert is_blocked(html, "Check", 200)

    def test_are_you_a_robot(self) -> None:
        html = "<html><body>Are you a robot? Click to confirm.</body></html>"
        assert is_blocked(html, "Robot check", 200)

    def test_case_insensitive_html(self) -> None:
        html = "<html><body>CAPTCHA required</body></html>"
        assert is_blocked(html, "Security", 200)

    def test_ebay_real_results_page_has_s_item(self) -> None:
        """Real eBay results pages can contain 'captcha' in hidden elements.

        Callers should verify presence of s-item/srp-results rather than
        relying solely on is_blocked() to determine success.
        """
        html = (
            "<html><body>"
            # hidden captcha reference that appears in real pages
            "<script>window.__captchaEnabled=false;</script>"
            '<ul class="srp-results"><li class="s-item">RTX 4090</li></ul>'
            "</body></html>"
        )
        # is_blocked will return True due to 'captcha' in hidden script —
        # this is expected; callers should check for s-item as a positive signal.
        blocked = is_blocked(html, "Rtx 4090 for sale | eBay", 200)
        assert blocked is True, (
            "is_blocked flags 'captcha' even in real eBay pages; "
            "callers must check for s-item/srp-results as the success signal."
        )


# ---------------------------------------------------------------------------
# BrowserSessionConfig — env-var loading
# ---------------------------------------------------------------------------


class TestBrowserSessionConfigEnv:
    def test_defaults(self) -> None:
        cfg = BrowserSessionConfig()
        assert cfg.use_cloakbrowser is False
        assert cfg.cloakbrowser_fallback is True

    def test_env_use_cloakbrowser_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRICERECON_CLOAKBROWSER_USE", "true")
        cfg = BrowserSessionConfig()
        assert cfg.use_cloakbrowser is True

    def test_env_use_cloakbrowser_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRICERECON_CLOAKBROWSER_USE", "1")
        cfg = BrowserSessionConfig()
        assert cfg.use_cloakbrowser is True

    def test_env_use_cloakbrowser_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRICERECON_CLOAKBROWSER_USE", "false")
        cfg = BrowserSessionConfig(use_cloakbrowser=True)
        assert cfg.use_cloakbrowser is False

    def test_env_fallback_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRICERECON_CLOAKBROWSER_FALLBACK", "0")
        cfg = BrowserSessionConfig()
        assert cfg.cloakbrowser_fallback is False

    def test_env_fallback_true_overrides_field(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRICERECON_CLOAKBROWSER_FALLBACK", "true")
        cfg = BrowserSessionConfig(cloakbrowser_fallback=False)
        assert cfg.cloakbrowser_fallback is True

    def test_unknown_env_value_leaves_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRICERECON_CLOAKBROWSER_USE", "maybe")
        cfg = BrowserSessionConfig()
        # "maybe" is not a recognised truthy/falsy value — default unchanged
        assert cfg.use_cloakbrowser is False


# ---------------------------------------------------------------------------
# resolve_cloakbrowser_binary — path resolution
# ---------------------------------------------------------------------------


class TestResolveCloakbrowserBinary:
    def test_env_var_takes_priority(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        fake_chrome = tmp_path / "chrome"
        fake_chrome.touch()
        monkeypatch.setenv("PRICERECON_CLOAKBROWSER_CHROME", str(fake_chrome))
        result = resolve_cloakbrowser_binary()
        assert result == str(fake_chrome)

    def test_env_var_missing_file_falls_through(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRICERECON_CLOAKBROWSER_CHROME", "/does/not/exist/chrome")
        # Should fall through to glob — if no ~/.cloakbrowser, returns None
        with patch("glob.glob", return_value=[]):
            result = resolve_cloakbrowser_binary()
        assert result is None

    def test_glob_picks_highest_version(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("PRICERECON_CLOAKBROWSER_CHROME", raising=False)
        # Create fake versioned chrome binaries
        v1 = tmp_path / "chromium-145.0.0.0" / "chrome"
        v1.parent.mkdir()
        v1.touch()
        v2 = tmp_path / "chromium-146.0.7680.177.5" / "chrome"
        v2.parent.mkdir()
        v2.touch()

        candidates = [str(v1), str(v2)]
        with patch("glob.glob", return_value=candidates):
            result = resolve_cloakbrowser_binary()
        assert result == str(v2)

    def test_no_binary_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PRICERECON_CLOAKBROWSER_CHROME", raising=False)
        with patch("glob.glob", return_value=[]):
            result = resolve_cloakbrowser_binary()
        assert result is None


class _FakeStream:
    def __init__(self, data: bytes) -> None:
        self.data = data

    async def read(self, *_args: object) -> bytes:
        return self.data

    async def readline(self) -> bytes:
        return self.data

    def write(self, _data: bytes) -> None:
        return None

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        return None


class _FakeProcess:
    def __init__(self, stdout: bytes) -> None:
        self.stdout = _FakeStream(stdout)
        self.stdin = _FakeStream(b"")
        self.returncode: int | None = 0
        self.kill = MagicMock()
        self.wait = AsyncMock()


class _FakePage:
    def __init__(self, html: str, title: str) -> None:
        self.html, self.title_value = html, title

    def on(self, *_args: object) -> None:
        return None

    def set_default_navigation_timeout(self, _timeout: int) -> None:
        return None

    async def goto(self, *_args: object, **_kwargs: object) -> None:
        return None

    async def title(self) -> str:
        return self.title_value

    async def content(self) -> str:
        return self.html


class _FakeContext:
    def __init__(self, html: str, title: str) -> None:
        self.page = _FakePage(html, title)
        self.closed = False

    async def new_page(self) -> _FakePage:
        return self.page

    async def close(self) -> None:
        self.closed = True


class TestCloakBrowserBridge:
    async def test_protocol_returns_structured_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        process = _FakeProcess(
            b'{"status":200,"title":"eBay","html":"<li class=\\"s-item\\">x</li>",'
            b'"content":"x","blocked":false,"timing_ms":12}\n'
        )
        create = AsyncMock(return_value=process)
        monkeypatch.setattr("asyncio.create_subprocess_exec", create)

        result = await run_cloakbrowser_bridge("https://www.ebay.co.uk/sch/i.html?_nkw=x")

        assert result["status"] == 200
        assert result["title"] == "eBay"
        assert result["blocked"] is False
        assert create.await_args.args[0] == "node"
        assert create.await_args.args[1].endswith("tools/cloakbrowser-bridge/bridge.mjs")
        assert create.await_args.args[2] == "--stdio"

    async def test_timeout_kills_process_and_fails_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        process = _FakeProcess(b"")
        process.returncode = None
        create = AsyncMock(return_value=process)
        monkeypatch.setattr("asyncio.create_subprocess_exec", create)

        async def timeout(_awaitable: object, **_kwargs: object) -> None:
            # Simulate timeout by properly handling the coroutine
            # Close coroutine to avoid RuntimeWarning
            close_method = getattr(_awaitable, "close", None)
            if close_method is not None and callable(close_method):
                close_method()
            raise TimeoutError

        monkeypatch.setattr("asyncio.wait_for", timeout)
        result = await run_cloakbrowser_bridge("https://example.test", timeout_ms=10)

        assert result["blocked"] is True
        assert result["status"] == 0
        process.kill.assert_called_once()
        process.wait.assert_awaited_once()

    async def test_unavailable_runtime_fails_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def unavailable(*_args: object, **_kwargs: object) -> None:
            raise FileNotFoundError("node")

        monkeypatch.setattr("asyncio.create_subprocess_exec", unavailable)
        result = await run_cloakbrowser_bridge("https://example.test")

        assert result["blocked"] is True
        assert result["status"] == 0
        assert isinstance(result["error"], CloakBrowserBridgeUnavailable)

    async def test_bridge_is_selected_only_after_primary_block(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client = BrowserClient(config=BrowserSessionConfig(cloakbrowser_fallback=True))
        primary_context = _FakeContext("<html>Access denied</html>", "Access denied")
        client.start = AsyncMock()
        client.new_context = AsyncMock(return_value=primary_context)
        bridge = AsyncMock(
            return_value={
                "status": 200,
                "title": "eBay",
                "html": '<li class="s-item">x</li>',
                "content": "x",
                "blocked": False,
                "timing_ms": 10,
            }
        )
        monkeypatch.setattr("pricerecon.connectors.browser_client.run_cloakbrowser_bridge", bridge)

        result = await client.fetch_with_fallback("https://example.test", wait_ms=0)

        assert result["used_cloakbrowser"] is True
        bridge.assert_awaited_once()
