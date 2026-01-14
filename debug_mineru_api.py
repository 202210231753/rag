import requests
import os

# 配置
API_URL = "http://127.0.0.1:18000/file_parse"
TEST_FILE = "debug_test.pdf"

# 创建一个最小的有效 PDF 文件用于测试
def create_dummy_pdf():
    with open(TEST_FILE, "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 612 792]\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n70 50 TD\n/F1 12 Tf\n(Hello, MinerU!) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000117 00000 n\n0000000236 00000 n\n0000000323 00000 n\ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n417\n%%EOF")
    print(f"Created dummy PDF: {TEST_FILE}")

def test_upload(field_name, extra_data=None):
    print(f"\n--- Testing with field name: '{field_name}', data: {extra_data} ---")
    try:
        with open(TEST_FILE, "rb") as f:
            files = {field_name: (TEST_FILE, f, "application/pdf")}
            response = requests.post(API_URL, files=files, data=extra_data, timeout=10)
            
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}") # 只打印前500字符
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            return True
        else:
            print("❌ FAILED")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    create_dummy_pdf()
    
    # 1. 尝试 'file'
    test_upload("file")
    
    # 2. 尝试 'pdf'
    test_upload("pdf")
    
    # 3. 尝试 'file' + 参数
    test_upload("file", {"parse_method": "auto"})
    
    # 4. 尝试 'file' + 完整参数 (参考 MinerU 常见参数)
    test_upload("file", {"is_json_md_dump": "true"})

    # 5. 尝试 'files' (复数)
    test_upload("files")

    # 6. 尝试 'upload_file'
    test_upload("upload_file")

    # 清理
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)
