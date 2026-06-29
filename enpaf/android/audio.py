"""ENPAF Android — Audio module (microphone level)."""

from enpaf.android.manager import Manager


class AudioManager(Manager):
    NAME = "audio"
    _ALLOWED = {"level"}

    def level(self, **kw):
        """Peak microphone amplitude {amplitude, db}. Needs RECORD_AUDIO."""
        return self._api.get_audio_level(**kw)
