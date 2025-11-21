
import tkinter as tk
from tkinter import Canvas
import threading
import time
import ctypes
import win32gui
import win32con
import win32api
import winsound
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, ISimpleAudioVolume
import pythoncom

class HIDResponse:

    def __init__(self):
        self.screen_width = win32api.GetSystemMetrics(0)
        self.screen_height = win32api.GetSystemMetrics(1)
        self.input_blocked = False
        self.original_audio_states = {}  # Store original audio states

    # IMPROVED INPUT BLOCKING WITH MULTIPLE METHODS
    def _block_input(self):
        """Block all keyboard and mouse input using multiple methods"""
        try:
            # Method 1: Windows BlockInput API
            ctypes.windll.user32.BlockInput(True)
            self.input_blocked = True
            print("✓ Input blocked via BlockInput API")
        except Exception as e:
            print(f"✗ BlockInput failed: {e}")

    def _unblock_input(self):
        """Unblock all keyboard and mouse input"""
        try:
            if self.input_blocked:
                ctypes.windll.user32.BlockInput(False)
                self.input_blocked = False
                print("✓ Input unblocked")
        except Exception as e:
            print(f"✗ UnblockInput failed: {e}")

    # TO MINIMIZE ALL THE CURRENTLY RUNNING APPLICATION WINDOWS
    def _minimize_all_windows(self):
        try:
            shell = win32gui.FindWindow("Shell_TrayWnd", None)
            win32gui.SendMessage(shell, win32con.WM_COMMAND, 419, 0)
            print("✓ All windows minimized")
        except Exception as e:
            print(f"✗ Minimize windows failed: {e}")

    # IMPROVED INPUT BLOCKING WITH BETTER ERROR HANDLING
    def disable_inputs_for(self, duration):
        """Block all input devices for specified duration with retry logic"""
        def block_temporarily():
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"Attempt {attempt + 1} to block input for {duration} seconds...")
                    self._block_input()
                    
                    # Verify blocking worked
                    time.sleep(0.5)
                    if self.input_blocked:
                        print(f"✓ Input successfully blocked for {duration} seconds")
                        time.sleep(duration)
                        break
                    else:
                        print(f"✗ Blocking attempt {attempt + 1} failed")
                        if attempt < max_retries - 1:
                            time.sleep(1)  # Wait before retry
                except Exception as e:
                    print(f"✗ Blocking error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
            else:
                print("✗ All blocking attempts failed")
            
            # Always ensure input is unblocked
            self._unblock_input()

        threading.Thread(target=block_temporarily, daemon=True).start()

    # -------------------------------
    # AUDIO CONTROL - FIXED VERSION
    # -------------------------------
    def _pause_media_and_play_alert(self, duration):
        """Pause media and play alert sound with proper COM initialization and restoration"""
        def audio_control_worker(duration):
            pythoncom.CoInitialize()
            
            try:
                print("🎵 Controlling audio...")
                
                # SET VOLUME TO 70%
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
                original_volume = volume.GetMasterVolumeLevelScalar()
                volume.SetMasterVolumeLevelScalar(0.7, None)
                print(f"✓ Volume set to 70% (was {original_volume:.2f})")

                # MUTE ALL AUDIO SESSIONS AND STORE ORIGINAL STATES
                sessions = AudioUtilities.GetAllSessions()
                self.original_audio_states.clear()  # Clear previous states
                muted_count = 0
                
                for session in sessions:
                    try:
                        if session.Process:
                            process_name = session.Process.name() if session.Process else "Unknown"
                            # Don't mute system processes to avoid issues
                            if process_name not in ("explorer.exe", "System", "svchost.exe"):
                                audio = session._ctl.QueryInterface(ISimpleAudioVolume)
                                original_mute = audio.GetMute()
                                original_volume_level = audio.GetMasterVolume()
                                
                                # Store both mute state and volume level
                                self.original_audio_states[session] = {
                                    'mute': original_mute,
                                    'volume': original_volume_level,
                                    'process': process_name
                                }
                                
                                audio.SetMute(1, None)  # mute
                                muted_count += 1
                                print(f"  - Muted {process_name} (was muted: {original_mute})")
                    except Exception as e:
                        print(f"  - Error processing session {process_name}: {e}")
                        continue

                print(f"✓ Muted {muted_count} audio sessions")

                # PLAY ALERT BEEP
                end_time = time.time() + duration
                beep_count = 0
                while time.time() < end_time:
                    winsound.Beep(1000, 500)  # 1000 Hz, 500 ms
                    beep_count += 1
                    time.sleep(0.5)

                print(f"✓ Played {beep_count} alert beeps")

                # RESTORE ORIGINAL AUDIO STATES
                self._restore_audio_states()
                        
            except Exception as e:
                print(f"✗ Audio control error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                pythoncom.CoUninitialize()

        # Start audio control in a separate thread
        audio_thread = threading.Thread(target=audio_control_worker, args=(duration,), daemon=True)
        audio_thread.start()

    def _restore_audio_states(self):
        """Restore original audio states for all sessions"""
        try:
            print("🔊 Restoring audio states...")
            restored_count = 0
            
            # Get current sessions to match with stored states
            current_sessions = AudioUtilities.GetAllSessions()
            
            for session in current_sessions:
                try:
                    if session.Process:
                        process_name = session.Process.name() if session.Process else "Unknown"
                        
                        # Find matching original state
                        original_state = None
                        for orig_session, state in self.original_audio_states.items():
                            if (orig_session.Process and 
                                orig_session.Process.name() == process_name):
                                original_state = state
                                break
                        
                        if original_state:
                            audio = session._ctl.QueryInterface(ISimpleAudioVolume)
                            # Restore mute state
                            audio.SetMute(original_state['mute'], None)
                            # Restore volume level
                            audio.SetMasterVolume(original_state['volume'], None)
                            restored_count += 1
                            print(f"  - Restored {process_name} (mute: {original_state['mute']}, volume: {original_state['volume']:.2f})")
                            
                except Exception as e:
                    print(f"  - Error restoring session {process_name}: {e}")
                    continue
            
            print(f"✓ Restored {restored_count} audio sessions")
            
            # If we couldn't restore specific sessions, try a general unmute
            if restored_count == 0:
                self._force_unmute_all()
                
        except Exception as e:
            print(f"✗ Audio restoration error: {e}")
            # Fallback: force unmute all
            self._force_unmute_all()

    def _force_unmute_all(self):
        """Force unmute all audio sessions as a fallback"""
        try:
            print("🔄 Force unmuting all audio sessions...")
            sessions = AudioUtilities.GetAllSessions()
            unmuted_count = 0
            
            for session in sessions:
                try:
                    if session.Process:
                        audio = session._ctl.QueryInterface(ISimpleAudioVolume)
                        audio.SetMute(0, None)  # Unmute
                        unmuted_count += 1
                except Exception:
                    continue
            
            print(f"✓ Force unmuted {unmuted_count} sessions")
        except Exception as e:
            print(f"✗ Force unmute failed: {e}")

    # -------------------------------
    # UI SECTION
    # -------------------------------
    def _create_alert_window(self, device_name="Unknown", duration=30):
        """Creates and shows a modern opaque alert box with dimmed background."""
        
        print(f"🖥️ Creating alert window for {duration} seconds...")

        # --- Dim Background Overlay ---
        overlay = tk.Tk()
        overlay.title("Background Overlay")
        overlay.attributes('-fullscreen', True)
        overlay.attributes('-topmost', True)
        overlay.overrideredirect(True)
        overlay.configure(bg='black')
        overlay.attributes('-alpha', 0.45)  # semi-transparent dim layer

        # Prevent closing or alt-tabbing
        overlay.bind("<Alt-F4>", lambda e: "break")
        overlay.protocol("WM_DELETE_WINDOW", lambda: None)
        overlay.bind("<Escape>", lambda e: "break")

        # --- Opaque Message Window ---
        msg_window = tk.Toplevel(overlay)
        msg_window.title("HID ALERT")
        msg_window.geometry("550x250")
        msg_window.resizable(False, False)
        msg_window.overrideredirect(True)
        msg_window.attributes('-topmost', True)

        # Centering
        x = (self.screen_width // 2) - 275
        y = (self.screen_height // 2) - 125
        msg_window.geometry(f"550x250+{x}+{y}")

        # --- Gradient Background ---
        gradient = Canvas(msg_window, width=550, height=250, highlightthickness=0, bd=0)
        gradient.pack(fill="both", expand=True)
        for i in range(250):
            r = 255
            g = int(70 + (i / 250) * 100)
            b = 0
            gradient.create_line(0, i, 550, i, fill=f"#{r:02x}{g:02x}{b:02x}")

        # ADDING TEXT LABEL ON TOP OF GRADIENT WINDOW
        gradient.create_text(
            275, 70,
            text="⚠️  MALICIOUS HID DEVICE DETECTED  ⚠️",
            fill="white", font=("Segoe UI Semibold", 17, "bold"), anchor="center"
        )
        gradient.create_text(
            275, 115,
            text=f"Device Name: {device_name if device_name else 'Unknown'}",
            fill="white", font=("Consolas", 13, "bold"), anchor="center"
        )
        gradient.create_text(
            275, 150,
            text="Remove all connected USB devices immediately!",
            fill="#fff3cd", font=("Consolas", 12), anchor="center"
        )
        countdown_text = gradient.create_text(
            275, 200,
            text=f"Closing in {duration} seconds...",
            fill="white", font=("Consolas", 14, "bold"), anchor="center"
        )

        # Fix Z-Order 
        overlay.update_idletasks()
        msg_window.lift(overlay)
        msg_window.focus_force()
        win32gui.SetWindowPos(
            msg_window.winfo_id(),
            win32con.HWND_TOPMOST,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
        )

        print("✓ Alert window created and positioned")

        # COUNTDOWN LOGIC
        def update_countdown():
            remaining = duration
            while remaining > 0:
                try:
                    gradient.itemconfig(countdown_text, text=f"Closing in {remaining} seconds...")
                    overlay.update()
                    time.sleep(1)
                    remaining -= 1
                except Exception as e:
                    print(f"✗ Countdown error: {e}")
                    break
            
            try:
                msg_window.destroy()
                overlay.destroy()
                print("✓ Alert window closed")
            except Exception as e:
                print(f"✗ Window destruction error: {e}")

        countdown_thread = threading.Thread(target=update_countdown, daemon=True)
        countdown_thread.start()
        
        # Start the GUI
        try:
            overlay.mainloop()
        except Exception as e:
            print(f"✗ GUI error: {e}")

    # MAIN CALLING FUNCTION
    def show_alert(self, device_name="Unknown", duration=30):
        """Main alert trigger with input blocking and audio alert."""
        print(f"🚨 ALERT TRIGGERED: {device_name}")
        
        # Execute all response actions
        self._minimize_all_windows()
        self.disable_inputs_for(duration)
        self._pause_media_and_play_alert(duration)
        self._create_alert_window(device_name, duration)

# TEST
if __name__ == "__main__":
    response = HIDResponse()
    response.show_alert("Rubber Ducky V3", duration=15)
