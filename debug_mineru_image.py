import requests
import os

# 配置
API_URL = "http://127.0.0.1:18000/file_parse"
TEST_FILE = "debug_test.png"

# 创建一个简单的 PNG 文件
def create_dummy_image():
    # 这是一个 1x1 像素的红色 PNG 图片的 base64 解码内容
    import base64
    img_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    with open(TEST_FILE, "wb") as f:
        f.write(img_data)
    print(f"Created dummy Image: {TEST_FILE}")

def test_upload(field_name):
    print(f"\n--- Testing Image upload with field name: '{field_name}' ---")
    try:
        with open(TEST_FILE, "rb") as f:
            files = {field_name: (TEST_FILE, f, "image/png")}
            response = requests.post(API_URL, files=files, timeout=10)
            
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
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
    create_dummy_image()
    
    # 尝试 'files' (已知 PDF 是用这个)
    test_upload("files")

    # 清理
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)
