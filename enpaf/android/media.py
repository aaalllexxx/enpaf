"""
ENPAF Android — Media (Camera, Gallery, Microphone)
Handles camera capture, video recording, gallery picks, and audio recording.

No Android imports at module top level — everything is imported lazily.
"""
import logging
import threading
import time

from enpaf.android.manager import Manager

logger = logging.getLogger("enpaf.media")


class MediaManager(Manager):
    NAME = "media"
    _ALLOWED = {"take_picture", "record_video", "pick_media", "record_audio"}

    def __init__(self, app=None):
        super().__init__(app)

    def take_picture(self, **_) -> dict:
        """Open the system camera app, take a photo, return its content:// URI."""
        if not self._is_android:
            return {"available": False, "dev": True, "note": "desktop stub"}
        try:
            from android.content import Intent
            from android.provider import MediaStore

            intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
            activity = self._app.api._activity
            if activity is None:
                return {"ok": False, "error": "no Activity"}

            ev = threading.Event()
            result = {"ok": False}

            def on_result(payload):
                if payload.get("request_code") == 2001:
                    self._app.events.off("activity_result", on_result)
                    if payload.get("result_code") == -1:  # RESULT_OK
                        data = payload.get("data")
                        if data and data.getData():
                            result["uri"] = str(data.getData())
                        result["ok"] = True
                    ev.set()

            self._app.events.on("activity_result", on_result)
            # Use Java helper — runs startActivityForResult on UI thread
            activity.launchForResult(intent, 2001)
            ev.wait(120)
            return result
        except Exception as e:
            logger.error(f"take_picture error: {e}")
            return {"ok": False, "error": str(e)}

    def record_video(self, **_) -> dict:
        """Open the system camera in video mode, record, return URI."""
        if not self._is_android:
            return {"available": False, "dev": True, "note": "desktop stub"}
        try:
            from android.content import Intent
            from android.provider import MediaStore

            intent = Intent(MediaStore.ACTION_VIDEO_CAPTURE)
            activity = self._app.api._activity
            if activity is None:
                return {"ok": False, "error": "no Activity"}

            ev = threading.Event()
            result = {"ok": False}

            def on_result(payload):
                if payload.get("request_code") == 2003:
                    self._app.events.off("activity_result", on_result)
                    if payload.get("result_code") == -1:
                        data = payload.get("data")
                        if data and data.getData():
                            result["uri"] = str(data.getData())
                        result["ok"] = True
                    ev.set()

            self._app.events.on("activity_result", on_result)
            activity.launchForResult(intent, 2003)
            ev.wait(300)
            return result
        except Exception as e:
            logger.error(f"record_video error: {e}")
            return {"ok": False, "error": str(e)}

    def pick_media(self, media_type="image", **_) -> dict:
        """Open gallery / file picker and return the chosen media URI."""
        if not self._is_android:
            return {"available": False, "dev": True, "note": "desktop stub"}
        try:
            from android.content import Intent

            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType("video/*" if media_type == "video" else "image/*")

            activity = self._app.api._activity
            if activity is None:
                return {"ok": False, "error": "no Activity"}

            ev = threading.Event()
            result = {"ok": False}

            def on_result(payload):
                if payload.get("request_code") == 2002:
                    self._app.events.off("activity_result", on_result)
                    if payload.get("result_code") == -1:
                        data = payload.get("data")
                        if data and data.getData():
                            result["uri"] = str(data.getData())
                            result["ok"] = True
                    ev.set()

            self._app.events.on("activity_result", on_result)
            activity.launchForResult(intent, 2002)
            ev.wait(120)
            return result
        except Exception as e:
            logger.error(f"pick_media error: {e}")
            return {"ok": False, "error": str(e)}

    def record_audio(self, duration_sec=5, **_) -> dict:
        """Record audio from the microphone for duration_sec seconds."""
        if not self._is_android:
            return {"ok": True, "dev": True, "note": "desktop stub"}
        try:
            import os
            from android.media import MediaRecorder

            data_dir = os.environ.get("ENPAF_DATA_DIR", "/data/local/tmp")
            out = os.path.join(data_dir, "enpaf_audio_record.3gp")

            recorder = MediaRecorder()
            recorder.setAudioSource(MediaRecorder.AudioSource.MIC)
            recorder.setOutputFormat(MediaRecorder.OutputFormat.THREE_GPP)
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AMR_NB)
            recorder.setOutputFile(out)

            recorder.prepare()
            recorder.start()
            time.sleep(max(0.5, float(duration_sec)))
            recorder.stop()
            recorder.release()
            return {"ok": True, "path": out}
        except Exception as e:
            logger.error(f"record_audio error: {e}")
            return {"ok": False, "error": str(e)}
