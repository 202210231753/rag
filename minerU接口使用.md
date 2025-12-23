# MinerU Web API 接口使用说明

本文档基于当前服务暴露的 OpenAPI（`/openapi.json`）整理，适用于 **MinerU Web API** 的文件解析接口。

## 1. 入口与文档

- Swagger 文档：`http://<server_ip>:<port>/docs`
- OpenAPI JSON：`http://<server_ip>:<port>/openapi.json`

> 端口以实际部署为准：如果通过 Docker 映射了 `18000:8000`，则应访问 `http://<server_ip>:18000/docs`。

## 2. 接口概览

- 方法：`POST`
- 路径：`/file_parse`
- Content-Type：`multipart/form-data`
- 必填字段：`files`（数组，可多文件；每个元素为 pdf/图片二进制）
- 成功响应：`200 application/json`（OpenAPI 未声明具体 schema，字段以实际返回为准）
- 失败响应：
  - `422`：请求参数校验失败（FastAPI ValidationError）

## 3. 请求参数（multipart/form-data）

### 3.1 必填

- `files`：文件数组（多文件上传时重复该字段即可）
  - PDF：`application/pdf`
  - 图片：例如 `image/png`、`image/jpeg`

### 3.2 可选（OpenAPI 默认值见括号）

- `output_dir`：输出目录（容器内路径，默认：`./output`）
- `lang_list`：PDF 中可能出现的语言列表（默认：`["ch"]`）
  - 仅对 `backend=pipeline` 更有意义，用于提升 OCR 准确率
  - 可选值示例：`ch`、`en`、`korean`、`japan`、`chinese_cht` 等（完整列表见 OpenAPI 描述）
- `backend`：解析后端（默认：`pipeline`）
  - `pipeline`：更通用
  - `vlm-transformers`：更通用但更慢
  - `vlm-mlx-engine`：需要 Apple Silicon/macOS 13.5+
  - `vlm-vllm-async-engine`：更快（需 vllm）
  - `vlm-lmdeploy-engine`：更快（需 lmdeploy）
  - `vlm-http-client`：通过 OpenAI 兼容服务加速（需 `server_url`）
- `parse_method`：仅对 `backend=pipeline` 生效（默认：`auto`）
  - `auto`：自动判断
  - `txt`：文本抽取
  - `ocr`：OCR（适合扫描版/图片型 PDF）
- `formula_enable`：公式解析（默认：`true`）
- `table_enable`：表格解析（默认：`true`）
- `server_url`：仅对 `backend=vlm-http-client` 生效（默认：`null`）
  - 示例：`http://127.0.0.1:30000`
- 返回控制：
  - `return_md`：返回 Markdown（默认：`true`）
  - `return_middle_json`：返回中间 JSON（默认：`false`）
  - `return_model_output`：返回模型输出 JSON（默认：`false`）
  - `return_content_list`：返回内容列表 JSON（默认：`false`）
  - `return_images`：返回抽取图片（默认：`false`）
  - `response_format_zip`：返回 ZIP 而非 JSON（默认：`false`）
- 页码范围：
  - `start_page_id`：起始页（从 0 开始，默认：`0`）
  - `end_page_id`：结束页（从 0 开始，默认：`99999`）

## 4. 调用示例

以下示例默认 API 基址为 `http://127.0.0.1:18000`，请按实际替换。

### 4.1 最简（单 PDF，返回 JSON）

```bash
curl -sS -X POST "http://127.0.0.1:18000/file_parse" \
  -H "accept: application/json" \
  -F "files=@/path/to/a.pdf;type=application/pdf"
```

### 4.2 多文件 + pipeline 强制 OCR + 多语言

```bash
curl -sS -X POST "http://127.0.0.1:18000/file_parse" \
  -H "accept: application/json" \
  -F "files=@/path/to/a.pdf;type=application/pdf" \
  -F "files=@/path/to/b.png;type=image/png" \
  -F "backend=pipeline" \
  -F "parse_method=ocr" \
  -F "lang_list=ch" \
  -F "lang_list=en" \
  -F "return_md=true"
```

### 4.3 只解析前 3 页（0,1,2）

```bash
curl -sS -X POST "http://127.0.0.1:18000/file_parse" \
  -F "files=@/path/to/a.pdf;type=application/pdf" \
  -F "start_page_id=0" \
  -F "end_page_id=2"
```

### 4.4 返回 ZIP（保存到本地文件）

当 `response_format_zip=true` 时，响应通常是二进制 ZIP，而不是 JSON。

```bash
curl -sS -X POST "http://127.0.0.1:18000/file_parse" \
  -F "files=@/path/to/a.pdf;type=application/pdf" \
  -F "response_format_zip=true" \
  -o "/tmp/mineru_result.zip"
```

### 4.5 Python（requests）

```python
import requests

url = "http://127.0.0.1:18000/file_parse"
with open("/path/to/a.pdf", "rb") as f:
    resp = requests.post(
        url,
        files=[("files", ("a.pdf", f, "application/pdf"))],
        data={
            "backend": "pipeline",
            "parse_method": "auto",
            "return_md": "true",
        },
        timeout=300,
    )
resp.raise_for_status()
print(resp.json())
```

### 4.6 vlm-http-client（通过 OpenAI 兼容服务）

当你有独立的 OpenAI 兼容推理服务（例如 vLLM OpenAI server）时，可配置：

```bash
curl -sS -X POST "http://127.0.0.1:18000/file_parse" \
  -F "files=@/path/to/a.pdf;type=application/pdf" \
  -F "backend=vlm-http-client" \
  -F "server_url=http://127.0.0.1:30000"
```

## 5. 快速自检（可用性验证）

```bash
curl -i "http://127.0.0.1:18000/docs"
curl -sS "http://127.0.0.1:18000/openapi.json" | head
```

若 `curl -i` 返回 `404 {"detail":"Not Found"}`：
- 通常是 **访问了错误端口** 或 **路径写错**（应为 `/docs`、`/file_parse`）。
- 若你同时运行了项目后端（同样可能占用宿主机 `8000`），请确认 Docker 端口映射后再访问。

## 6. 常见问题与建议

- `422`：通常是 `files` 字段名写错、未使用 `multipart/form-data`、或数组字段传参方式不对（多文件需要重复 `-F "files=@..."`）。
- `output_dir`：这是容器内路径；若要在宿主机拿到输出文件，需要给容器挂载 volume 并把 `output_dir` 指向挂载点。
- `start_page_id/end_page_id`：建议在大文档场景下按页切分调用，便于控制耗时与显存峰值。
