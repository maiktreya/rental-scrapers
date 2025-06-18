#!/usr/bin/env bash
# script shortened from an original taken from:  https://gist.github.com/gffcoutinho/51e74d356a43dd1427a407762d8edc72

# Remove existing downloads and binaries so we can start from scratch.
apt remove --assume-yes google-chrome-stable
rm -f ~/chromedriver_linux64.zip
rm -f /usr/bin/chromedriver # Adjusted to /usr/bin/ based on your feedback

# Install dependencies.
apt update --assume-yes
# Removed libgconf-2-4 as it's causing "Unable to locate package" error on modern Ubuntu
apt install --assume-yes unzip openjdk-8-jre-headless xvfb libxi6

# Install Chrome.
# Clean up existing Google Chrome source list files and keyrings to prevent conflicts
sudo rm -f /etc/apt/sources.list.d/google-chrome.list
sudo rm -f /etc/apt/keyrings/google-chrome.gpg

# Attempt to remove problematic public key if it exists
# This handles the "NO_PUBKEY" error by clearing the conflicting key
sudo apt-key list | grep "Google Inc. (Linux Packages Signing Key)" | awk '{print $NF}' | xargs -r sudo apt-key del

# Add the Google Chrome GPG key using wget and place it in the recommended location
sudo wget -O /etc/apt/keyrings/google-chrome.gpg https://dl.google.com/linux/linux_signing_key.pub

# Add the Google Chrome repository with explicit architecture and signed-by parameter
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list > /dev/null

apt -y update
apt -y install google-chrome-stable

# Determine the installed Chrome *full* version string (e.g., "137.0.7151.119")
# Use the full path for google-chrome to ensure it's found
CHROME_FULL_VERSION=$("/usr/bin/google-chrome" --version | awk '{print $3}')

# Construct the ChromeDriver download URL based on the exact Chrome version
# This uses the new "Chrome for Testing" distribution approach
CHROME_DRIVER_DOWNLOAD_URL="https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROME_FULL_VERSION/linux64/chromedriver-linux64.zip"

# Install ChromeDriver.
wget -N "$CHROME_DRIVER_DOWNLOAD_URL" -P ~/
unzip -o ~/chromedriver-linux64.zip -d ~/ # Use -o to overwrite existing files without prompt
rm -f ~/chromedriver-linux64.zip
sudo mv -f ~/chromedriver-linux64 /usr/bin/chromedriver # Move to /usr/bin/ as per your system's expectation
sudo chown root:root /usr/bin/chromedriver
sudo chmod 0755 /usr/bin/chromedriver