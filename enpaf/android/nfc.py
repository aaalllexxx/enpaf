"""ENPAF Android — NFC module (read / write every record type / lock)."""

from enpaf.android.manager import Manager


class NfcManager(Manager):
    NAME = "nfc"
    _ALLOWED = {
        "status", "read", "write_text", "write_uri", "write_app", "write_mime",
        "write_wifi", "write_contact", "write_records", "arm_write",
        "cancel_write", "make_readonly",
    }

    def status(self, **_): return self._api.get_nfc()
    def read(self, **_): return self._api.nfc_read()
    def write_text(self, **kw): return self._api.nfc_write_text(**kw)
    def write_uri(self, **kw): return self._api.nfc_write_uri(**kw)
    def write_app(self, **kw): return self._api.nfc_write_app(**kw)
    def write_mime(self, **kw): return self._api.nfc_write_mime(**kw)
    def write_wifi(self, **kw): return self._api.nfc_write_wifi(**kw)
    def write_contact(self, **kw): return self._api.nfc_write_contact(**kw)
    def write_records(self, **kw): return self._api.nfc_write_records(**kw)
    def arm_write(self, **kw): return self._api.nfc_arm_write(**kw)
    def cancel_write(self, **_): return self._api.nfc_cancel_write()
    def make_readonly(self, **kw): return self._api.nfc_make_readonly(**kw)
