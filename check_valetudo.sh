#!/bin/bash

# Path to a small file to store the last version we saw
VERSION_FILE="/data/valetudo-faq-bot/last_valetudo_version.txt"
# Your Perl script path
PERL_SCRIPT="/data/valetudo-faq-bot/scripts/parse_supported_robots_for_root.pl"

# Get the latest tag name from GitHub
LATEST_VERSION=$(curl -s https://api.github.com/repos/Hypfer/Valetudo/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

# Read the last version we processed
if [ -f "$VERSION_FILE" ]; then
    LAST_VERSION=$(cat "$VERSION_FILE")
else
    LAST_VERSION=""
fi

# Compare them
if [ "$LATEST_VERSION" != "$LAST_VERSION" ]; then
    echo "New Valetudo release found: $LATEST_VERSION. Updating..."
    
    # 1. Run your Perl script
    rm -rf /data/valetudo-faq-bot/valetudobot/root/*
    perl "$PERL_SCRIPT" /data/valetudo-faq-bot/valetudobot/root
    
    # 2. Update the version file
    echo "$LATEST_VERSION" > "$VERSION_FILE"
    
    # 3. Update the bot's changelog.txt (Optional but cool)
    echo "- Updated for Valetudo $LATEST_VERSION" > /data/valetudo-faq-bot/changelog.txt
    
    # 4. Restart the bot to force a fresh sync
    systemctl restart valetudobot
    
    echo "Update complete."
else
    echo "No new release. Current: $LATEST_VERSION"
fi