#!/bin/bash
# Synology NAS Setup Script for MedEdBot
# Run this script as root on your Synology NAS via SSH

echo "🚀 Starting MedEdBot Synology NAS Setup..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "❌ Please run as root (use sudo)"
   exit 1
fi

# Variables
DOCKER_ROOT="/volume1/docker/mededbot-v4"
APP_UID=1000  # Default Docker user
APP_GID=1000  # Default Docker group

echo "📁 Creating directory structure..."
# Create only necessary directories for memory storage mode
mkdir -p "$DOCKER_ROOT"/{credentials,logs}

echo "🔧 Setting permissions..."
# Set ownership to Docker user (UID 1000 is standard for containers)
chown -R $APP_UID:$APP_GID "$DOCKER_ROOT"

# Set directory permissions
# 755 for directories (read/write/execute for owner, read/execute for others)
find "$DOCKER_ROOT" -type d -exec chmod 755 {} \;

# Special permissions for logs directory (optional)
chmod 775 "$DOCKER_ROOT/logs"

# Ensure the directories are writable by the container
# DSM 7+ uses different permission model, we need to ensure Docker can write
synogroup --add docker $(whoami) 2>/dev/null || true

echo "📝 Creating template files..."

# Create .env template if it doesn't exist
if [ ! -f "$DOCKER_ROOT/.env" ]; then
    cat > "$DOCKER_ROOT/.env" << 'EOF'
# === Database Configuration ===
DATABASE_URL=postgresql://username:password@host/database?ssl=require

# === LINE Bot Configuration ===
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret

# === Google AI Configuration ===
GEMINI_API_KEY=your_gemini_api_key

# === Email Configuration ===
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

# === Google Drive Configuration (Optional) ===
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
# Option 1: Base64 encoded credentials
GOOGLE_CREDS_B64=your_base64_encoded_credentials
# Option 2: Mount credentials.json file instead

# === Server Configuration ===
# For local network access (external port 10002):
BASE_URL=http://your-nas-ip:10002
# For external access (with domain):
# BASE_URL=https://your-domain.com

# === Application Settings ===
PORT=8080  # Using 8080 to enable memory storage mode
LOG_LEVEL=info

# === Storage Configuration ===
# Force memory storage (like Render deployment)
USE_MEMORY_STORAGE=true
EOF
    echo "✅ Created .env template"
else
    echo "ℹ️  .env file already exists, skipping..."
fi

# Create docker-compose override for local paths
cat > "$DOCKER_ROOT/docker-compose.override.yml" << EOF
# Local override for Synology NAS paths
version: '3.8'

services:
  mededbot:
    volumes:
      # Use absolute paths for Synology (memory storage mode)
      - $DOCKER_ROOT/.env:/app/.env:ro
      - $DOCKER_ROOT/credentials/service-account.json:/app/credentials.json:ro
      # Optional: Mount logs directory
      # - $DOCKER_ROOT/logs:/app/logs
    
    # Ensure proper user mapping
    user: "$APP_UID:$APP_GID"
EOF

echo "🔐 Setting up credentials directory..."
chmod 700 "$DOCKER_ROOT/credentials"
cat > "$DOCKER_ROOT/credentials/README.txt" << 'EOF'
Place your Google service account JSON file here if using file-based authentication.
Rename it to: service-account.json

To use it, uncomment the credentials volume mount in docker-compose.override.yml
EOF

echo "📊 Creating maintenance scripts..."

# Note: No cleanup script needed for memory storage mode
echo "ℹ️  Memory storage mode - audio files are stored in RAM and backed up to Google Drive"

# Create backup script
cat > "$DOCKER_ROOT/backup_data.sh" << 'EOF'
#!/bin/bash
# Backup logs and important data
BACKUP_DIR="/volume1/backup/mededbot/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
cp -r /volume1/docker/mededbot-v4/logs "$BACKUP_DIR/"
tar -czf "$BACKUP_DIR/logs.tar.gz" -C "$BACKUP_DIR" logs
rm -rf "$BACKUP_DIR/logs"
echo "Backup completed to $BACKUP_DIR"
EOF
chmod +x "$DOCKER_ROOT/backup_data.sh"

echo "🚨 Setting up Synology-specific configurations..."

# Check if firewall needs configuration
if synoservice --status synofirewall | grep -q "enabled"; then
    echo "⚠️  Firewall is enabled. Remember to allow port 10002 in:"
    echo "   Control Panel → Security → Firewall → Edit Rules"
fi

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Copy your project files to: $DOCKER_ROOT/"
echo "2. Edit the .env file at: $DOCKER_ROOT/.env"
echo "3. If using file-based Google auth, place service-account.json in: $DOCKER_ROOT/credentials/"
echo "4. Build and run the container:"
echo "   cd $DOCKER_ROOT"
echo "   docker-compose -f docker-compose.synology.yml up -d --build"
echo ""
echo "🔧 Maintenance:"
echo "- Backup logs: $DOCKER_ROOT/backup_data.sh"
echo "- Audio files are stored in memory and backed up to Google Drive"
echo ""
echo "📁 Memory Storage Mode:"
echo "- Files stored in RAM (100 file limit, 24hr TTL)"
echo "- All files backed up to Google Drive automatically"
echo "- No local audio/voicemail directories needed"