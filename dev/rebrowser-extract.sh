#!/bin/bash

# Simple DataDome Cookie Extractor for Idealista
# Usage: ./extract_cookies.sh

USER_DATA_DIR="$HOME/idealista_session"
BOT_PROFILE="/home/other/Downloads/BotBrowser-main/profiles/v137/chrome137_win10_x64.enc"
URL="https://www.idealista.com"

echo "Extracting DataDome cookies from Idealista..."

# Function to extract cookies from Chrome profile
extract_cookies() {
    local cookies_db="$USER_DATA_DIR/Default/Cookies"

    if [ ! -f "$cookies_db" ]; then
        echo "Error: Cookies database not found at $cookies_db"
        return 1
    fi

    echo "Extracting cookies from Chrome profile..."

    # Use sqlite3 to query cookies
    sqlite3 "$cookies_db" "
    SELECT name, value, host_key, path
    FROM cookies
    WHERE (name LIKE '%datadome%' OR host_key LIKE '%idealista%')
    AND expires_utc > $(date +%s)000000;
    " | while IFS='|' read -r name value domain path; do
        echo "Cookie: $name=$value (Domain: $domain, Path: $path)"
    done
}

# Function to launch Chrome and wait
launch_and_wait() {
    echo "Launching Chrome with bot profile..."

    chromium-browser \
        --no-sandbox \
        --user-data-dir="$USER_DATA_DIR" \
        --bot-profile="$BOT_PROFILE" \
        --headless=new \
        "$URL" &

    CHROME_PID=$!
    echo "Chrome PID: $CHROME_PID"

    # Wait for page to load and DataDome to initialize
    echo "Waiting 15 seconds for DataDome to initialize..."
    sleep 15

    # Kill Chrome
    kill $CHROME_PID 2>/dev/null
    wait $CHROME_PID 2>/dev/null
}

# Function to get cookies in different formats
format_cookies() {
    local format=$1
    local cookies_db="$USER_DATA_DIR/Default/Cookies"

    case $format in
        "curl")
            echo "--- Cookies for curl ---"
            sqlite3 "$cookies_db" "
            SELECT name || '=' || value
            FROM cookies
            WHERE (name LIKE '%datadome%' OR host_key LIKE '%idealista%')
            AND expires_utc > $(date +%s)000000;
            " | tr '\n' ';' | sed 's/;$//'
            echo
            ;;
        "requests")
            echo "--- Cookies for Python requests ---"
            echo "{"
            sqlite3 "$cookies_db" "
            SELECT '\"' || name || '\": \"' || value || '\",'
            FROM cookies
            WHERE (name LIKE '%datadome%' OR host_key LIKE '%idealista%')
            AND expires_utc > $(date +%s)000000;
            " | sed '$s/,$//'
            echo "}"
            ;;
        "json")
            echo "--- Cookies as JSON ---"
            echo "["
            sqlite3 "$cookies_db" "
            SELECT '{\"name\": \"' || name || '\", \"value\": \"' || value || '\", \"domain\": \"' || host_key || '\"},'
            FROM cookies
            WHERE (name LIKE '%datadome%' OR host_key LIKE '%idealista%')
            AND expires_utc > $(date +%s)000000;
            " | sed '$s/,$//'
            echo "]"
            ;;
    esac
}

# Main execution
main() {
    # Launch Chrome and let it load
    launch_and_wait

    # Extract and display cookies
    echo
    echo "=== EXTRACTED COOKIES ==="
    extract_cookies

    echo
    format_cookies "curl"

    echo
    format_cookies "requests"

    echo
    format_cookies "json"
}

# Check dependencies
if ! command -v sqlite3 &> /dev/null; then
    echo "Error: sqlite3 is required but not installed."
    echo "Install with: sudo apt-get install sqlite3"
    exit 1
fi

if ! command -v chromium-browser &> /dev/null; then
    echo "Error: chromium-browser not found"
    exit 1
fi

# Run main function
main