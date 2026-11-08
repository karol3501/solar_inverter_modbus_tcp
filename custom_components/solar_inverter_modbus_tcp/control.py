"""Immediate feedback for controls waiting for Modbus communication."""

import asyncio
from functools import wraps


def control_state_attributes(entity):
    """Return confirmation information for the latest requested operation."""
    return {
        "write_status": getattr(entity, "_write_status", "idle"),
        "write_error": getattr(entity, "_write_error", None),
    }


def optimistic_control(method):
    """Show the latest requested value until its operation finishes."""
    @wraps(method)
    async def async_set_value(self, value):
        pending = (object(), value)
        self._pending_control_value = pending
        self._write_status = "pending"
        self._write_error = None
        self.async_write_ha_state()
        try:
            result = await method(self, value)
        except asyncio.CancelledError:
            if self._pending_control_value is pending:
                self._write_status = "cancelled"
            raise
        except Exception as err:
            if self._pending_control_value is pending:
                self._write_status = "error"
                self._write_error = str(err)
            raise
        else:
            if self._pending_control_value is pending:
                self._write_status = "confirmed"
            return result
        finally:
            if self._pending_control_value is pending:
                self._pending_control_value = None
                self.async_write_ha_state()
            self.coordinator.async_update_listeners()

    return async_set_value
