import os
import time
from playwright.sync_api import sync_playwright

# ============================================================
# LOAD ALL CREDENTIALS FROM GITHUB SECRETS
# ============================================================
raw_emails = os.environ.get("ALL_EMAILS", "")
email_password = os.environ.get("ACCOUNT_PASSWORD", "")

ALL_EMAILS = [e.strip() for e in raw_emails.replace(",", " ").split() if e.strip()]

if not ALL_EMAILS:
    raise ValueError("ERROR: No emails found in 'ALL_EMAILS' secret! Please configure GitHub Secrets.")

ACCOUNTS = [{"email": email, "password": email_password} for email in ALL_EMAILS]

BATCH_SIZE = 5
CYCLES_PER_BATCH = 10


# ============================================================
# AUTOMATION HELPER FUNCTIONS
# ============================================================

def check_login_failed(page):
    try:
        error_texts = [
            "Email does not exist!",
            "Email does not exist",
            "Invalid email or password",
            "User not found",
            "Password is incorrect",
            "Please enter a valid email address"
        ]
        for frame in page.frames:
            for txt in error_texts:
                element = frame.get_by_text(txt, exact=False)
                if element.count() > 0 and element.first.is_visible():
                    return True
    except Exception:
        pass
    return False


def check_daily_limit_reached(page):
    try:
        limit_text = "You have used all your ad watch opportunities for today"
        for frame in page.frames:
            element = frame.get_by_text(limit_text, exact=False)
            if element.count() > 0 and element.first.is_visible():
                return True
    except Exception:
        pass
    return False


def purge_popups(page):
    """Removes floating ad widgets (Celebrity Twin Finder, GPT Image 2.5) and modal backdrops."""
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
                "WHAT'S NEW",
                'SEEDANCE',
                'WAN 3.0'
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


def click_close_button(page):
    """Finds all visible 'Close' elements after watching an ad and clicks them."""
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    except Exception:
        pass

    try:
        clicked = page.evaluate("""() => {
            const allElements = Array.from(document.querySelectorAll('*'));
            const closeEl = allElements.find(el => 
                el.children.length === 0 && 
                el.textContent.trim().toLowerCase() === 'close' &&
                el.offsetWidth > 0 && el.offsetHeight > 0
            );
            if (closeEl) {
                closeEl.click();
                return true;
            }
            return false;
        }""")
        if clicked:
            return True
    except Exception:
        pass

    for frame in page.frames:
        locators = [
            frame.get_by_text("Close", exact=True),
            frame.locator("text=/^close$/i"),
            frame.locator("button:has-text('Close')"),
            frame.locator("[role='button']:has-text('Close')"),
            frame.locator("span:has-text('Close')")
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
                        else:
                            element.click(force=True)
                        page.wait_for_timeout(1000)
                        return True
            except Exception:
                pass

    return False


def click_ok_button(page):
    """Clicks the credit reward OK button across main page and frames."""
    page.wait_for_timeout(1500)

    try:
        clicked = page.evaluate("""() => {
            const allElements = Array.from(document.querySelectorAll('*'));
            const okBtn = allElements.find(el => 
                (el.tagName === 'BUTTON' || el.tagName === 'DIV' || el.tagName === 'SPAN') &&
                el.textContent.trim().toLowerCase() === 'ok' &&
                el.offsetWidth > 0 && el.offsetHeight > 0
            );
            if (okBtn) {
                okBtn.click();
                return true;
            }
            return false;
        }""")
        if clicked:
            return True
    except Exception:
        pass

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

    if check_login_failed(page):
        print(f"[{email}] LOGIN FAILED: Invalid account credentials!")
        return "INVALID_ACCOUNT"

    # 2. Earn Credits Navigation
    print(f"[{email}] Navigating to Earn Credits page...")
    page.goto("https://easemate.ai/earn-credits", wait_until="load")
    page.wait_for_timeout(4000)

    # 3. Purge floating widgets & Scroll
    purge_popups(page)
    page.wait_for_timeout(1000)

    if check_daily_limit_reached(page):
        print(f"[{email}] LIMIT DETECTED: Daily limit reached!")
        return "LIMIT_REACHED"

    page.mouse.wheel(0, 500)
    page.wait_for_timeout(1000)

    # 4. Click Go Now
    print(f"[{email}] Starting ad task...")
    purge_popups(page)
    if not click_watch_ad(page):
        print(f"[{email}] ERROR: Could not click 'Go Now'. Skipping...")
        return "ERROR"

    page.wait_for_timeout(2000)
    if check_daily_limit_reached(page):
        print(f"[{email}] LIMIT DETECTED: Daily limit reached!")
        return "LIMIT_REACHED"

    # 5. Wait for Video Playback
    print(f"[{email}] Watching video ad (38s)...")
    time.sleep(38)

    # 6. Close Ad
    print(f"[{email}] Closing ad player...")
    if click_close_button(page):
        print(f"[{email}] Ad closed successfully.")
    else:
        print(f"[{email}] Warning: Close button click failed.")

    page.wait_for_timeout(2000)

    # 7. Claim OK
    print(f"[{email}] Claiming reward...")
    if click_ok_button(page):
        print(f"[{email}] SUCCESS: Reward claimed for {email}!")
    else:
        print(f"[{email}] Warning: OK button not found.")

    return "SUCCESS"


# ============================================================
# BATCH & MULTI-CYCLE RUNNER
# ============================================================

def run_all_accounts():
    os.makedirs("videos", exist_ok=True)
    batches = [ACCOUNTS[i:i + BATCH_SIZE] for i in range(0, len(ACCOUNTS), BATCH_SIZE)]
    total_batches = len(batches)

    with sync_playwright() as p:
        print(f"Total accounts loaded: {len(ACCOUNTS)}")
        print(f"Structure: {total_batches} batches x {BATCH_SIZE} accounts x {CYCLES_PER_BATCH} cycles per batch.")
        
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        for batch_index, current_batch in enumerate(batches, start=1):
            print("\n" + "=" * 60)
            print(f"   STARTING BATCH {batch_index} OF {total_batches}")
            print(f"   Accounts in this batch: {[acc['email'] for acc in current_batch]}")
            print("=" * 60)

            for cycle in range(1, CYCLES_PER_BATCH + 1):
                print(f"\n>>> [Batch {batch_index}/{total_batches}] CYCLE {cycle} OF {CYCLES_PER_BATCH} <<<")

                for acc_index, account in enumerate(current_batch, start=1):
                    print(f"\n[Batch {batch_index}/{total_batches} | Cycle {cycle}/{CYCLES_PER_BATCH}] Account {acc_index}/{len(current_batch)} ({account['email']})")

                    context = browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                        record_video_dir="videos/",
                        record_video_size={"width": 1920, "height": 1080}
                    )
                    page = context.new_page()

                    try:
                        status = process_single_account(page, account)
                    except Exception as e:
                        print(f"Error processing {account['email']}: {e}")

                    context.close()
                    time.sleep(2)

        print("\n" + "=" * 60)
        print("ALL BATCHES AND CYCLES COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        browser.close()


if __name__ == "__main__":
    run_all_accounts()
