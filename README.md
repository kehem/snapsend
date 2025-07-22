# SnapSend

SnapSend is a lightweight, local network (LAN) file transfer application built with Python and Kivy. It enables seamless file and folder sharing between devices on the same network using a drag-and-drop interface, with real-time progress tracking and speed monitoring. Ideal for quick, secure transfers within trusted local environments!

## Features
- **File and Folder Transfer**: Send individual files or zipped folders effortlessly.
- **Automatic Device Discovery**: Detects devices on the LAN without manual configuration.
- **Real-Time Progress**: Displays transfer progress and speed metrics.
- **Drag-and-Drop Support**: Upload files or folders by dragging them into the app or via a file explorer.
- **Modern UI**: Features a clean, customizable interface with rounded designs.
- **Extensible Design**: Built with Kivy, with potential for future cross-platform support.

## Requirements
- Python 3.6 or higher
- Kivy 2.0.0 or higher
- tkinter (for file dialog)
- Dependencies: `kivy`, `socket`, `threading`, `os`, `zipfile`, `tempfile`

## Installation

### Prerequisites
Install Python from [python.org](https://www.python.org/downloads/) if not already present.

### Steps
1. Clone the repository or download the source code:
   ```bash
   git clone https://github.com/kehem/snapsend.git
   cd snapsend
   ```
- Install the required dependencies:

```bash
pip install -r requirements.txt
```
- Run the application 
```bash
python app.py
```

# Usage

## Getting Started

- Launch SnapSend on at least two devices connected to the same LAN.

- The app will automatically discover available devices and display them in the device list.

- Select a device by clicking its card to navigate to the upload screen.

- Drag and drop a file or folder into the upload area, or click to select files/folders via the file explorer.

- Monitor the transfer progress and speed in the sending status UI.

- Received files are saved to the ~/Downloads/SnapSend directory.


## Navigation 
- **Back Buttton**: Click the back arrow (top-right) on the upload screen to return to the device list.

- **Settings Icon**: Currently a placeholder; future updates may include settings options.

# Known Limitations

- Currently supports desktop environments (Windows, potentially macOS/Linux with adjustments).
- No encryption or security features (intended for trusted local networks).
- Mobile support is not yet implemented.

# Contributing

Contributions are welcome! Please fork the repository and submit pull requests for:
- Bug fixes
- New features (e.g., transfer history, pause/resume)
- Cross-platform support

# License[MIT]

This project is open-source; feel free to modify and distribute it under the terms of the license.

# Contact
For questions or support, reach out at support@kehem.com.

Last updated: 04:36 PM +06, Tuesday, July 22, 2025

