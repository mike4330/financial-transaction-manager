# Hetzner Migration Guide (Git Sync, No Reverse Proxy)

## Current Architecture

**Stack:**
- Backend: Flask API (Python 3.14) on port 5000
- Frontend: React + Vite (Node 23.8, pnpm 10.12) on port 3001
- Database: SQLite (3.5MB) at `transactions.db`
- Data: CSV files in `transactions/` (2.8MB)
- Git Repo: `https://github.com/mike4330/financial-transaction-manager.git`
- Features: File monitoring, LLM payee extraction (requires ANTHROPIC_API_KEY)

**Deployment Strategy:** Git sync, direct port access (no nginx)

---

## Hetzner VPS Recommendation

**Minimum Specs:**
- **VPS Type:** CPX11 or CX22 (2 vCPU, 4GB RAM, 40GB disk)
- **OS:** Ubuntu 24.04 LTS
- **Location:** Choose closest to your timezone (EDT/EST mentioned in code)
- **Estimated Cost:** ~$5-7/month

---

## Migration Steps

### 1. Initial Hetzner Setup

```bash
# SSH into new VPS
ssh root@YOUR_HETZNER_IP

# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y python3 python3-pip python3-venv \
    git sqlite3 curl ufw

# Install Node.js (v20+ required)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Install pnpm
npm install -g pnpm

# Create app user
useradd -m -s /bin/bash bankapp
usermod -aG sudo bankapp  # Optional: if you want sudo access
```

### 2. Clone Git Repository

```bash
# Switch to app user
su - bankapp

# Clone repo
cd ~
git clone https://github.com/mike4330/financial-transaction-manager.git bank
cd bank

# Verify
git log --oneline -5
ls -la
```

### 3. Setup Python Backend

```bash
cd ~/bank

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env <<EOF
ANTHROPIC_API_KEY=your-actual-api-key-here
FLASK_ENV=production
EOF
chmod 600 .env

# Create necessary directories
mkdir -p logs transactions/processed

# Initialize empty database (if starting fresh)
# OR transfer your existing transactions.db (see step 7)
python3 -c "from database import TransactionDB; TransactionDB('transactions.db')"
```

### 4. Setup Frontend

```bash
cd ~/bank/frontend

# Install dependencies
pnpm install

# Fix Vite proxy to use IPv4 (required for Hetzner)
# Update vite.config.ts to use 127.0.0.1 instead of localhost
sed -i "s|target: 'http://localhost:5000'|target: 'http://127.0.0.1:5000'|g" vite.config.ts

# Build production assets (optional, can run dev mode)
pnpm run build
```

**Important:** The Vite proxy must use `127.0.0.1` instead of `localhost` to avoid IPv6 connection issues on Hetzner.

### 5. Create Systemd Services

**Create:** `~/bank-backend.service` (temporary file)

```ini
[Unit]
Description=Financial Tracker Flask Backend API
After=network.target

[Service]
Type=simple
User=bankapp
Group=bankapp
WorkingDirectory=/home/bankapp/bank
Environment=PATH=/home/bankapp/bank/.venv/bin:/usr/bin
EnvironmentFile=/home/bankapp/bank/.env

ExecStart=/home/bankapp/bank/.venv/bin/python3 /home/bankapp/bank/api_server.py

Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bank-backend

# Security
NoNewPrivileges=yes
PrivateTmp=yes

# Resource limits
LimitNOFILE=65536
MemoryMax=512M

[Install]
WantedBy=multi-user.target
```

**Create:** `~/bank-frontend.service` (temporary file)

```ini
[Unit]
Description=Financial Tracker React Frontend
After=network.target bank-backend.service
Requires=bank-backend.service

[Service]
Type=simple
User=bankapp
Group=bankapp
WorkingDirectory=/home/bankapp/bank/frontend
Environment=PATH=/usr/bin:/usr/local/bin
Environment=NODE_ENV=production

ExecStart=/usr/local/bin/pnpm run dev -- --host 0.0.0.0 --port 3001

Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bank-frontend

# Security
NoNewPrivileges=yes
PrivateTmp=yes

# Resource limits
LimitNOFILE=65536
MemoryMax=1G

[Install]
WantedBy=multi-user.target
```

**Install services:**

```bash
# As root
exit  # Exit bankapp user back to root

# Copy service files
cp /home/bankapp/bank-backend.service /etc/systemd/system/
cp /home/bankapp/bank-frontend.service /etc/systemd/system/

# Set permissions
chmod 644 /etc/systemd/system/bank-*.service

# Enable and start
systemctl daemon-reload
systemctl enable bank-backend bank-frontend
systemctl start bank-backend bank-frontend

# Check status
systemctl status bank-backend
systemctl status bank-frontend
```

### 6. Configure Firewall

```bash
# As root
ufw allow OpenSSH
ufw allow 5000/tcp   # Backend API
ufw allow 3001/tcp   # Frontend
ufw enable
ufw status
```

### 7. Transfer Existing Database

**From your local workstation:**

```bash
# Transfer database
scp /var/www/html/bank/transactions.db bankapp@YOUR_HETZNER_IP:~/bank/

# Transfer existing CSV files (optional)
scp -r /var/www/html/bank/transactions/*.csv bankapp@YOUR_HETZNER_IP:~/bank/transactions/

# On Hetzner: Set permissions
ssh bankapp@YOUR_HETZNER_IP
cd ~/bank
chmod 644 transactions.db
chmod 755 transactions/
```

---

## Access URLs

After migration, access your app at:

- **Frontend:** `http://YOUR_HETZNER_IP:3001`
- **Backend API:** `http://YOUR_HETZNER_IP:5000/api/health`

---

## Git Update Workflow

When you make changes locally:

```bash
# On local machine
cd /var/www/html/bank
git add .
git commit -m "Your changes"
git push origin main

# On Hetzner
ssh bankapp@YOUR_HETZNER_IP
cd ~/bank
git pull origin main

# Restart services if needed
sudo systemctl restart bank-backend
sudo systemctl restart bank-frontend

# Or if frontend files changed
cd frontend && pnpm install && pnpm run build
sudo systemctl restart bank-frontend
```

---

## Frontend: Dev vs Production Mode

**Option 1: Dev Mode (Current setup)**
- Run Vite dev server on port 3001
- Hot reload enabled
- What the systemd service currently does

**Option 2: Production Mode (Recommended later)**
- Build static files: `pnpm run build`
- Serve with simple HTTP server
- Update systemd service:

```ini
# Updated ExecStart for production mode:
ExecStart=/usr/bin/npx serve -s dist -l 3001
```

For now, dev mode works fine for intranet access.

---

## Security Hardening

### 1. SSH Key Authentication

```bash
# On Hetzner
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add your public key to authorized_keys
# Then disable password auth (as root):
nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
systemctl restart sshd
```

### 2. Database Backups

```bash
# Create backup script
cat > ~/backup-db.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/home/bankapp/backups"
mkdir -p $BACKUP_DIR
sqlite3 /home/bankapp/bank/transactions.db ".backup '$BACKUP_DIR/transactions-$(date +%Y%m%d-%H%M%S).db'"
find $BACKUP_DIR -name "transactions-*.db" -mtime +30 -delete
EOF

chmod +x ~/backup-db.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/bankapp/backup-db.sh
```

### 3. Git Credentials

Your git remote includes an embedded token. Consider switching to SSH:

```bash
# Generate SSH key on Hetzner
ssh-keygen -t ed25519 -C "bankapp@hetzner"

# Add public key to GitHub
cat ~/.ssh/id_ed25519.pub
# Copy to GitHub Settings > SSH Keys

# Update git remote
cd ~/bank
git remote set-url origin git@github.com:mike4330/financial-transaction-manager.git
```

### 4. API Key Security

Never commit `.env` file (already in .gitignore). Transfer it manually:

```bash
# From local
scp /var/www/html/bank/.env bankapp@YOUR_HETZNER_IP:~/bank/.env
```

---

## Monitoring & Maintenance

### Log Locations

```bash
# Backend logs
journalctl -u bank-backend -f

# Frontend logs
journalctl -u bank-frontend -f

# Application logs
tail -f ~/bank/logs/*.log
tail -f ~/bank/flask_app.log
```

### Quick Commands

```bash
# Restart services
sudo systemctl restart bank-backend
sudo systemctl restart bank-frontend

# Update from git
cd ~/bank && git pull

# Check resource usage
htop  # Install: sudo apt install htop
df -h
du -sh ~/bank/*

# Database stats
sqlite3 ~/bank/transactions.db "SELECT COUNT(*) FROM transactions;"
```

### Health Checks

```bash
# Backend health
curl http://localhost:5000/api/health

# Check ports
ss -tlnp | grep -E '5000|3001'

# Service status
systemctl status bank-backend bank-frontend
```

---

## Troubleshooting

### Backend won't start

```bash
journalctl -u bank-backend -n 50
# Common issues:
# - Missing .env file
# - Database permissions
# - Python path incorrect
```

### Frontend build errors

```bash
cd ~/bank/frontend
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### Port already in use

```bash
# Find process using port
sudo lsof -i :5000
sudo lsof -i :3001

# Kill if needed
sudo kill -9 <PID>
```

### Database locked

```bash
# Check for processes using DB
lsof ~/bank/transactions.db

# Usually means backend is already running
systemctl status bank-backend
```

### Git pull conflicts

```bash
cd ~/bank
git stash  # Save local changes
git pull origin main
git stash pop  # Reapply local changes
```

### Frontend can't connect to backend (proxy errors)

```bash
# Check logs for "ECONNREFUSED ::1:5000" errors
journalctl -u bank-frontend -n 50 | grep proxy

# This indicates IPv6 issue with localhost
# Fix: Update vite.config.ts to use 127.0.0.1
cd ~/bank/frontend
sed -i "s|localhost:5000|127.0.0.1:5000|g" vite.config.ts
sudo systemctl restart bank-frontend

# Verify fix
curl http://localhost:3001/api/health
```

---

## Cost Estimate

- **VPS (CPX11):** ~$5/month
- **Anthropic API:** Pay-as-you-go (~$0.01-0.05/transaction with LLM)

**Total:** ~$60/year + API usage

---

## Development Workflow

**Working locally:**
1. Make changes in `/var/www/html/bank`
2. Test locally on localhost
3. Commit and push to GitHub
4. Pull on Hetzner
5. Restart services if needed

**Direct editing on Hetzner (for quick fixes):**
1. SSH into Hetzner
2. Edit files in `~/bank`
3. Commit and push from Hetzner
4. Pull on local machine later

---

## Rollback Plan

If migration fails:
1. Your local system is unchanged
2. GitHub has full history
3. Can destroy Hetzner VPS and retry

To revert to local only:
```bash
# On local machine
cd /var/www/html/bank
python3 api_server.py  # Terminal 1
cd frontend && pnpm run dev  # Terminal 2
```

---

## Future Improvements

1. **Add nginx reverse proxy** (consolidate to single port 80/443)
2. **SSL with Let's Encrypt** (requires domain name)
3. **Production frontend build** (serve static files instead of dev server)
4. **Docker containers** (easier updates and isolation)
5. **Monitoring** (Uptime Robot, Healthchecks.io)
6. **Automated backups** to external storage

---

## Pre-Migration Checklist

- [ ] Commit all local changes to GitHub
- [ ] Note your ANTHROPIC_API_KEY for .env file
- [ ] Create Hetzner VPS account
- [ ] Have SSH access to Hetzner VPS
- [ ] Backup local transactions.db just in case

---

**Ready to migrate! Start with step 1 and work sequentially.**

Access your app at `http://YOUR_HETZNER_IP:3001` when complete.
