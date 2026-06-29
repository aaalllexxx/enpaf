"""ENPAF Android — Notifications module (system notifications)."""

from enpaf.android.manager import Manager


class NotificationsManager(Manager):
    NAME = "notifications"
    _ALLOWED = {"notify"}

    def notify(self, title="", text="", notification_id=1,
               payload="", action="", image_base64=None, buttons=None, **_):
        """Show a system notification (supports image + action buttons)."""
        self._api.notify(title=title, text=text, notification_id=notification_id,
                         payload=payload, action=action,
                         image_base64=image_base64, buttons=buttons)
        return {"ok": True}
