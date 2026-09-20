import os
import time
from playwright.sync_api import sync_playwright

# ============================================================
# LOAD CREDENTIALS FROM GITHUB SECRETS OR FALLBACK LIST
# ============================================================
raw_emails = os.environ.get("ALL_EMAILS", "")
email_password = os.environ.get("ACCOUNT_PASSWORD", "Mansi@1996")

if raw_emails.strip():
    ALL_EMAILS = [e.strip() for e in raw_emails.replace(",", " ").split() if e.strip()]
else:
    ALL_EMAILS = [
        "kowimu@denipl.net", "namezyxo@denipl.net", "zyqaqy@denipl.net",
        "fojofi9071@dreameg.com", "xadyhi@forexzig.com", "mycukugu@fxzig.com",
        "jojeqegu@fxzig.com", "qisadiri@denipl.net", "qizuwuvo@forexzig.com",
        "taxegocu@fxzig.com", "gujybeci@denipl.net", "juhuraki@denipl.net",
        "ciforuva@denipl.net", "jafasa@fxzig.com", "buzyka@fxzig.com",
        "gahivan368@jobscai.com", "6z181rxr1e@yzcalo.com", "ybc80on8sc@lnovic.com",
        "ztlptskko0@fpklm.com", "gcyb2qe385@fpklm.com", "4tlomtzyll@fpklm.com",
        "sti17yrntn@fpklm.com", "03v8k1gelr@fpklm.com", "h3w2g8ts62@fpklm.com",
        "es8ea9c4rq@fpklm.com", "asxxig3fb8@fpklm.com", "4uwexfl87i@fpklm.com",
        "krhjv2szsm@fpklm.com", "igmed713nt@fpklm.com", "vnzsam39xj@fpklm.com",
        "tipsunorte@necub.com", "nodrelatri@necub.com", "burduyusti@necub.com",
        "ladroyurta@necub.com", "custujadra@necub.com", "tortebagnu@necub.com",
        "kardojopsu@necub.com", "5cbraq7oop@fpklm.com", "vapuk7tqav@fpklm.com",
        "ynbjdluz8t@fpklm.com", "oo3azfzmrb@fpklm.com", "hcss5i76co@fpklm.com",
        "smpqce43ny@fpklm.com", "odimwutqlu@fpklm.com", "cnedbyjv4n@fpklm.com",
        "56p7q75ycb@fpklm.com", "0d499wkj64@fpklm.com", "0n0jn4vl7h@fpklm.com",
        "bqi5p43xwg@fpklm.com", "qsvcbtcm17@fpklm.com", "wdr65seq2b@gmeenramy.com",
        "3w8n6svrmu@gmeenramy.com", "5ym3haze8q@ruutukf.com", "ll82zko8wz@yzcalo.com",
        "cso21mh0s0@yzcalo.com", "9ojp4fpw6o@ruutukf.com", "7xtmhjpntl@gmeenramy.com",
        "ox6af7cks3@ruutukf.com", "p4bsqnp48w@fpklm.com", "58fy9273ok@fpklm.com",
        "wdqhy1n32g@fpklm.com", "7d7osqmvx4@fpklm.com", "k0ayhjh6pj@fpklm.com",
        "1shljho9ct@fpklm.com", "tka4fg4gbh@fpklm.com", "c06l8fh5cr@fpklm.com",
        "tzud0gclrl@fpklm.com", "xov2wtt5l4@fpklm.com", "c2q4a6ef0y@fpklm.com",
        "ub5ugi7lyi@fpklm.com", "reydavirte@necub.com", "kilmagitro@necub.com",
        "mistodispu@necub.com", "borkosufye@necub.com", "zudrobiknu@necub.com",
        "dispabofyu@necub.com", "tokneralmu@necub.com", "fuknonakno@necub.com",
        "zatricekku@necub.com", "xeoapq1rw6@yzcalo.com", "yw423x2d2s@ooynib.com"
    ]

ACCOUNTS = [{"email": email, "password": email_password} for email in ALL_EMAILS]
TARGET_BATCH_SIZE = 5


# ============================================================
# AUTOMATION HELPER FUNCTIONS
# ============================================================

def purge_popups(page):
    """Removes floating ad widgets and modal backdrops."""
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    except Exception:
        pass

    try:
        page.evaluate("""() => {
            const badPhrases = [
                'Celebrity Twin Finder', 
                'Find Your Star', 
                'GPT Image 2.5', 
                "WHAT'S NEW"
            ];
            
            const allNodes = Array.from(document.querySelectorAll('*'));
            allNodes.forEach(el => {
                if (el.children.length === 0 && badPhrases.some(p => el.textContent.includes(p))) {
                    let container = el;
                    for (let i = 0; i < 8; i++) {
                        if (!container || container === document.body) break;
                        const style = window.getComputedStyle(container);
                        if (style.position === 'fixed' || style.position === 'absolute' || container.getAttribute('role') === 'dialog') {
                            container.remove();
                            break;
                        }
                        container = container.parentElement;
                    }
                }
            });

            const overlays = document.querySelectorAll('[class*="backdrop"], [class*="overlay"], div[role="dialog"]');
            overlays.forEach(o => o.remove());
        }""")
    except Exception:
        pass


def check_daily_limit_reached(page):
    """Checks if the daily limit toast alert appears on page."""
    try:
        limit_text = "You have used all your ad watch opportunities for today"
        for frame in page.frames:
            element = frame.get_by_text(limit_text, exact=False)
            if element.count() > 0 and element.first.is_visible():
                return True
    except Exception:
        pass
    return False


def click_close_button(page):
    """Finds all visible 'Close' elements after watching an ad and clicks them."""
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    except Exception:
        pass

    for frame in page.frames:
        locators = [
            frame.get_by_text("Close", exact=True),
            frame.locator("text=/^close$/i"),
            frame.locator("button:has-text('Close')"),
            frame.locator("[role='button']:has-text('Close')")
        ]
        for loc in locators:
            try:
                count = loc.count()
                for i in range(count):
                    element = loc.nth(i)
                    if element.is_visible():
                        box = element.bounding_box()
                        if box:
                            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                            page.wait_for_timeout(1000)
                            return True
            except Exception:
                pass

    return False


def click_ok_button(page):
    """Clicks the credit reward OK button across main page and frames."""
    page.wait_for_timeout(1500)
    for frame in page.frames:
        locators = [
            frame.get_by_role("button", name="OK"),
            frame.get_by_text("OK", exact=True),
            frame.locator("text=/^ok$/i")
        ]
        for loc in locators:
            try:
                count = loc.count()
                for i in range(count):
                    element = loc.nth(i)
                    if element.is_visible():
                        element.click(force=True)
                        return True
            except Exception:
                pass
    return False


def click_watch_ad(page):
    """Locates and clicks 'Go Now' inside the Watch Ad card."""
    try:
        clicked = page.evaluate("""() => {
            const allElements = Array.from(document.querySelectorAll('*'));
            const watchAdTitle = allElements.find(el =>
                el.children.length === 0 && el.textContent.includes('Watch ad to earn credits')
            );
            if (!watchAdTitle) return false;

            let card = watchAdTitle;
            while (card && card.parentElement && !card.textContent.includes('10 ads/day')) {
                card = card.parentElement;
            }
            if (!card) card = watchAdTitle.closest('div');
            if (!card) return false;

            const elements = Array.from(card.querySelectorAll('*'));
            const goNowBtn = elements.find(el =>
                el.textContent.trim().toLowerCase().includes('go now')
            );

            if (!goNowBtn) return false;

            goNowBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
            goNowBtn.click();
            return true;
        }""")
        if clicked:
            return True
    except Exception:
        pass

    try:
        page.locator("div").filter(has_text="Watch ad to earn credits").get_by_text("Go Now").last.click(force=True)
        return True
    except Exception:
        pass

    return False


# ============================================================
# SINGLE ACCOUNT EXECUTION
# ============================================================

def process_single_account(page, account):
    email = account["email"]
    password = account["password"]

    print(f"--- Logging into: {email} ---")
    page.goto("https://easemate.ai/Dashboard", wait_until="load")
    page.wait_for_timeout(3000)

    # 1. Login
    page.get_by_text("Log In", exact=True).first.click()
    page.wait_for_timeout(1000)

    try:
        email_option = page.get_by_text("Continue with Email", exact=True)
        if email_option.is_visible():
            email_option.click()
            page.wait_for_timeout(1000)
    except Exception:
        pass

    page.wait_for_selector("input[placeholder='Enter your email address']")
    page.fill("input[placeholder='Enter your email address']", email)
    page.fill("input[placeholder='Enter your Password']", password)
    page.get_by_role("button", name="Log in").last.click()
    page.wait_for_timeout(4000)

    # 2. Earn Credits
    print(f"[{email}] Navigating to Earn Credits page...")
    page.goto("https://easemate.ai/earn-credits", wait_until="load")
    page.wait_for_timeout(4000)

    # 3. Purge floating widgets & Scroll
    purge_popups(page)
    page.wait_for_timeout(1000)

    # Check limit immediately on page load
    if check_daily_limit_reached(page):
        print(f"[{email}] LIMIT DETECTED: Account has used all ad opportunities for today!")
        return "LIMIT_REACHED"

    page.mouse.wheel(0, 500)
    page.wait_for_timeout(1000)

    # 4. Click Go Now
    print(f"[{email}] Starting ad task...")
    purge_popups(page)
    if not click_watch_ad(page):
        print(f"[{email}] ERROR: Could not click 'Go Now'. Skipping...")
        return "ERROR"

    # 5. Check if Daily Limit Toast Appears after clicking "Go Now"
    page.wait_for_timeout(2000)
    if check_daily_limit_reached(page):
        print(f"[{email}] LIMIT DETECTED: 'You have used all your ad watch opportunities for today.'")
        return "LIMIT_REACHED"

    # 6. Wait for Video Playback (32 seconds)
    print(f"[{email}] Watching video ad (32s)...")
    time.sleep(32)

    # 7. Close Ad
    print(f"[{email}] Closing ad player...")
    if click_close_button(page):
        print(f"[{email}] Ad closed successfully.")
    else:
        print(f"[{email}] Warning: Close button click failed.")

    page.wait_for_timeout(2000)

    # 8. Claim OK
    print(f"[{email}] Claiming reward...")
    if click_ok_button(page):
        print(f"[{email}] SUCCESS: Reward claimed!")
    else:
        print(f"[{email}] Warning: OK button not found.")

    return "SUCCESS"


# ============================================================
# DYNAMIC 5-ACCOUNT SLIDING BATCH RUNNER
# ============================================================

def run_all_accounts():
    os.makedirs("videos", exist_ok=True)
    remaining_pool = list(ACCOUNTS)
    active_batch = []

    # Initialize batch with first 5 accounts
    while remaining_pool and len(active_batch) < TARGET_BATCH_SIZE:
        active_batch.append(remaining_pool.pop(0))

    cycle_count = 1
    current_idx = 0

    with sync_playwright() as p:
        print(f"Total Accounts Loaded: {len(ACCOUNTS)}")
        print(f"Starting active batch with {len(active_batch)} accounts.")
        print(f"Accounts waiting in reserve pool: {len(remaining_pool)}")

        # Headful mode enabled for full video ad support via Xvfb
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--autoplay-policy=no-user-gesture-required"
            ]
        )

        while active_batch:
            if current_idx >= len(active_batch):
                current_idx = 0
                cycle_count += 1
                print("\n" + "=" * 60)
                print(f"   STARTING CYCLE {cycle_count} ACROSS CURRENT {len(active_batch)} ACTIVE ACCOUNTS")
                print("=" * 60)

            account = active_batch[current_idx]
            print(f"\n[Cycle {cycle_count} | Slot {current_idx + 1}/{len(active_batch)}] Account: {account['email']}")

            context = browser.new_context(
                no_viewport=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                record_video_dir="videos/",
                record_video_size={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            try:
                status = process_single_account(page, account)
            except Exception as e:
                print(f"Error executing {account['email']}: {e}")
                status = "ERROR"

            context.close()

            if status == "LIMIT_REACHED":
                print(f"--> [REMOVING ACCOUNT] {account['email']} reached limit. Dropping from active batch.")
                active_batch.pop(current_idx)

                if remaining_pool:
                    new_acc = remaining_pool.pop(0)
                    print(f"--> [ADDING NEW ACCOUNT] Pulled {new_acc['email']} into slot {current_idx + 1}.")
                    active_batch.insert(current_idx, new_acc)
                else:
                    print(f"--> Pool empty. Active batch size reduced to {len(active_batch)}.")
            else:
                current_idx += 1
                time.sleep(1)

        print("\n" + "=" * 60)
        print("ALL ACCOUNTS HAVE REACHED THEIR DAILY AD LIMIT FOR TODAY!")
        print("=" * 60)
        browser.close()


if __name__ == "__main__":
    run_all_accounts()
