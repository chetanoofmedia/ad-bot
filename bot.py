import os
import time
import signal
import sys
from playwright.sync_api import sync_playwright

current_context = None
STEALTH_JS = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"

def shutdown_handler(sig, frame):
    global current_context
    if current_context:
        try:
            current_context.close()
        except Exception:
            pass
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

raw_emails = ""
if os.path.exists("emails.txt"):
    with open("emails.txt", "r", encoding="utf-8") as f:
        raw_emails = f.read()
else:
    raw_emails = os.environ.get("ALL_EMAILS", "")

email_password = os.environ.get("ACCOUNT_PASSWORD", "Chetan@2026")
ALL_EMAILS = [e.strip().lower() for e in raw_emails.replace(",", " ").split() if e.strip()]

shard_index = int(os.environ.get("SHARD_INDEX", "1"))
total_shards = int(os.environ.get("TOTAL_SHARDS", "1"))
shard_file = f"completed_accounts_shard_{shard_index}.txt"

completed_set = set()
for s in range(1, total_shards + 1):
    s_file = f"completed_accounts_shard_{s}.txt"
    if os.path.exists(s_file):
        with open(s_file, "r", encoding="utf-8") as f:
            completed_set.update({line.strip().lower() for line in f if line.strip()})

PENDING_EMAILS = [e for e in ALL_EMAILS if e not in completed_set]
SHARD_ASSIGNED_EMAILS = [e for idx, e in enumerate(PENDING_EMAILS) if idx % total_shards == (shard_index - 1)]

if not SHARD_ASSIGNED_EMAILS:
    print(f"--> [SHARD {shard_index}] No pending accounts. Exiting...")
    sys.exit(0)

ACCOUNTS = [{"id": i + 1, "email": email, "password": email_password} for i, email in enumerate(SHARD_ASSIGNED_EMAILS)]
TARGET_BATCH_SIZE = 5

def purge_popups(page):
    try:
        page.keyboard.press("Escape")
        page.evaluate("""() => {
            const dialogs = Array.from(document.querySelectorAll('div[role="dialog"], [class*="modal"], [class*="popup"]'));
            dialogs.forEach(d => {
                const isLogin = d.querySelector('input[placeholder*="email" i], input[type="email"]') || (d.textContent && d.textContent.includes('Sign in'));
                if (!isLogin) {
                    const closeBtn = d.querySelector('button, [class*="close"], svg, i');
                    if (closeBtn) closeBtn.click();
                }
            });
        }""")
    except Exception:
        pass

def force_unpause_videos(page):
    try:
        page.evaluate("""() => {
            document.querySelectorAll('video').forEach(v => { v.muted = true; v.play().catch(e => {}); });
            document.querySelectorAll('iframe').forEach(f => {
                try { if (f.contentDocument) f.contentDocument.querySelectorAll('video').forEach(v => { v.muted = true; v.play().catch(e => {}); }); } catch(e) {}
            });
        }""")
    except Exception:
        pass

def check_daily_limit_reached(page):
    try:
        limit_text = "You have used all your ad watch opportunities for today"
        for frame in page.frames:
            if frame.get_by_text(limit_text, exact=False).count() > 0:
                return True
    except Exception:
        pass
    return False

def click_close_button(page):
    print("--> Waiting to close ad player...")
    for attempt in range(12):
        force_unpause_videos(page)
        page.wait_for_timeout(1000)
        try:
            closed = page.evaluate("""() => {
                function clickClose(doc) {
                    const els = Array.from(doc.querySelectorAll('*'));
                    for (let el of els) {
                        const txt = (el.textContent || '').trim().toLowerCase();
                        if (txt === 'close' || txt === '×' || (el.id && el.id.toLowerCase().includes('dismiss'))) {
                            if (el.offsetWidth > 0 && el.offsetHeight > 0) { el.click(); return true; }
                        }
                    }
                    return false;
                }
                if (clickClose(document)) return true;
                for (let f of document.querySelectorAll('iframe')) {
                    try { if (f.contentDocument && clickClose(f.contentDocument)) return true; } catch(e) {}
                }
                return false;
            }""")
            if closed:
                print("--> [SUCCESS] Ad player closed!")
                return True
        except Exception:
            pass
        if attempt >= 3:
            for cx, cy in [(1515, 235), (1520, 240), (1500, 230)]:
                try: page.mouse.click(cx, cy)
                except Exception: pass
    page.goto("https://easemate.ai/earn-credits", wait_until="load")
    return True

def click_ok_button(page):
    page.wait_for_timeout(1000)
    for _ in range(3):
        try:
            page.keyboard.press("Enter")
            ok_clicked = page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"], a, span'));
                for (let btn of btns) {
                    const txt = btn.textContent ? btn.textContent.trim().toLowerCase() : '';
                    if (['ok', 'claim', 'confirm', 'got it'].includes(txt) && btn.offsetWidth > 0) { btn.click(); return true; }
                }
                return false;
            }""")
            if ok_clicked: return True
        except Exception: pass
        page.wait_for_timeout(500)
    return True

def click_watch_ad(page):
    try:
        page.wait_for_timeout(2000)
        purge_popups(page)
        card = page.locator("div").filter(has_text="Watch ad to earn credits").last
        if card.count() > 0:
            card.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            go_btn = card.get_by_text("Go Now", exact=False).last
            if go_btn.is_visible():
                box = go_btn.bounding_box()
                if box:
                    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                else:
                    go_btn.click(force=True)

        page.wait_for_timeout(3000)
        has_ad = page.evaluate("""() => {
            const hasVid = document.querySelector('video, [id*="goog_fullscreen"], [src*="googleads"]');
            const hasModal = document.querySelector('div[role="dialog"], [class*="modal-open"]');
            return !!(hasVid || hasModal);
        }""")
        if has_ad:
            print("--> [SUCCESS] Ad launched!")
            force_unpause_videos(page)
            return True
    except Exception as e:
        print(f"--> Error clicking watch ad: {e}")
    return False

def process_single_account(page, account):
    email = account["email"]
    password = account["password"]
    print(f"--- Logging into: {email} ---")
    page.goto("https://easemate.ai/Dashboard", wait_until="load")
    page.wait_for_timeout(1000)
    purge_popups(page)

    page.get_by_text("Log In", exact=True).first.click()
    page.wait_for_timeout(1000)

    try:
        if page.get_by_text("Continue with Email", exact=True).is_visible():
            page.get_by_text("Continue with Email", exact=True).click()
            page.wait_for_timeout(1000)
    except Exception:
        pass

    page.wait_for_selector("input[placeholder='Enter your email address']")
    page.fill("input[placeholder='Enter your email address']", email)
    page.fill("input[placeholder='Enter your Password']", password)
    page.get_by_role("button", name="Log in").last.click()
    page.wait_for_timeout(4000)

    print(f"[{email}] Navigating to Earn Credits page...")
    page.goto("https://easemate.ai/earn-credits", wait_until="load")
    page.wait_for_timeout(3000)
    purge_popups(page)
    page.mouse.wheel(0, 500)

    if check_daily_limit_reached(page):
        print(f"[{email}] LIMIT DETECTED!")
        return "LIMIT_REACHED"

    ad_started = False
    for attempt in range(3):
        if click_watch_ad(page):
            ad_started = True
            break
        print(f"[{email}] Retrying ad launch ({attempt + 1}/3)...")
        page.goto("https://easemate.ai/earn-credits", wait_until="load")
        page.wait_for_timeout(2000)
        page.mouse.wheel(0, 500)

    if not ad_started:
        print(f"[{email}] ERROR: Failed to launch ad.")
        return "ERROR"

    print(f"[{email}] Watching video ad (35s)...")
    for _ in range(7):
        force_unpause_videos(page)
        time.sleep(5)

    click_close_button(page)
    click_ok_button(page)
    print(f"[{email}] SUCCESS: Reward claimed!")
    return "SUCCESS"

def run_all_accounts():
    global current_context
    remaining_pool = list(ACCOUNTS)
    active_batch = []
    last_ad_completion_time = {}

    while remaining_pool and len(active_batch) < TARGET_BATCH_SIZE:
        active_batch.append(remaining_pool.pop(0))

    current_idx = 0
    os.makedirs("videos", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
        )

        while active_batch:
            if current_idx >= len(active_batch):
                current_idx = 0

            account = active_batch[current_idx]
            email = account["email"]

            COOLDOWN_SECONDS = 180
            if email in last_ad_completion_time:
                elapsed = time.time() - last_ad_completion_time[email]
                if elapsed < COOLDOWN_SECONDS:
                    wait_needed = int(COOLDOWN_SECONDS - elapsed) + 1
                    print(f"--> [3-MIN COOLDOWN] Pausing {wait_needed}s for {email}...")
                    time.sleep(wait_needed)

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_video_dir="videos/",
                record_video_size={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            page.add_init_script(STEALTH_JS)
            current_context = context

            try:
                status = process_single_account(page, account)
            except Exception as e:
                print(f"Error on {email}: {e}")
                status = "ERROR"

            context.close()
            current_context = None

            if status == "SUCCESS":
                last_ad_completion_time[email] = time.time()
                current_idx += 1
            elif status == "LIMIT_REACHED":
                finished_acc = active_batch.pop(current_idx)
                with open(shard_file, "a", encoding="utf-8") as f:
                    f.write(f"{finished_acc['email']}\n")
                if remaining_pool:
                    active_batch.insert(current_idx, remaining_pool.pop(0))
            else:
                current_idx += 1
                time.sleep(1)

        browser.close()

if __name__ == "__main__":
    run_all_accounts()
    
