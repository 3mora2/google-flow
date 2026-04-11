# Flow Image Local API

Chinese README: [README-zh.md](./README-zh.md)

This repository packages `flow-image-cli` into a cleaner local deployment that exposes an OpenAI-compatible image API.

The intended flow is simple:

1. Run `install.bat`
2. Run `start-flow-api.bat`
3. Sign in to Google Flow in the browser window that opens
4. Wait for `/setup` to finish and copy the final `URL`, `API Key`, and `Model`

No browser extension is required.

## What This Repo Includes

- Local OpenAI-compatible API service
- Guided setup page at `/setup`
- Automatic Flow login detection and token sync
- Text-to-image and image-to-image generation
- 1K / 2K / 4K output selection
- Aspect ratio mapping for `1:1`, `9:16`, `16:9`, and `21:9`
- Playwright-based local browser flow for Flow login / captcha handling

## Requirements

- Windows
- Python 3.10 or newer
- A Google account that can access Flow: <https://labs.google/fx>
- Flow image generation permission on that account

## Quick Start

### 1. Install

Double-click:

```bat
install.bat
```

What it does:

- Creates `.venv`
- Installs Python dependencies
- Installs the project in editable mode
- Installs Playwright Chromium

### 2. Start

Double-click:

```bat
start-flow-api.bat
```

This starts the local server and opens:

- Setup page: `http://127.0.0.1:8787/setup`
- API base URL: `http://127.0.0.1:8787/v1`

### 3. Complete Setup

On the setup page:

1. Sign in to Google Flow when the browser opens
2. Wait for the local service to detect the login
3. Let the service finish token sync automatically
4. Copy the displayed API information card

The setup page provides:

- `Open Login`
- `Re-sync`
- `Reset Config`
- Human-readable API result cards instead of raw JSON

## API Information

Default local configuration:

- Base URL: `http://127.0.0.1:8787/v1`
- API Key: `flow-local-key`

You can change the API key by setting:

```powershell
$env:FLOW_API_KEY="your-own-key"
```

## Supported Endpoints

- `GET /health`
- `GET /setup`
- `GET /setup/status`
- `POST /setup/open-login`
- `POST /setup/finalize`
- `POST /setup/reset`
- `GET /v1/models`
- `POST /v1/images/generations`
- `POST /v1/images/edits`
- `POST /v1/chat/completions`
- `GET /v1/files/{filename}`

## Model Usage

Examples of direct model IDs:

- `gemini-3.1-flash-image-landscape`
- `gemini-3.1-flash-image-portrait`
- `gemini-3.1-flash-image-square`
- `gemini-3.0-pro-image-landscape`
- `imagen-4.0-generate-preview-landscape`
- `nano-banana-2-landscape`
- `nano-banana-2-portrait`
- `nano-banana-2-square`
- `nano-banana-2-ultrawide`
- `nano-banana-pro-landscape`
- `nano-banana-pro-portrait`
- `nano-banana-pro-square`

Family aliases also work:

- `gemini-3.1-flash-image`
- `gemini-3.0-pro-image`
- `imagen-4.0-generate-preview`
- `nano banana2`
- `nano banana pro`

Important note:

- Only `nano banana2` supports `21:9`

## Size And Aspect Ratio Mapping

The compatible API accepts either standard image size hints or friendly values from third-party tools.

Size mapping:

- `1K` -> original output
- `2K` -> 2K upscale
- `4K` -> 4K upscale
- `1024x1024` -> square
- `1024x1536` -> portrait
- `1536x1024` -> landscape

Aspect ratio mapping:

- `1:1` -> square
- `9:16` -> portrait
- `16:9` -> landscape
- `21:9` -> ultrawide, `nano banana2` only

Quality mapping:

- `standard` -> original
- `hd` or `2k` -> 2K upscale
- `4k` -> 4K upscale

The wrapper also reads friendly prompt hints such as:

- `Preferred size: 4K`
- `Preferred aspect ratio: 9:16`

## Example Requests

Text-to-image:

```bash
curl http://127.0.0.1:8787/v1/images/generations ^
  -H "Authorization: Bearer flow-local-key" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"gemini-3.1-flash-image\",\"prompt\":\"a cinematic cat\",\"size\":\"1536x1024\",\"quality\":\"hd\",\"response_format\":\"url\"}"
```

Image-to-image:

```bash
curl http://127.0.0.1:8787/v1/images/edits ^
  -H "Authorization: Bearer flow-local-key" ^
  -F "model=gemini-3.1-flash-image" ^
  -F "prompt=convert to watercolor" ^
  -F "size=1024x1024" ^
  -F "quality=2k" ^
  -F "image=@input.jpg"
```

Python example:

```python
import asyncio
from flow_cli.client import ImageGenerator

async def main():
    g = ImageGenerator()
    path = await g.generate(
        prompt="a cinematic cat",
        model="gemini-3.1-flash-image-landscape",
        output_path="output/api_basic.png",
    )
    print(path)

asyncio.run(main())
```

More request examples are in [API_USAGE.md](./API_USAGE.md).

## Project Layout

```text
flow-image-cli/
├── flow_cli/              # Core CLI + local API server
├── install.bat            # One-click installer
├── start-flow-api.bat     # One-click launcher
├── API_USAGE.md           # Compatible API examples
└── README.md
```

## Notes

- This repository is intended for local deployment on your own machine or another Windows PC.
- The user only needs to complete Google Flow login.
- The remaining setup is handled by the local service.
- If the account does not have Flow image access or upscale permissions, generation or 4K output may fail upstream.

## License

MIT
