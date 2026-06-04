# GoGoGate2 Remote

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Home Assistant custom integration for controlling **GoGoGate2** garage doors via the cloud relay (`my-gogogate.com`).

This is useful when your Home Assistant instance doesn't have access to the GoGoGate2's local network — for example, when HA is hosted remotely in the cloud.

## Features

- Open, close, and stop garage doors
- Door status polling (every 30 seconds)
- Multi-door support (up to 3 doors)
- Status shows as unavailable if device goes offline
- Credentials verified during setup

## Installation

1. In HACS, search for **"GoGoGate2 Remote"** and install it
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration**
4. Search for **"GoGoGate2 Remote"**
5. Enter your device details:
   - **GoGoGate UID** — the 10-character ID printed on your device (e.g. `ac12345678`)
   - **Username** — defaults to `admin`
   - **Password** — your GoGoGate2 password
6. Your doors will appear as cover entities (e.g. `cover.garage_mum_and_dad`)

## Configuration

All configuration is done through the UI. No YAML required.

## Requirements

- A GoGoGate2 device with **remote access enabled** in its settings
- The device must be online and connected to Wi-Fi

## How It Works

The integration communicates with your GoGoGate2 through the official cloud relay at `https://<uid>.my-gogogate.com`. API requests are encrypted using AES/CBC with the GoGoGate2 shared secret.

## Troubleshooting

- **"Failed to connect"** during setup → Make sure remote access is enabled on the GoGoGate2 device
- **Device shows as unavailable** → The GoGoGate2 is likely offline or has lost Wi-Fi
- **Door status not updating** → Check the device is powered on and the PageKite tunnel is active
