# AppGuard Pro 🛡️

AppGuard Pro is a robust, premium-designed application locker and access management system for Windows. It allows you to lock individual applications, set up application groups, restrict access via USB physical keys, and even lock your PC remotely via your mobile phone.

## Features

- **App Locking**: Instantly lock specific executables (like Chrome, Discord, or games) behind a secure password prompt.
- **Session Allowance**: Once unlocked, multi-process apps remain unlocked for the duration of the session until manually locked or the screen is locked.
- **USB Physical Key**: Tie application access to a physical USB drive. If the USB drive is unplugged, the app locks automatically.
- **Remote Lock**: Scan a QR code on your mobile device to lock your PC instantly over your local network. Token-secured.
- **AES-256-GCM Encryption**: All application configurations, including password hashes (Argon2id), are stored securely using machine-specific encryption keys.
- **Screen Lock Detection**: Automatically re-locks all applications when the Windows screen locks.
- **Emergency Lock**: Quickly lock all allowed apps with a global hotkey (default: `Ctrl+Shift+L`).
- **Premium UI**: Crafted with PyQt6 featuring beautiful micro-animations, ripple effects, and dynamic theme colors.

## Installation

### Prerequisites

Ensure you have Python 3.10+ installed on your Windows machine.

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/AppGuard.git
   cd AppGuard
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```
   *(For a background silent run, you can use `pythonw.exe main.py`)*

## Security Architecture

- **Password Hashing**: Employs `Argon2id` which is resistant to GPU-based brute-force attacks.
- **Data Encryption**: The configuration is encrypted via `AES-256-GCM`. The key is dynamically derived using Windows DPAPI, tying the config exclusively to your Windows user account.
- **Process Protection**: Automatically catches and terminates restricted background processes until authenticated.

## License
[MIT License](LICENSE)
