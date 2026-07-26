"""Truthful states for connectors whose current upstream lanes are stale."""

import pytest

from pricerecon.connectors.aria import AriaConnector
from pricerecon.connectors.ccl import CclConnector
from pricerecon.connectors.ebuyer import EbuyerConnector
from pricerecon.connectors.ao import AOConnector
from pricerecon.connectors.status import ConnectorDegradedError, ConnectorStatus


@pytest.mark.parametrize(
    "connector_class, connector_id",
    [
        (AriaConnector, "aria"),
        (CclConnector, "ccl"),
        (EbuyerConnector, "ebuyer"),
        (AOConnector, "ao"),
    ],
)
@pytest.mark.asyncio
async def test_stale_connectors_fail_explicitly_as_disabled(
    connector_class: type, connector_id: str
):
    connector = connector_class()
    try:
        with pytest.raises(ConnectorDegradedError) as raised:
            await connector.search("RTX 5090")
    finally:
        await connector.cleanup()

    error = raised.value
    assert error.status is ConnectorStatus.disabled
    assert error.connector_id == connector_id
    assert error.detail and error.detail["reason"]
