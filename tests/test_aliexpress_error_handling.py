"""Test AliExpress connector error handling for IncompleteSignature and other API errors."""
from typing import cast
import pytest
from pricerecon.connectors.aliexpress import AliExpressConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus
import httpx


@pytest.mark.asyncio
async def test_aliexpress_connector_raises_on_incomplete_signature_error() -> None:
    """Test that IncompleteSignature errors are surfaced instead of silently returning empty results."""
    
    class DummyResponse:
        def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
            self._payload = payload
            self.status_code = status_code
            self.headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "boom",
                    request=httpx.Request("POST", "https://example.test"),
                    response=httpx.Response(self.status_code),
                )

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyClient:
        async def post(
            self, url: str, json: object = None, headers: object = None, data: object = None
        ) -> DummyResponse:
            # Return IncompleteSignature error
            return DummyResponse(
                {
                    "error_response": {
                        "code": "IncompleteSignature",
                        "msg": "The request signature does not conform to platform standards"
                    }
                }
            )

        async def get(self, url: str, params: object = None, headers: object = None, timeout: object = None) -> DummyResponse:
            # Return empty response for Brave search (so we can test affiliate lane in isolation)
            return DummyResponse({"web": {"results": []}})

        async def aclose(self) -> None:
            return None

    connector = AliExpressConnector(
        {
            "app_key": "test-key",
            "app_secret": "test-secret",
            "affiliate_currency": "GBP",
        },
        http_client=cast(httpx.AsyncClient, DummyClient()),
    )

    # Call _affiliate_search directly to test error handling
    with pytest.raises(ConnectorDegradedError) as exc_info:
        await connector._affiliate_search("test query", {})

    error = exc_info.value
    assert error.status == ConnectorStatus.auth_failed
    assert "IncompleteSignature" in error.message
    assert "signature does not conform" in error.message
    assert error.detail is not None
    assert "error_response" in error.detail
    assert error.detail["error_response"]["code"] == "IncompleteSignature"

    await connector.cleanup()


@pytest.mark.asyncio
async def test_aliexpress_connector_raises_on_other_api_errors() -> None:
    """Test that other error_response errors are surfaced as unknown_error."""
    
    class DummyResponse:
        def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
            self._payload = payload
            self.status_code = status_code
            self.headers: dict[str, str] = {}

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, object]:
            return self._payload

    class DummyClient:
        async def post(
            self, url: str, json: object = None, headers: object = None, data: object = None
        ) -> DummyResponse:
            return DummyResponse(
                {
                    "error_response": {
                        "code": "InvalidParameter",
                        "msg": "Invalid parameter value"
                    }
                }
            )

        async def get(self, url: str, params: object = None, headers: object = None, timeout: object = None) -> DummyResponse:
            return DummyResponse({"web": {"results": []}})

        async def aclose(self) -> None:
            return None

    connector = AliExpressConnector(
        {
            "app_key": "test-key",
            "app_secret": "test-secret",
            "affiliate_currency": "GBP",
        },
        http_client=cast(httpx.AsyncClient, DummyClient()),
    )

    # Call _affiliate_search directly to test error handling
    with pytest.raises(ConnectorDegradedError) as exc_info:
        await connector._affiliate_search("test query", {})

    error = exc_info.value
    assert error.status == ConnectorStatus.unknown_error
    assert "InvalidParameter" in error.message
    assert "Invalid parameter" in error.message

    await connector.cleanup()


@pytest.mark.asyncio
async def test_aliexpress_connector_extract_top_response_payload_with_error_response() -> None:
    """Test _extract_top_response_payload raises ConnectorDegradedError for error_response."""
    
    connector = AliExpressConnector(
        {
            "app_key": "test-key",
            "app_secret": "test-secret",
        }
    )

    # Test IncompleteSignature (auth_failed)
    with pytest.raises(ConnectorDegradedError) as exc_info:
        connector._extract_top_response_payload(
            {
                "error_response": {
                    "code": "IncompleteSignature",
                    "msg": "Signature error"
                }
            }
        )
    
    assert exc_info.value.status == ConnectorStatus.auth_failed
    assert "IncompleteSignature" in exc_info.value.message

    # Test other error codes (unknown_error)
    with pytest.raises(ConnectorDegradedError) as exc_info:
        connector._extract_top_response_payload(
            {
                "error_response": {
                    "code": "SomeOtherError",
                    "msg": "Other error"
                }
            }
        )
    
    assert exc_info.value.status == ConnectorStatus.unknown_error
    assert "SomeOtherError" in exc_info.value.message

    # Test valid response (should not raise)
    result = connector._extract_top_response_payload(
        {
            "aliexpress_affiliate_product_query_response": {
                "result": {
                    "items": [{"productId": "123"}]
                }
            }
        }
    )
    assert result == {"items": [{"productId": "123"}]}