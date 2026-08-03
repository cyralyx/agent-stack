# Installer and Packaging

Targets:

- Windows installer
- Linux AppImage or package
- macOS package where feasible
- portable mode
- Docker Compose server mode

Installer responsibilities:

- hardware check
- dependency check
- storage estimate
- local database setup
- first-run provider setup
- optional local model detection
- backup path selection
- diagnostics
- repair mode
- uninstall without deleting user data unless explicitly chosen
