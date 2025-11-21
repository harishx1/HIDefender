# restore_audio.py
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume

def restore_all_audio_sessions():
    """Unmutes all active media sessions to restore audio."""
    sessions = AudioUtilities.GetAllSessions()
    for session in sessions:
        try:
            if session.Process and session.Process.name() not in ("explorer.exe", "System"):
                audio = session._ctl.QueryInterface(ISimpleAudioVolume)
                audio.SetMute(0, None)  # unmute
        except Exception:
            continue

if __name__ == "__main__":
    restore_all_audio_sessions()
    print("All audio sessions restored.")
