# 同义词数据获取快速指南

## 🎯 快速获取大规模同义词数据

### 推荐方案（按优先级）

#### 1. 同义词词林（Cilin）- 最推荐 ⭐⭐⭐⭐⭐

**数据特点**：
- 数据量大：通常包含 5,000-20,000+ 个同义词组
- 质量高：权威的中文同义词词典
- 格式标准：A01A01= 词1 词2 词3 ...

**获取方式**：

```bash
# 方式1：GitHub 搜索（推荐）
# 在 GitHub 搜索：cilin OR 同义词词林
# 或访问：https://github.com/search?q=cilin+chinese

# 方式2：使用 GitHub CLI（如果已安装）
gh repo search 'cilin' --limit 10

# 方式3：直接下载（如果找到公开链接）
wget -O data/cilin.txt https://example.com/cilin.txt
```

**导入步骤**：
```bash
# 1. 检查文件格式
python scripts/check_data_format.py data/cilin.txt

# 2. 转换格式
python scripts/convert_cilin_format.py \
    --input data/cilin.txt \
    --output data/synonyms.json \
    --domain default

# 3. 导入数据库
python scripts/init_synonyms.py \
    --file data/synonyms.json \
    --domain default \
    --force
```

---

#### 2. Synonyms 中文同义词工具包 ⭐⭐⭐⭐

**数据特点**：
- Python 库，包含大量同义词数据
- 易于使用，可直接提取数据

**获取方式**：
```bash
# 安装库
pip install synonyms

# 或从 GitHub 克隆
git clone https://github.com/chatopera/Synonyms.git
```

**使用方式**：
```python
import synonyms
synonyms.nearby("Python")  # 获取同义词
```

---

#### 3. CSDN 中文同义词词库 ⭐⭐⭐

**数据特点**：
- 约 3 万条同义词和近义词
- 格式通常为 CSV 或 TXT

**获取方式**：
- 访问：https://download.csdn.net/download/qq_36758270/88243480
- 需要登录 CSDN 账号
- 下载后解压到 `data/` 目录

---

## 📋 完整的导入流程

### 步骤1：获取数据文件

选择一个数据源，下载到 `data/` 目录

### 步骤2：检查数据格式

```bash
python scripts/check_data_format.py data/your_file.txt
```

### 步骤3：转换格式（如果需要）

如果是同义词词林格式：
```bash
python scripts/convert_cilin_format.py \
    --input data/your_file.txt \
    --output data/synonyms.json \
    --domain default \
    --min-synonyms 1  # 过滤掉同义词太少的组
```

如果是 CSV 格式，需要使用 API 导入（见下方）

### 步骤4：导入数据库

```bash
python scripts/init_synonyms.py \
    --file data/synonyms.json \
    --domain default \
    --force  # 如果已有数据需要重新导入
```

### 步骤5：验证导入结果

```bash
# 检查导入数量
python scripts/init_synonyms.py --domain default --check-only

# 或使用查询脚本
python query_synonyms.py
```

---

## 🔧 实用工具脚本

项目已提供以下工具脚本：

1. **`scripts/download_synonyms_info.py`**
   - 查看数据源信息和获取方式

2. **`scripts/check_data_format.py`**
   - 检查数据文件格式是否正确

3. **`scripts/convert_cilin_format.py`**
   - 转换同义词词林格式为系统格式

4. **`scripts/init_synonyms.py`**
   - 导入 JSON 格式数据到数据库

5. **`scripts/fetch_cilin_example.sh`**
   - 数据获取命令示例

---

## 📊 预期数据量参考

| 数据源 | 预计组数 | 适用场景 |
|--------|---------|---------|
| 小型测试 | 10-100 | 功能测试 |
| 基础词林 | 1,000-5,000 | 一般应用 |
| 扩展词林 | 5,000-20,000 | 生产环境 |
| 大规模词库 | 20,000+ | 企业级应用 |

---

## ⚠️ 注意事项

1. **版权问题**：确保数据源允许使用
2. **数据质量**：优先选择权威数据源
3. **编码格式**：确保文件是 UTF-8 编码
4. **性能考虑**：大量数据导入可能需要较长时间

---

## 🆘 常见问题

### Q: 如何找到公开的同义词词林数据？

A: 
- 在 GitHub 搜索 "cilin" 或 "同义词词林"
- 访问哈工大语言技术平台
- 查看学术数据集网站

### Q: 数据格式不匹配怎么办？

A: 
- 使用 `check_data_format.py` 检查格式
- 如果是 CSV，可以使用 API 的 `batch_import_file` 接口
- 如果是其他格式，需要编写转换脚本

### Q: 导入失败怎么办？

A: 
- 检查数据库连接
- 查看错误日志
- 确保文件编码正确（UTF-8）
- 检查数据格式是否正确

---

## 📚 更多信息

详细文档请查看：`docs/同义词数据源获取指南.md`









