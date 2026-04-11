# Flow Image 本地 API

English README: [README.md](./README.md)

这个仓库把 `flow-image-cli` 整理成了一个更适合本地部署和分享给别人使用的版本，对外提供 OpenAI 兼容图片 API。

推荐使用流程很简单：

1. 双击 `install.bat`
2. 双击 `start-flow-api.bat`
3. 在自动打开的浏览器里登录 Google Flow
4. 等 `/setup` 页面自动完成，复制最终显示的 `URL`、`API Key`、`Model`

不需要浏览器插件。

## 这个版本包含什么

- 本地 OpenAI 兼容 API 服务
- `/setup` 引导完成页
- 自动检测 Flow 登录并同步令牌
- 文生图 / 图生图
- 1K / 2K / 4K 输出选择
- `1:1`、`9:16`、`16:9`、`21:9` 比例映射
- 基于 Playwright 的本地浏览器登录 / 验证码处理流程

## 运行要求

- Windows
- Python 3.10 及以上
- 能访问并登录 Flow：<https://labs.google/fx>
- 登录账号本身具备 Flow 生图权限

## 快速开始

### 1. 安装

双击：

```bat
install.bat
```

它会自动完成：

- 创建 `.venv`
- 安装 Python 依赖
- 以可编辑模式安装项目
- 安装 Playwright Chromium

### 2. 启动

双击：

```bat
start-flow-api.bat
```

启动后会自动打开：

- 设置页：`http://127.0.0.1:8787/setup`
- API 地址：`http://127.0.0.1:8787/v1`

### 3. 完成配置

在设置页中：

1. 按提示登录 Google Flow
2. 等待系统自动检测到登录状态
3. 让本地服务自动完成同步
4. 直接复制卡片里展示的 API 信息

设置页提供：

- `Open Login`
- `Re-sync`
- `Reset Config`
- 可直接阅读的 API 信息卡片，不再显示原始 JSON

## 默认 API 信息

默认本地配置如下：

- Base URL：`http://127.0.0.1:8787/v1`
- API Key：`flow-local-key`

如果你想改 API Key，可以在启动前设置：

```powershell
$env:FLOW_API_KEY="your-own-key"
```

## 支持的接口

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

## 模型使用

可直接使用的模型 ID 示例：

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

也支持模型族别名：

- `gemini-3.1-flash-image`
- `gemini-3.0-pro-image`
- `imagen-4.0-generate-preview`
- `nano banana2`
- `nano banana pro`

特别说明：

- 只有 `nano banana2` 支持 `21:9`

## 尺寸与比例映射

为了方便第三方调用，这个兼容层支持常见尺寸字段和更友好的提示值。

尺寸映射：

- `1K` -> 原图
- `2K` -> 2K 放大
- `4K` -> 4K 放大
- `1024x1024` -> 方图
- `1024x1536` -> 竖图
- `1536x1024` -> 横图

比例映射：

- `1:1` -> 方图
- `9:16` -> 竖图
- `16:9` -> 横图
- `21:9` -> 超宽图，仅 `nano banana2`

质量映射：

- `standard` -> 原图
- `hd` 或 `2k` -> 2K 放大
- `4k` -> 4K 放大

同时也能识别第三方拼进提示词里的信息，例如：

- `Preferred size: 4K`
- `Preferred aspect ratio: 9:16`

## 请求示例

文生图：

```bash
curl http://127.0.0.1:8787/v1/images/generations ^
  -H "Authorization: Bearer flow-local-key" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"gemini-3.1-flash-image\",\"prompt\":\"a cinematic cat\",\"size\":\"1536x1024\",\"quality\":\"hd\",\"response_format\":\"url\"}"
```

图生图：

```bash
curl http://127.0.0.1:8787/v1/images/edits ^
  -H "Authorization: Bearer flow-local-key" ^
  -F "model=gemini-3.1-flash-image" ^
  -F "prompt=convert to watercolor" ^
  -F "size=1024x1024" ^
  -F "quality=2k" ^
  -F "image=@input.jpg"
```

Python 调用示例：

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

更多调用示例见 [API_USAGE.md](./API_USAGE.md)。

## 仓库结构

```text
flow-image-cli/
├── flow_cli/              # 核心 CLI 与本地 API 服务
├── install.bat            # 一键安装
├── start-flow-api.bat     # 一键启动
├── API_USAGE.md           # 兼容 API 示例
└── README.md
```

## 说明

- 这个仓库定位是本机或其他 Windows 电脑上的本地部署版本。
- 用户只需要完成 Google Flow 登录。
- 剩余配置和同步由本地服务自动完成。
- 如果账号本身没有 Flow 生图权限或 4K 权限，请求仍然会被上游限制。

## License

MIT
