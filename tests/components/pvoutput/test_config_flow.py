"""Tests for the PVOutput config flow."""

from unittest.mock import AsyncMock, MagicMock

from pvo import PVOutputAuthenticationError, PVOutputConnectionError

from homeassistant.components.pvoutput.const import CONF_SYSTEM_ID, DOMAIN
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_REAUTH, SOURCE_USER
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)

from tests.common import MockConfigEntry


async def test_full_user_flow(
    hass: HomeAssistant,
    mock_pvoutput_config_flow: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the full user configuration flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") == RESULT_TYPE_FORM
    assert result.get("step_id") == SOURCE_USER
    assert "flow_id" in result

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYSTEM_ID: 12345,
            CONF_API_KEY: "tadaaa",
        },
    )

    assert result2.get("type") == RESULT_TYPE_CREATE_ENTRY
    assert result2.get("title") == "12345"
    assert result2.get("data") == {
        CONF_SYSTEM_ID: 12345,
        CONF_API_KEY: "tadaaa",
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pvoutput_config_flow.status.mock_calls) == 1


async def test_full_flow_with_authentication_error(
    hass: HomeAssistant,
    mock_pvoutput_config_flow: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the full user configuration flow with incorrect API key.

    This tests tests a full config flow, with a case the user enters an invalid
    PVOutput API key, but recovers by entering the correct one.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") == RESULT_TYPE_FORM
    assert result.get("step_id") == SOURCE_USER
    assert "flow_id" in result

    mock_pvoutput_config_flow.status.side_effect = PVOutputAuthenticationError
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYSTEM_ID: 12345,
            CONF_API_KEY: "invalid",
        },
    )

    assert result2.get("type") == RESULT_TYPE_FORM
    assert result2.get("step_id") == SOURCE_USER
    assert result2.get("errors") == {"base": "invalid_auth"}
    assert "flow_id" in result2

    assert len(mock_setup_entry.mock_calls) == 0
    assert len(mock_pvoutput_config_flow.status.mock_calls) == 1

    mock_pvoutput_config_flow.status.side_effect = None
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={
            CONF_SYSTEM_ID: 12345,
            CONF_API_KEY: "tadaaa",
        },
    )

    assert result3.get("type") == RESULT_TYPE_CREATE_ENTRY
    assert result3.get("title") == "12345"
    assert result3.get("data") == {
        CONF_SYSTEM_ID: 12345,
        CONF_API_KEY: "tadaaa",
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pvoutput_config_flow.status.mock_calls) == 2


async def test_connection_error(
    hass: HomeAssistant, mock_pvoutput_config_flow: MagicMock
) -> None:
    """Test API connection error."""
    mock_pvoutput_config_flow.status.side_effect = PVOutputConnectionError

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_SYSTEM_ID: 12345,
            CONF_API_KEY: "tadaaa",
        },
    )

    assert result.get("type") == RESULT_TYPE_FORM
    assert result.get("errors") == {"base": "cannot_connect"}

    assert len(mock_pvoutput_config_flow.status.mock_calls) == 1


async def test_already_configured(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_pvoutput_config_flow: MagicMock,
) -> None:
    """Test we abort if the PVOutput system is already configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert "flow_id" in result

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYSTEM_ID: 12345,
            CONF_API_KEY: "tadaaa",
        },
    )

    assert result2.get("type") == RESULT_TYPE_ABORT
    assert result2.get("reason") == "already_configured"


async def test_import_flow(
    hass: HomeAssistant,
    mock_pvoutput_config_flow: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the import configuration flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={
            CONF_SYSTEM_ID: 1337,
            CONF_API_KEY: "tadaaa",
            CONF_NAME: "Test",
        },
    )

    assert result.get("type") == RESULT_TYPE_CREATE_ENTRY
    assert result.get("title") == "Test"
    assert result.get("data") == {
        CONF_SYSTEM_ID: 1337,
        CONF_API_KEY: "tadaaa",
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pvoutput_config_flow.status.mock_calls) == 1


async def test_reauth_flow(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_pvoutput_config_flow: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the reauthentication configuration flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_REAUTH,
            "unique_id": mock_config_entry.unique_id,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )
    assert result.get("type") == RESULT_TYPE_FORM
    assert result.get("step_id") == "reauth_confirm"
    assert "flow_id" in result

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "some_new_key"},
    )
    await hass.async_block_till_done()

    assert result2.get("type") == RESULT_TYPE_ABORT
    assert result2.get("reason") == "reauth_successful"
    assert mock_config_entry.data == {
        CONF_SYSTEM_ID: 12345,
        CONF_API_KEY: "some_new_key",
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pvoutput_config_flow.status.mock_calls) == 1


async def test_reauth_with_authentication_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_pvoutput_config_flow: MagicMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the reauthentication configuration flow with an authentication error.

    This tests tests a reauth flow, with a case the user enters an invalid
    API key, but recover by entering the correct one.
    """
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_REAUTH,
            "unique_id": mock_config_entry.unique_id,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )
    assert result.get("type") == RESULT_TYPE_FORM
    assert result.get("step_id") == "reauth_confirm"
    assert "flow_id" in result

    mock_pvoutput_config_flow.status.side_effect = PVOutputAuthenticationError
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "invalid_key"},
    )
    await hass.async_block_till_done()

    assert result2.get("type") == RESULT_TYPE_FORM
    assert result2.get("step_id") == "reauth_confirm"
    assert result2.get("errors") == {"base": "invalid_auth"}
    assert "flow_id" in result2

    assert len(mock_setup_entry.mock_calls) == 0
    assert len(mock_pvoutput_config_flow.status.mock_calls) == 1

    mock_pvoutput_config_flow.status.side_effect = None
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={CONF_API_KEY: "valid_key"},
    )
    await hass.async_block_till_done()

    assert result3.get("type") == RESULT_TYPE_ABORT
    assert result3.get("reason") == "reauth_successful"
    assert mock_config_entry.data == {
        CONF_SYSTEM_ID: 12345,
        CONF_API_KEY: "valid_key",
    }

    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pvoutput_config_flow.status.mock_calls) == 2


async def test_reauth_api_error(
    hass: HomeAssistant,
    mock_pvoutput_config_flow: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test API error during reauthentication."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_REAUTH,
            "unique_id": mock_config_entry.unique_id,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )
    assert result.get("type") == RESULT_TYPE_FORM
    assert result.get("step_id") == "reauth_confirm"
    assert "flow_id" in result

    mock_pvoutput_config_flow.status.side_effect = PVOutputConnectionError
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "some_new_key"},
    )
    await hass.async_block_till_done()

    assert result2.get("type") == RESULT_TYPE_FORM
    assert result2.get("step_id") == "reauth_confirm"
    assert result2.get("errors") == {"base": "cannot_connect"}
