"""
Test API upload endpoint to verify fraud ring detection
"""

import requests
import json

# File path
file_path = r"C:\Users\Shai\Desktop\לסדר אחכ את כל הקבצים למיין וכו\Home assignments\Riskified TEST\Fraud_Exercise_-_1.xlsx"

print("=" * 80)
print("TESTING API UPLOAD ENDPOINT")
print("=" * 80)

print(f"\n[1] Uploading file to API...")
print(f"    Endpoint: http://localhost:8000/api/v1/upload-and-analyze")

try:
    with open(file_path, 'rb') as f:
        files = {'file': (f'Fraud_Exercise_-_1.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        response = requests.post('http://localhost:8000/api/v1/upload-and-analyze', files=files, timeout=60)

    print(f"\n[2] API Response:")
    print(f"    Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()

        print(f"\n[3] Response Data Structure:")
        print(f"    Keys in response: {list(data.keys())}")

        # Check for organized_fraud field
        if 'organized_fraud' in data:
            organized = data['organized_fraud']
            print(f"\n[4] ORGANIZED FRAUD DETECTION:")
            print(f"    Rings Detected: {organized.get('total_rings_detected', 0)}")

            if organized.get('total_rings_detected', 0) > 0:
                print(f"\n    SUCCESS! Fraud rings are being returned by the API!")
                print(f"\n    First 3 Rings:")
                for i, ring in enumerate(organized.get('rings', [])[:3], 1):
                    print(f"\n    [{i}] {ring.get('ring_name', 'Unknown')}")
                    print(f"        Severity: {ring.get('severity', 'Unknown')}")
                    print(f"        Members: {ring.get('member_count', 0)}")
            else:
                print(f"\n    ERROR: No fraud rings detected by API!")
        else:
            print(f"\n    ERROR: 'organized_fraud' field not in API response!")

    else:
        print(f"\n    ERROR: API returned status code {response.status_code}")
        print(f"    Response: {response.text[:500]}")

except Exception as e:
    print(f"\n    ERROR: {type(e).__name__}: {e}")

print("\n" + "=" * 80)
