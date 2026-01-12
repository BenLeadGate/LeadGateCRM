from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

print("Sende Test-Login...")
resp = client.post("/api/auth/login", data={"username": "ben", "password": "admin123"})
print("Status:", resp.status_code)
print("Response:", resp.text)
