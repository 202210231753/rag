import datetime
import random
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.stats import BehaviorLog
from datetime import timedelta

def init_behavior_data():
    db = SessionLocal()
    try:
        # 清除旧数据（可选，视需求而定）
        # db.query(BehaviorLog).delete()
        
        # 生成最近 14 天的数据
        end_date = datetime.datetime.now()
        start_date = end_date - timedelta(days=14)
        
        current = start_date
        records = []
        
        print(f"Generating behavior data from {start_date.date()} to {end_date.date()}...")
        
        while current <= end_date:
            # 基础流量
            base_pv = 1000
            base_uv = 200
            
            # 周末流量略低
            if current.weekday() >= 5:
                factor = 0.7
            else:
                factor = 1.0 + random.uniform(-0.1, 0.2)
                
            pv = int(base_pv * factor * random.uniform(0.9, 1.2))
            uv = int(base_uv * factor * random.uniform(0.9, 1.1))
            # 确保 PV >= UV
            uv = min(uv, pv) 
            
            duration = int(random.uniform(60, 300)) # 60s ~ 300s
            
            log = BehaviorLog(
                timestamp=current,
                pv=pv,
                uv=uv,
                duration=duration
            )
            records.append(log)
            current += timedelta(days=1)
            
        db.add_all(records)
        db.commit()
        print(f"Successfully added {len(records)} behavior logs.")
        
    except Exception as e:
        print(f"Error inserting data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_behavior_data()
