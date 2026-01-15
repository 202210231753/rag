from typing import List
import torch
import random
from transformers import AutoModel, AutoTokenizer, AutoModelForCausalLM

class AIModelClient:
    def __init__(self):
        # 用户提供的路径
        self.emb_model_path = "/home/yl/yl/yl/code-llm/Qwen/Qwen3-Embedding-0.6B"
        self.llm_model_path = "/home/yl/yl/yl/code-llm/Qwen/Qwen3-4B-Instruct-2507"
        
        # 检查 GPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"AIModelClient initialized. Target device: {self.device}")

        # 加载 Embedding 模型
        try:
            print(f"Loading Embedding Model from: {self.emb_model_path}")
            self.emb_tokenizer = AutoTokenizer.from_pretrained(self.emb_model_path, trust_remote_code=True)
            # 尽可能尝试使用 device_map="auto"，否则回退到 .to(device)
            try:
                self.emb_model = AutoModel.from_pretrained(self.emb_model_path, device_map="auto", trust_remote_code=True)
            except Exception:
                self.emb_model = AutoModel.from_pretrained(self.emb_model_path, trust_remote_code=True).to(self.device)
            self.use_real_emb = True
            print("Embedding Model loaded successfully.")
        except Exception as e:
            print(f"Failed to load Embedding Model: {e}. Using mock.")
            self.use_real_emb = False

        # 加载 LLM
        try:
            print(f"Loading LLM from: {self.llm_model_path}")
            self.llm_tokenizer = AutoTokenizer.from_pretrained(self.llm_model_path, trust_remote_code=True)
            try:
                self.llm_model = AutoModelForCausalLM.from_pretrained(self.llm_model_path, device_map="auto", trust_remote_code=True, torch_dtype="auto")
            except Exception:
                self.llm_model = AutoModelForCausalLM.from_pretrained(self.llm_model_path, trust_remote_code=True, torch_dtype="auto").to(self.device)
            self.use_real_llm = True
            print("LLM loaded successfully.")
        except Exception as e:
            print(f"Failed to load LLM: {e}. Using mock.")
            self.use_real_llm = False

    def get_embedding(self, text: str) -> List[float]:
        if not self.use_real_emb:
            # 模拟
            random.seed(len(text))
            return [random.random() for _ in range(10)]
            
        # 真实
        inputs = self.emb_tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        # 将输入移动到模型设备
        inputs = {k: v.to(self.emb_model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.emb_model(**inputs)
            # 使用 last_hidden_state 平均池化
            embeddings = outputs.last_hidden_state.mean(dim=1)
            # 归一化以用于余弦相似度
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            
        return embeddings[0].tolist()

    def analyze_user_intent(self, dialogue: str) -> str:
        if not self.use_real_llm:
            # 模拟
            if "help" in dialogue.lower():
                return "support"
            elif "buy" in dialogue.lower() or "price" in dialogue.lower():
                return "purchase"
            return "informational"

        # 真实
        messages = [
            {"role": "system", "content": "You are an assistant that analyzes user intent. Classify the user intent into one of these categories: 'support' (seeking help), 'purchase' (buying intent), or 'informational' (general query). Return ONLY the category name, nothing else."},
            {"role": "user", "content": dialogue}
        ]
        text = self.llm_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = self.llm_tokenizer([text], return_tensors="pt").to(self.llm_model.device)
        
        with torch.no_grad():
            generated_ids = self.llm_model.generate(
                **model_inputs,
                max_new_tokens=10,
                do_sample=False,  # 确定性
                temperature=0.01
            )
            # 仅提取新生成的 token
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            response = self.llm_tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
        response = response.strip().lower()
        if "support" in response: return "support"
        if "purchase" in response: return "purchase"
        if "informational" in response: return "informational"
        # 如果模型输出其他内容，则回退
        return "informational"
