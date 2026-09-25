import os
import sys
import requests

repo = os.environ.get("GITHUB_REPOSITORY")
token = os.environ.get("GITHUB_TOKEN")
run_id = os.environ.get("GITHUB_RUN_ID")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

# 1. Check if the current workflow run was cancelled manually
if repo and token and run_id:
    try:
        run_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
        response = requests.get(run_url, headers=headers)
        if response.status_code == 200:
            run_data = response.json()
            conclusion = run_data.get("conclusion")
            
            if conclusion == "cancelled":
                print("--> [CHECK STATUS] Workflow was manually CANCELLED. Stopping auto-chain.")
                sys.exit(0)
    except Exception as e:
        print(f"--> [CHECK STATUS] Could not check run conclusion: {e}")

# 2. Read emails from emails.txt
if not os.path.exists("emails.txt"):
    print("--> [CHECK STATUS] emails.txt not found. Exiting cleanly.")
    sys.exit(0)

with open("emails.txt", "r", encoding="utf-8") as f:
    raw_emails = f.read()

all_emails = [e.strip() for e in raw_emails.replace(",", " ").split() if e.strip()]
total_emails = len(all_emails)

# 3. Read completed accounts count
completed_count = 0
if os.path.exists("completed_accounts.txt"):
    with open("completed_accounts.txt", "r", encoding="utf-8") as f:
        completed_count = len([line for line in f.readlines() if line.strip()])

print(f"--> [CHECK STATUS] Total Accounts: {total_emails} | Completed: {completed_count}")

# 4. Trigger next run ONLY if accounts are pending AND it was NOT cancelled
if completed_count < total_emails:
    print("--> [CHECK STATUS] Pending accounts remain! Triggering next workflow run...")
    
    if repo and token:
        dispatch_url = f"https://api.github.com/repos/{repo}/actions/workflows/run_bot.yml/dispatches"
        data = {"ref": "main"}
        
        res = requests.post(dispatch_url, headers=headers, json=data)
        if res.status_code == 204:
            print("--> [SUCCESS] Next workflow run triggered successfully!")
        else:
            print(f"--> [ERROR] Failed to trigger dispatch: {res.status_code} - {res.text}")
else:
    print("--> [CHECK STATUS] All accounts have reached their daily limit! Stopping loop completely.")
  
