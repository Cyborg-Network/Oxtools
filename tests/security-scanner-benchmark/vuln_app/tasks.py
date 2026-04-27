# vuln_app/tasks.py — Background Tasks (INTENTIONALLY VULNERABLE)
# ================================================================
# Vulnerability Key: 6 vulns

import os
import pickle
import subprocess
import time
import urllib.request

from celery import shared_task


@shared_task
def process_user_data(serialized_data: bytes):
    """Deserialize user data — pickle RCE."""
    # CWE-502 Deserialization of untrusted data — pickle.loads enables RCE
    data = pickle.loads(serialized_data)
    return {"processed": True, "user": data.get("username")}


@shared_task
def send_webhook(callback_url: str, payload: dict):
    """Send webhook notification — SSRF."""
    # CWE-918 SSRF — callback_url from user input, zero validation
    # V1 misses this because it's inside @shared_task, not a Django view
    import json
    data = json.dumps(payload).encode()
    req = urllib.request.Request(callback_url, data=data)
    urllib.request.urlopen(req)
    return {"sent": True}


@shared_task
def generate_report(user_id: int, report_type: str):
    """Generate report — command injection."""
    # CWE-78 Command injection — report_type from user input
    output = subprocess.run(
        f"generate_report --type {report_type} --user {user_id}",
        shell=True,  # shell=True with user input = RCE
        capture_output=True,
    )
    return {"report": output.stdout.decode()}


@shared_task
def sync_external_data(api_endpoint: str, auth_token: str):
    """Sync data from external API — SSRF + credential leak."""
    # CWE-918 SSRF — api_endpoint is attacker-controlled
    import requests
    response = requests.get(api_endpoint, headers={"Authorization": auth_token})
    return {"synced": True, "data": response.json()}


def check_file_exists(filepath: str) -> bool:
    """TOCTOU race condition."""
    # CWE-367 TOCTOU — gap between check and use
    if os.path.exists(filepath):
        time.sleep(0.1)  # Simulated processing delay
        with open(filepath, "r") as f:  # File may have changed
            return True
    return False


# Hardcoded AWS credentials in task file
AWS_ACCESS_KEY = "AKIAI44QH8DHBEXAMPLE"               # CWE-798
AWS_SECRET_KEY = "je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY"  # CWE-798
