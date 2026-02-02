import random
import uuid
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from app.core.database import SessionLocal, engine
from app.models.stats import SearchLog, Base

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def generate_mock_data():
    db = SessionLocal()
    try:
        print("Starting to seed SearchLog data...")
        
        # 1. Clear existing data (Optional, maybe user wants to append? "加入" means add, so maybe just append. But to ensure clean charts, maybe delete? existing data might be empty or valid. I will just append.)
        # db.query(SearchLog).delete()
        # db.commit()
        
        # 2. Configuration
        DAYS_TO_GENERATE = 14
        BASE_USERS = [str(uuid.uuid4()) for _ in range(50)] # 50 distinct users
        QUERIES = [
            "RAG architecture", "Transformer models", "LangChain tutorial",
            "Python async", "FastAPI dependency injection", "Vector database comparison",
            "Milvus vs Pinecone", "Elasticsearch weighting", "React hooks",
            "Ant Design components", "Vite build optimization", "Docker compose networking",
            "CUDA installation linux", "Gradient descent", "Attention mechanism",
            "Prompt engineering techniques", "Llama 3 capabilities", "OpenAI API pricing",
            "Azure cloud services", "Kubernetes deployment"
        ]
        
        # 3. Generate data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=DAYS_TO_GENERATE)
        
        total_records = 0
        
        current_date = start_date
        while current_date <= end_date:
            # Daily volume: Random between 50 and 200, with some "weekend" dip simulation maybe?
            day_volume = random.randint(50, 200)
            
            # Simulate a trend (increasing slightly)
            days_passed = (current_date - start_date).days
            day_volume += days_passed * 10
            
            print(f"Generating {day_volume} records for {current_date.strftime('%Y-%m-%d')}...")
            
            for _ in range(day_volume):
                # Time distribution: concentrate around 9am - 10pm
                hour = random.randint(8, 23)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                log_time = current_date.replace(hour=hour, minute=minute, second=second)
                
                # Random user
                user_id = random.choice(BASE_USERS)
                
                # Random query
                query = random.choice(QUERIES)
                
                # Random latency (0.1s to 2.0s usually, some spikes)
                latency = random.uniform(0.1, 1.5)
                if random.random() < 0.05: # 5% slow queries
                    latency += random.uniform(1.0, 5.0)
                
                # Random status
                status = 1
                if random.random() < 0.02: # 2% error rate
                    status = 0
                    
                log = SearchLog(
                    user_id=user_id,
                    timestamp=log_time,
                    query=query,
                    answer=f"This is a simulated answer for '{query}'...",
                    trace_id=uuid.uuid4().hex,
                    latency=round(latency, 3),
                    status=status
                )
                db.add(log)
                total_records += 1
                
            current_date += timedelta(days=1)
        
        db.commit()
        print(f"Successfully added {total_records} SearchLog records.")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_mock_data()
