import os
import sys
import time
import subprocess
import requests

repo = os.environ.get("GITHUB_REPOSITORY")
token = os.environ.get("GITHUB_TOKEN")
run_id = os.environ.get("GITHUB_RUN_ID")
total_shards = int(os.environ.get("TOTAL_SHARDS", "8"))

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

print("==========================================================")
print("              STARTING CHECK STATUS ENGINE               ")
print("==========================================================")

# 1. Stop if workflow was manually cancelled
if repo and token and run_id:
    try:
        run_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
        response = requests.get(run_url, headers=headers)
        if response.status_code == 200:
            run_data = response.json()
            if run_data.get("conclusion") == "cancelled":
                print("--> [CHECK STATUS] Workflow was manually CANCELLED. Stopping auto-chain.")
                sys.exit(0)
    except Exception as e:
        print(f"--> [CHECK STATUS] Warning: Could not check run conclusion: {e}")

# 2. Pull latest git changes to aggregate all shard tracking files
try:
    subprocess.run(["git", "fetch", "origin", "main"], check=False)
    subprocess.run(["git", "rebase", "origin/main"], check=False)
except Exception as e:
    print(f"--> [CHECK STATUS] Note: Git sync check: {e}")

# 3. Check for ALL_DONE lock file
if os.path.exists("ALL_DONE.txt"):
    print("--> [CHECK STATUS] ALL_DONE.txt lock found! All accounts completed successfully.")
    print("--> Stopping workflow loop permanently for today.")
    sys.exit(0)

# 4. Read emails from emails.txt
if not os.path.exists("emails.txt"):
    print("--> [CHECK STATUS] ERROR: emails.txt not found. Exiting cleanly.")
    sys.exit(0)

with open("emails.txt", "r", encoding="utf-8") as f:
    raw_emails = f.read()

all_emails = [e.strip().lower() for e in raw_emails.replace(",", " ").split() if e.strip()]
total_emails = len(all_emails)

# 5. Read completed accounts across ALL shard files
completed_emails = set()

for s in range(1, total_shards + 1):
    s_file = f"completed_accounts_shard_{s}.txt"
    if os.path.exists(s_file):
        with open(s_file, "r", encoding="utf-8") as f:
            completed_emails.update({line.strip().lower() for line in f if line.strip()})

if os.path.exists("completed_accounts.txt"):
    with open("completed_accounts.txt", "r", encoding="utf-8") as f:
        completed_emails.update({line.strip().lower() for line in f if line.strip()})

completed_count = len(completed_emails)
pending_count = total_emails - completed_count

print(f"--> [CHECK STATUS] Total Accounts in List: {total_emails}")
print(f"--> [CHECK STATUS] Completed Accounts:    {completed_count}")
print(f"--> [CHECK STATUS] Pending Accounts:      {pending_count}")

# 6. Trigger next run ONLY if accounts remain
if total_emails > 0 and completed_count < total_emails:
    print(f"--> [CHECK STATUS] {pending_count} accounts remaining! Pausing 10s to let other matrix shards complete before dispatching...")
    time.sleep(10)
    
    if repo and token:
        dispatch_url = f"https://api.github.com/repos/{repo}/actions/workflows/run_bot.yml/dispatches"
        res = requests.post(dispatch_url, headers=headers, json={"ref": "main"})
        
        if res.status_code == 204:
            print("--> [SUCCESS] Single dispatch request sent! Next parallel workflow run triggered successfully.")
        else:
            print(f"--> [ERROR] Failed to trigger dispatch: {res.status_code} - {res.text}")
    else:
        print("--> [ERROR] GITHUB_REPOSITORY or GITHUB_TOKEN environment variables missing!")
else:
    print("--> [CHECK STATUS] All accounts completed across all shards! Writing ALL_DONE.txt...")
    with open("ALL_DONE.txt", "w", encoding="utf-8") as f:
        f.write("DONE\n")
    
    try:
        subprocess.run(["git", "add", "ALL_DONE.txt"], check=False)
        subprocess.run(["git", "commit", "-m", "update: marked ALL_DONE"], check=False)
        subprocess.run(["git", "push", "origin", "HEAD:main"], check=False)
    except Exception as e:
        print(f"--> Error pushing ALL_DONE.txt: {e}")
