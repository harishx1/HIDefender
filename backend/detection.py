
import time
import threading
from collections import deque
from pynput import keyboard
from pynput.keyboard import Key, Listener
import sys
import os
import pythoncom
import re

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from update_logs import UpdateLogs
from response import HIDResponse

class HIDDetector:
    def __init__(self):
        self.keystroke_buffer = deque(maxlen=1000)
        self.buffer_duration = 10
        self.keystroke_threshold = 100
        self.command_length_threshold = 200
        
        # EXPANDED Malicious keywords to detect in commands - INCLUDING URL PATTERNS
        self.malicious_keywords = [
            # URL and web patterns
            "http://", "https://", "www.", ".com", ".net", ".org", ".io", ".ru", ".cn",
            "youtu", "youtube", "fakeupdate", "bit.ly", "tinyurl", "shorturl",
            "pastebin", "github.io", "webhook", "download", "server", "payload",
            
            # System commands and scripts
            "powershell", "cmd", "command", "wget", "curl", "iwr", "invoke-webrequest",
            "iex", "invoke-expression", "downloadstring", "base64", "encodedcommand",
            "bitsadmin", "certutil", "regsvr32", "rundll32", "mshta", "msiexec",
            "schtasks", "wmic", "net user", "net localgroup", "add-mpreference",
            "set-mpreference", "disable-realtime", "disable-behavior", "exclusion",
            "remove-definition", "stop-service", "disable-service", "firewall",
            "netsh firewall", "netsh advfirewall", "sc config", "sc delete",
            "bcdedit", "bootconfig", "recovery", "safe boot", "wfp", "wf.msc",
            
            # Security bypass
            "defender", "securitycenter", "windefend", "mrt", "msascui", "mspaint",
            "taskmgr", "eventvwr", "compmgmt", "services.msc", "regedit", "gpedit",
            "control panel", "system32", "temp", "tmp", "appdata", "startup",
            "task scheduler", "group policy", "registry", "hkey", "runonce",
            "shell:startup", "startup folder", "scheduled task", "autostart",
            
            # Malware and persistence
            "persistence", "backdoor", "reverse shell", "bind shell", "listener",
            "payload", "metasploit", "meterpreter", "beacon", "implant", "cobalt strike",
            "empire", "poshc2", "brute", "password", "credential", "hash", "dump",
            "mimikatz", "kiwi", "sekurlsa", "logonpasswords", "lsass", "sam",
            "system", "security", "syskey", "protect", "bypass", "uac", "elevate",
            
            # Privilege escalation
            "privilege", "admin", "administrator", "nt authority", "system",
            "get-system", "psexec", "psexecsvc", "wmicexec", "smbexec", "atexec",
            "dcom", "wmi", "winrm", "remote", "pivot", "lateral", "domain", "ad",
            "active directory", "dc", "domain controller", "kerberos", "golden ticket",
            "silver ticket", "pass the ticket", "pass the hash", "over pass the hash",
            "kerberoasting", "asreproasting", "dcsync", "dcsyncing", "ntds", "dit",
            
            # System manipulation
            "vss", "volume shadow", "shadow copy", "ntdsutil", "vssadmin", "diskshadow",
            "comsvcs", "minidump", "procdump", "sqldumper", "rundump", "memory",
            "process dump", "crash dump", "hibernation", "pagefile", "swap", "cache",
            
            # Data theft
            "browser", "chrome", "firefox", "edge", "password", "cookie", "history",
            "bookmark", "credit card", "bank", "crypto", "bitcoin", "ethereum",
            "wallet", "monero", "miner", "cryptominer", "coin miner", "mining",
            
            # Ransomware and encryption
            "ransom", "cryptolocker", "locker", "encrypt", "decrypt", "bitcoin address",
            "payment", "tor", "onion", "proxy", "vpn", "anonymizer", "obfuscate",
            
            # Network tools
            "netcat", "nc", "socat", "ncat", "powercat", "plink", "putty", "openssh",
            "winssh", "remote desktop", "rdp", "vnc", "teamviewer", "anydesk"
        ]
        
        self.command_mode = False
        self.current_command = ""
        self.win_pressed = False
        self._alert_active = False  # Prevent multiple simultaneous alerts
        
        self.logger = UpdateLogs()
        self.response = HIDResponse()
        
        # Keyboard listener
        self.listener = None
        
        print("HID Detector initialized - Ready to monitor for Rubber Ducky attacks")
        
    def start_detection(self):
        """Start the HID detection system"""
        print("HID Detection System Started...")
        print("Monitoring for Rubber Ducky attacks...")
        print("Detection methods:")
        print("  1. High-frequency keystroke detection (>100 keystrokes/10s)")
        print("  2. Malicious command detection (Win+R commands)")
        print("  3. Suspicious URL and keyword detection")
        
        # Start buffer cleanup thread
        cleanup_thread = threading.Thread(target=self._cleanup_buffer, daemon=True)
        cleanup_thread.start()
        
        # Start keyboard listener
        def on_press(key):
            self._on_keystroke(key, "press")
            
        def on_release(key):
            self._on_keystroke(key, "release")
        
        self.listener = Listener(on_press=on_press, on_release=on_release)
        self.listener.start()
        
        print("✓ Keyboard listener started")
        print("✓ Buffer cleanup thread started")
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping HID Detection...")
            self.stop_detection()
    
    def _cleanup_buffer(self):
        """Continuously clean up old keystrokes from buffer"""
        while True:
            current_time = time.time()
            
            # Remove keystrokes older than buffer duration
            while (self.keystroke_buffer and 
                   current_time - self.keystroke_buffer[0][0] > self.buffer_duration):
                self.keystroke_buffer.popleft()
            
            # Check for high frequency typing
            self._check_typing_frequency()
            
            time.sleep(1)
    
    def _on_keystroke(self, key, action):
        """Handle each keystroke event"""
        current_time = time.time()
        
        try:
            # Handle special keys
            if hasattr(key, 'char') and key.char is not None:
                key_str = key.char
            else:
                key_str = str(key).replace("Key.", "")
            
            # Track Windows key state
            if key == Key.cmd_l or key == Key.cmd_r:
                if action == "press":
                    self.win_pressed = True
                else:
                    self.win_pressed = False
                return
            
            # Check for Win+R combination
            if self.win_pressed and key_str.lower() == 'r' and action == "press":
                self._start_command_capture()
                return
            
            # Add to buffer (only press events to avoid double counting)
            if action == "press":
                self.keystroke_buffer.append((current_time, key_str))
                
                # Handle command capture mode
                if self.command_mode:
                    self._handle_command_capture(key_str, key)
                    
        except Exception as e:
            print(f"Error processing keystroke: {e}")
    
    def _start_command_capture(self):
        """Start capturing commands after Win+R"""
        print("Command capture started (Win+R detected)")
        self.command_mode = True
        self.current_command = ""
    
    def _handle_command_capture(self, key_str, key):
        """Handle keystrokes during command capture mode"""
        try:
            # Handle special keys
            if key == Key.enter:
                self._analyze_command()
                self.command_mode = False
            elif key == Key.backspace:
                self.current_command = self.current_command[:-1]
            elif key == Key.esc:
                self.command_mode = False
                self.current_command = ""
            elif hasattr(key, 'char') and key.char is not None:
                self.current_command += key_str
            elif key == Key.space:
                self.current_command += ' '
            elif key == Key.tab:
                self.current_command += '\t'
        except Exception as e:
            print(f"Error handling command capture: {e}")
    
    def _analyze_command(self):
        """Analyze the captured command for malicious patterns"""
        if not self.current_command.strip():
            return
        
        print(f"Command captured: {self.current_command}")
        
        # Check command length
        if len(self.current_command) >= self.command_length_threshold:
            self._trigger_alert(
                f"Long command detected: {self.current_command[:100]}...",
                "Long malicious command injection detected"
            )
            return
        
        # Check for malicious keywords
        command_lower = self.current_command.lower()
        for keyword in self.malicious_keywords:
            if keyword in command_lower:
                self._trigger_alert(
                    f"Malicious keyword '{keyword}' in command: {self.current_command[:100]}...",
                    f"Malicious command injection detected ({keyword})"
                )
                return
        
        # Check for URL patterns specifically
        if self._is_suspicious_url(command_lower):
            self._trigger_alert(
                f"Suspicious URL detected: {self.current_command[:100]}...",
                "Suspicious URL injection detected"
            )
            return
        
        # Check for suspicious patterns
        suspicious_patterns = [
            ("powershell", "-enc"),
            ("powershell", "encodedcommand"),
            ("cmd", "/c"),
            ("iex", "downloadstring"),
            ("invoke-expression", "new-object"),
            ("system.net.webclient", "downloadstring"),
            ("start", "min"),
            ("cmd", "start"),
            ("explorer", "http")
        ]
        
        for pattern1, pattern2 in suspicious_patterns:
            if pattern1 in command_lower and pattern2 in command_lower:
                self._trigger_alert(
                    f"Suspicious pattern '{pattern1} + {pattern2}' in command",
                    f"Suspicious command pattern detected"
                )
                return
        
        # Check for encoded commands
        if self._is_encoded_command(command_lower):
            self._trigger_alert(
                f"Encoded command detected: {self.current_command[:100]}...",
                "Encoded command injection detected"
            )
            return
    
    def _is_suspicious_url(self, command_lower):
        """Check if the command contains a suspicious URL pattern"""
        url_indicators = [
            "http://", "https://", "www.", ".com/", ".net/", ".org/", 
            ".io/", ".ru/", ".cn/", "youtu", "bit.ly", "tinyurl",
            "pastebin", "github.io", "webhook", "download", "server"
        ]
        
        # Check for IP addresses in URLs
        ip_pattern = re.compile(r'\b(?:https?://)?\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
        
        if ip_pattern.search(command_lower):
            return True
            
        for indicator in url_indicators:
            if indicator in command_lower:
                return True
        return False
    
    def _is_encoded_command(self, command_lower):
        """Check if the command contains base64 or other encoded content"""
        encoded_indicators = [
            "base64", "encodedcommand", "-enc", "-e ", "frombase64", "tobase64",
            "convertfrom-base64", "convertto-base64", "utf8", "unicode", "encoding"
        ]
        
        for indicator in encoded_indicators:
            if indicator in command_lower:
                return True
        
        # Check for typical base64 patterns (long strings of alphanumeric with = padding)
        base64_pattern = re.compile(r'[A-Za-z0-9+/]{20,}={0,2}')
        if base64_pattern.search(command_lower):
            return True
            
        return False
    
    def _check_typing_frequency(self):
        """Check if typing frequency exceeds threshold"""
        if not self.keystroke_buffer:
            return
        
        current_time = time.time()
        recent_keystrokes = [
            ts for ts, key in self.keystroke_buffer 
            if current_time - ts <= self.buffer_duration
        ]
        
        keystroke_count = len(recent_keystrokes)
        
        # Only log frequency if it's getting high (for debugging)
        if keystroke_count > 50 and keystroke_count % 10 == 0:
            print(f"Keystroke frequency: {keystroke_count} in {self.buffer_duration}s")
        
        # Trigger alert if keystroke count exceeds threshold
        if keystroke_count >= self.keystroke_threshold:
            self._trigger_alert(
                f"High frequency keystrokes detected: {keystroke_count} keystrokes in {self.buffer_duration}s",
                "High frequency keystrokes injector detected"
            )
            
            # Clear buffer after detection to prevent repeated alerts
            self.keystroke_buffer.clear()
    
    def _trigger_alert(self, log_message, alert_message):
        """Trigger logging and response for detected threats"""
        
        # Prevent multiple simultaneous alerts
        if self._alert_active:
            print("⚠️ Alert already active, skipping duplicate...")
            return
            
        self._alert_active = True
        print(f"🚨 ALERT TRIGGERED: {log_message}")
        print(f"Calling response module with: {alert_message}")
        
        # Log the detection
        try:
            self.logger.add_entry(log_message)
            print("✓ Log entry created successfully")
        except Exception as e:
            print(f"✗ Error logging detection: {e}")
        
        # Trigger response with COM initialization
        def trigger_response():
            try:
                print("Initializing COM for response...")
                pythoncom.CoInitialize()
                print("✓ COM initialized")
                print(f"Calling response.show_alert('{alert_message}', 30)")
                self.response.show_alert(alert_message, duration=30)
                print("✓ Response module executed successfully")
            except Exception as e:
                print(f"✗ Error in response thread: {e}")
                import traceback
                traceback.print_exc()
            finally:
                pythoncom.CoUninitialize()
                print("COM uninitialized")
                # Reset alert flag after response completes
                self._alert_active = False
        
        # Start response in a separate thread
        response_thread = threading.Thread(target=trigger_response, daemon=True)
        response_thread.start()
        print("Response thread started")
    
    def stop_detection(self):
        """Stop the HID detection system"""
        if self.listener:
            self.listener.stop()
        print("HID Detection System Stopped")
    
    def get_status(self):
        """Get current detection status"""
        return {
            "listener_running": self.listener is not None and self.listener.running,
            "alert_active": self._alert_active,
            "command_mode": self.command_mode,
            "buffer_size": len(self.keystroke_buffer),
            "keystroke_threshold": self.keystroke_threshold
        }


# Main execution
if __name__ == "__main__":
    detector = HIDDetector()
    
    try:
        detector.start_detection()
    except KeyboardInterrupt:
        print("\nShutting down detection system...")
    except Exception as e:
        print(f"Error in HID detection: {e}")
        import traceback
        traceback.print_exc()
    finally:
        detector.stop_detection()

