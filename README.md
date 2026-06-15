# Flow Image Local API & Programmatic SDK (Unified)

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

Arabic Version: [README-ar.md](./README-ar.md) | Architecture Details: [ARCHITECTURE-ar.md](./ARCHITECTURE-ar.md)

This repository provides a unified local deployment of Google Flow image generation, exposed via an **OpenAI-compatible HTTP API** and a **high-level programmatic Python SDK**.

---

## 🌟 Key Features

1. **Guided Setup (`/setup`)**: A user-friendly web interface that opens automatically, detects Google Flow login states, and synchronizes tokens without manual copy-pasting.
2. **Integrated Token Updater**: A background scheduling service that keeps session tokens alive across multiple profiles, supporting proxy isolation for each profile to prevent footprint leaks.
3. **In-Process Captcha Solver**: Resolves reCAPTCHA challenges directly within the same Python process via Playwright/nodriver, eliminating separate bridge servers or port configurations.
4. **Programmatic SDK (`FlowSDK`)**: A clean, thread-safe context manager to embed Google Flow image generation directly into other Python applications.
5. **OpenAI-Compatible Endpoints**: Seamlessly connects to any third-party AI UI client (e.g., Cherry Studio, Next Chat) using standard `URL`, `API Key`, and `Model` configurations.

---

## 🚀 Quick Start

### 1. Installation

Double-click the installer:
```bat
install.bat
```
*This will automatically create a `.venv`, install the package in editable mode, and download the Playwright Chromium browser.*

### 2. Startup

Double-click the launcher:
```bat
start-flow-api.bat
```
*This starts the API server on port `8787` and automatically opens the setup interface in your browser.*

### 3. Complete Setup
1. Log in to Google Flow on the browser window that opens.
2. Wait for the setup page (`http://127.0.0.1:8787/setup`) to detect the active session.
3. Copy the generated API URL, Key, and Model ID displayed on the screen.

---

## 📡 API Reference

### Connection Details
* **Base URL**: `http://127.0.0.1:8787/v1`
* **Default API Key**: `flow-local-key`

### Endpoints
* `POST /v1/images/generations` - Text-to-Image generation
* `POST /v1/images/edits` - Image-to-Image generation (watercolor, sketch, etc.)
* `GET /v1/models` - List available models and aspect ratios
* `GET /health` - Health check status
* `GET /setup` - Configuration wizard

---

## 🐍 Programmatic Python SDK Usage

You can import and use the SDK directly inside your own Python projects:

```python
import asyncio
from google_flow import FlowSDK

async def main():
    # Option 1: Direct Session Token Override
    async with FlowSDK(st_token="your-session-token", project_id="your-project-id") as sdk:
        image_path = await sdk.generate(
            prompt="A futuristic city in antigravity, neon lights, 4k",
            model="gemini-3.1-flash-image-landscape",
            output_path="output/direct_t2i.png"
        )
        print(f"Image saved to: {image_path}")

    # Option 2: Automatic Profile Selector (Querying local SQLite database)
    async with FlowSDK() as sdk:
        await sdk.select_profile("My_Google_Profile_Name")
        image_path = await sdk.generate(
            prompt="A majestic golden eagle flying over mountains",
            model="gemini-3.1-flash-image-square",
            output_path="output/profile_t2i.png"
        )
        print(f"Image saved to: {image_path}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📁 Repository Structure

```text
flow-image-cli-local-api/
├── google_flow/              # Unified core package
│   ├── api/               # FastAPI OpenAI web server & static dashboard
│   ├── captcha/           # In-process captcha provider integrations
│   ├── captcha_service/   # Integrated reCAPTCHA crawler (nodriver/playwright)
│   ├── token_updater/     # Automated session renewal daemon
│   ├── core/              # Programmatic SDK (FlowSDK) & API client
│   └── utils/             # Shared parsing, DB, and proxy utilities
├── examples/              # Programmatic usage examples
├── release-package/       # Scripts to build clean distribution zip packages
├── install.bat            # One-click installer for Windows
├── start-flow-api.bat     # One-click launcher for Windows
├── API_USAGE.md           # API endpoints & cURL request examples
└── README.md
```

## 📦 Building a Release

To share a clean distribution folder (without `.git`, `.venv`, or local output folders) with friends or clients:
1. Run `release-package\build-release-package.bat`
2. Share the generated zip file located at `release-package\dist\flow-image-cli-local-api-v1.0.0.zip`

## 📝 License

This project is licensed under the MIT License.
