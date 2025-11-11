"""Badge automation package.

Provides background monitors that detect user activity and awards badges,
plus helper functions to start/stop the shared scheduler.
"""

from .runtime import start_badge_automation, stop_badge_automation

__all__ = ["start_badge_automation", "stop_badge_automation"]

