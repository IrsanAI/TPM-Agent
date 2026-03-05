# Platform Execution Pack

## Linux (systemd)
Templates:
- `deployment/systemd/tpm-web.service`
- `deployment/systemd/tpm-live.service`
- `deployment/systemd/tpm-cockpit.service`

Usage example:
```bash
sudo cp deployment/systemd/tpm-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tpm-web.service
```

## macOS (launchd)
Templates:
- `deployment/launchd/com.irsanai.tpm.web.plist`
- `deployment/launchd/com.irsanai.tpm.live.plist`
- `deployment/launchd/com.irsanai.tpm.cockpit.plist`

> Replace `/Users/USERNAME/IrsanAI-TPM` with your real path.

Usage example:
```bash
cp deployment/launchd/com.irsanai.tpm.web.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.irsanai.tpm.web.plist
```

## iPhone PWA
PWA assets:
- `playground/manifest.webmanifest`
- `playground/sw.js`

Open the web hub in Safari, then "Add to Home Screen".
