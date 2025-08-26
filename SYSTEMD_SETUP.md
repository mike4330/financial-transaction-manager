# Systemd Service Setup

## Quick Start

```bash
# Install services
./manage-services.sh install

# Start everything
./manage-services.sh start

# Check status
./manage-services.sh status

# Follow logs
./manage-services.sh logs-follow
```

## What Gets Installed

- **financial-tracker-backend.service** - Flask API on port 5000
- **financial-tracker-frontend.service** - React dev server on port 3001 (with hot reload!)
- **financial-tracker.service** - Main service that controls both

## Features

✅ **Development-friendly**: Uses `npm run dev` for hot reload  
✅ **Auto-restart**: Services restart if they crash  
✅ **Logging**: Logs to systemd journal + `flask_app.log`  
✅ **Security**: Runs as user `mike`, not root  
✅ **Dependency management**: Frontend waits for backend  
✅ **Resource limits**: Memory limits to prevent runaway processes  

## Service Management

```bash
# Manual systemctl commands
sudo systemctl start financial-tracker
sudo systemctl stop financial-tracker
sudo systemctl restart financial-tracker
sudo systemctl status financial-tracker

# View logs
sudo journalctl -u financial-tracker-backend -f
sudo journalctl -u financial-tracker-frontend -f
```

## Logs Location

- **Flask app**: `/var/www/html/bank/flask_app.log` (rotated at 10MB)
- **Systemd logs**: `journalctl -u financial-tracker-backend`
- **Request logs**: Logged to both file and journal (skips health checks)

## Notes

- Frontend runs in development mode with hot reload
- Backend has production optimizations but debug=False
- Services auto-start on boot after installation
- Use `manage-services.sh uninstall` to remove everything