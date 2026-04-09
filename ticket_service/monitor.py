import asyncio
import random
import httpx

async def start_monitoring():
    print("🚦 SmartCity Monitoring System Started...")
    
    # Infinite loop jo background me chalega
    while True:
        await asyncio.sleep(10) # Har 10 second me check karega
        
        # Simulate a random failure (e.g., 20% chance a camera goes offline)
        if random.random() < 0.2:
            faulty_device = f"CAM-{random.randint(100, 999)}"
            print(f"⚠️ ALERT: Monitoring detected failure at {faulty_device}!")
            
            # Auto-Create Ticket Data
            alert_data = {
                "issue_type": "Camera Offline / Connection Lost",
                "location": "Highway Node",
                "device_id": faulty_device,
                "severity": "high"
            }
            
            # API Call lagakar khud hi ticket raise kar dega
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post("http://127.0.0.1:8000/api/v1/tickets/", json=alert_data)
                    if response.status_code == 200:
                        print(f"✅ Auto-Ticket Generated: ID #{response.json()['ticket_id']}")
                except Exception as e:
                    print(f"❌ Failed to auto-generate ticket: {e}")