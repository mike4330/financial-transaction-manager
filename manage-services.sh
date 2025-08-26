#!/bin/bash

# Financial Tracker Service Management Script

set -e

BACKEND_SERVICE="financial-tracker-backend.service"
FRONTEND_SERVICE="financial-tracker-frontend.service"
MAIN_SERVICE="financial-tracker.service"

SERVICE_FILES_DIR="/var/www/html/bank"
SYSTEMD_DIR="/etc/systemd/system"

case "$1" in
    install)
        echo "Installing Financial Tracker systemd services..."
        
        # Copy service files
        sudo cp "$SERVICE_FILES_DIR/$MAIN_SERVICE" "$SYSTEMD_DIR/"
        sudo cp "$SERVICE_FILES_DIR/$BACKEND_SERVICE" "$SYSTEMD_DIR/"
        sudo cp "$SERVICE_FILES_DIR/$FRONTEND_SERVICE" "$SYSTEMD_DIR/"
        
        # Set correct permissions
        sudo chmod 644 "$SYSTEMD_DIR/$MAIN_SERVICE"
        sudo chmod 644 "$SYSTEMD_DIR/$BACKEND_SERVICE"
        sudo chmod 644 "$SYSTEMD_DIR/$FRONTEND_SERVICE"
        
        # Reload systemd
        sudo systemctl daemon-reload
        
        # Enable services
        sudo systemctl enable $MAIN_SERVICE
        sudo systemctl enable $BACKEND_SERVICE
        sudo systemctl enable $FRONTEND_SERVICE
        
        echo "Services installed and enabled. Use 'sudo systemctl start financial-tracker' to start."
        ;;
        
    start)
        echo "Starting Financial Tracker services..."
        sudo systemctl start $MAIN_SERVICE
        echo "Services started. Check status with: systemctl status financial-tracker"
        ;;
        
    stop)
        echo "Stopping Financial Tracker services..."
        sudo systemctl stop $MAIN_SERVICE
        echo "Services stopped."
        ;;
        
    restart)
        echo "Restarting Financial Tracker services..."
        sudo systemctl restart $MAIN_SERVICE
        echo "Services restarted."
        ;;
        
    status)
        echo "=== Financial Tracker Service Status ==="
        sudo systemctl status $MAIN_SERVICE --no-pager -l
        echo
        echo "=== Backend Service Status ==="
        sudo systemctl status $BACKEND_SERVICE --no-pager -l
        echo
        echo "=== Frontend Service Status ==="
        sudo systemctl status $FRONTEND_SERVICE --no-pager -l
        ;;
        
    logs)
        echo "=== Recent Backend Logs ==="
        sudo journalctl -u $BACKEND_SERVICE -n 20 --no-pager
        echo
        echo "=== Recent Frontend Logs ==="
        sudo journalctl -u $FRONTEND_SERVICE -n 20 --no-pager
        ;;
        
    logs-follow)
        echo "Following logs (Ctrl+C to stop)..."
        sudo journalctl -u $BACKEND_SERVICE -u $FRONTEND_SERVICE -f
        ;;
        
    uninstall)
        echo "Uninstalling Financial Tracker systemd services..."
        
        # Stop and disable services
        sudo systemctl stop $MAIN_SERVICE 2>/dev/null || true
        sudo systemctl disable $MAIN_SERVICE 2>/dev/null || true
        sudo systemctl disable $BACKEND_SERVICE 2>/dev/null || true
        sudo systemctl disable $FRONTEND_SERVICE 2>/dev/null || true
        
        # Remove service files
        sudo rm -f "$SYSTEMD_DIR/$MAIN_SERVICE"
        sudo rm -f "$SYSTEMD_DIR/$BACKEND_SERVICE"
        sudo rm -f "$SYSTEMD_DIR/$FRONTEND_SERVICE"
        
        # Reload systemd
        sudo systemctl daemon-reload
        
        echo "Services uninstalled."
        ;;
        
    build-frontend)
        echo "Building frontend for production..."
        cd /var/www/html/bank/frontend
        npm run build
        echo "Frontend build complete."
        ;;
        
    *)
        echo "Financial Tracker Service Manager"
        echo
        echo "Usage: $0 {install|start|stop|restart|status|logs|logs-follow|build-frontend|uninstall}"
        echo
        echo "Commands:"
        echo "  install       - Install systemd service files"
        echo "  start         - Start all services"
        echo "  stop          - Stop all services"
        echo "  restart       - Restart all services"
        echo "  status        - Show service status"
        echo "  logs          - Show recent service logs"
        echo "  logs-follow   - Follow service logs in real-time"
        echo "  build-frontend- Build React frontend for production"
        echo "  uninstall     - Remove systemd service files"
        echo
        echo "After installation, services can also be managed with systemctl:"
        echo "  sudo systemctl start financial-tracker"
        echo "  sudo systemctl status financial-tracker"
        echo "  sudo journalctl -u financial-tracker-backend -f"
        exit 1
        ;;
esac