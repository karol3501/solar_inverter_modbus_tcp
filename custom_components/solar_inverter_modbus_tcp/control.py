"""Immediate feedback for controls waiting for Modbus communication."""

from functools import wraps


def optimistic_control(method):
    """Show the latest requested value until its operation finishes."""
    @wraps(method)
    async def async_set_value(self, value):
        pending = (object(), value)
        self._pending_control_value = pending
        self.async_write_ha_state()
        try:
            return await method(self, value)
        finally:
            if self._pending_control_value is pending:
                self._pending_control_value = None
                self.async_write_ha_state()

    return async_set_value
