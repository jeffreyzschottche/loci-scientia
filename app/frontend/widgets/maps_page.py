"""Compatibility wrapper for the map widget.

The original implementation lives in ``app.maps.maps_page`` but the new UI
expects it under ``app.frontend.widgets``. Re-export the class so both import
paths keep working.
"""

from app.maps.maps_page import MapsPage as MapsPage  # noqa: F401


__all__ = ["MapsPage"]
