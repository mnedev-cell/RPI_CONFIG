#!/bin/bash
echo "Initial Start"
WORKDIR=/home/pi/WORKDIR
MAINFILE=$WORKDIR/main.py
CONFIG_FILE=$WORKDIR/config.py
# Create WORKDIR if it doesn't exist
if [ ! -d "$WORKDIR" ]; then
  mkdir -p "$WORKDIR"
  echo "Created directory: $WORKDIR"
else
  echo "Directory $WORKDIR exists."
fi
cd /home/pi/WORKDIR
# Check if MAINFILE (main.py) exists, if not, download or create it
if [ ! -f "$MAINFILE" ]; then
  echo "Downloading or creating main.py"
  wget -O "$MAINFILE" "https://upload.yapo.ovh/update/main.py" || {

    echo "Could not download main.py, creating a default one."
    cat <<EOT >> "$MAINFILE"
# main.py - Auto-generated script
import os
import time

def main():
    print("Program started")

if __name__ == '__main__':
    main()
EOT
  }
else
  echo "main.py already exists: $MAINFILE"
fi
while true
do
    sudo /usr/bin/python3 /home/pi/WORKDIR/main.py
    sleep 1
done
$SHELL