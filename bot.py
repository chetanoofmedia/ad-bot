import os
import time
from playwright.sync_api import sync_playwright

# ============================================================
# LOAD CREDENTIALS SECURELY FROM GITHUB SECRETS
# ============================================================
raw_emails = os.environ.get("ALL_EMAILS", "")
email_password = os.environ.get("ACCOUNT_PASSWORD", "")

ALL_EMAILS = [e.strip() for e in raw_emails.replace(",", " ").split() if e.strip()]

if not ALL_EMAILS:
    raise ValueError("ERROR: No emails found in 'ALL_EMAILS' secret! Please configure GitHub Secrets.")

ACCOUNTS = [{"email": email, "password": email_password} for email in ALL_EMAILS]
TARGET_BATCH_SIZE = 5


def purge_popups(page):
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
            const overlays = document.querySelectorAll('[class*="backdrop"], [class*="overlay"]');
            overlays.forEach(o => o.remove());
        }""")
    except Exception:
        pass


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


def check_login_error(page):
    """Detects invalid emails, bad passwords, or registration errors on the login modal."""
    error_phrases = [
        "Email does not exist!",
        "Incorrect password",
        "Invalid email",
        "User not found"
    ]
    try:
        for phrase in error_phrases:
            elem = page.get_by_text(phrase, exact=False)
            if elem.count() > 0 and elem.first.is_visible():
                return phrase
    except Exception:
        pass
    return None


def click_close_button(page):
    page.wait_for_timeout(2500)
    
    for _ in range(2):
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
        except Exception:
            pass

    try:
        closed = page.evaluate("""() => {
            function findAndClick(doc) {
                const elements = Array.from(doc.querySelectorAll('button, div, span, a, svg, i'));
                for (let el of elements) {
                    const txt = el.textContent ? el.textContent.trim().toLowerCase() : '';
                    const aria = el.getAttribute('aria-label') ? el.getAttribute('aria-label').toLowerCase() : '';
                    const cls = el.className && typeof el.className === 'string' ? el.className.toLowerCase() : '';

                    const isClose = txt === 'close' || txt === '×' || txt === 'x' || txt === 'skip' || 
                                    aria.includes('close') || cls.includes('close') || cls.includes('skip');

                    if (isClose && el.offsetWidth > 0 && el.offsetHeight > 0) {
                        el.click();
                        return true;
                    }
                }
                return false;
            }

            if (findAndClick(document)) return true;

            const iframes = document.querySelectorAll('iframe');
            for (let f of iframes) {
                try {
                    if (f.contentDocument && findAndClick(f.contentDocument)) return true;
                } catch(e) {}
            }
            return false;
        }""")
        if closed:
            page.wait_for_timeout(1000)
            return True
    except Exception:
        pass

    for frame in page.frames:
        locators = [
            frame.get_by_text("Close", exact=True),
            frame.locator("text=/^close$/i"),
            frame.locator("button:has-text('Close')"),
            frame.locator("[role='button']:has-text('Close')"),
            frame.locator("[aria-label*='close' i]"),
            frame.locator(".close-btn, .closeButton, .btn-close, .skip-button, .reward-close"),
            frame.locator("text='×'"),
            frame.locator("text='X'")
        ]
        for loc in locators:
            try:
                count = loc.count()
                for i in range(count):
                    element = loc.nth(i)
                    if element.is_visible():
                        element.click(force=True)
                        page.wait_for_timeout(1000)
                        return True
            except Exception:
                pass

    return False


def click_ok_button(page):
    page.wait_for_timeout(2500)
    
    try:
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
    except Exception:
        pass

    try:
        ok_clicked = page.evaluate("""() => {
            function findOK(doc) {
                const buttons = Array.from(doc.querySelectorAll('button, div[role="button"], a, span'));
                for (let btn of buttons) {
                    const txt = btn.textContent ? btn.textContent.trim().toLowerCase() : '';
                    if ((txt === 'ok' || txt === 'claim' || txt === 'confirm' || txt === 'got it') && btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }

            if (findOK(document)) return true;

            const iframes = document.querySelectorAll('iframe');
            for (let f of iframes) {
                try {
                    if (f.contentDocument && findOK(f.contentDocument)) return true;
                } catch(e) {}
            }
            return false;
        }""")
        if ok_clicked:
            page.wait_for_timeout(1000)
            return True
    except Exception:
        pass

    for frame in page.frames:
        locators = [
            frame.get_by_role("button", name="OK"),
            frame.get_by_text("OK", exact=True),
            frame.locator("text=/^ok$/i"),
            frame.locator("button:has-text('OK')"),
            frame.locator("div[role='dialog'] button")
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


def process_single_account(page, account):
    email = account["email"]
    password = account["password"]

    print(f"--- Logging into: {email} ---")
    page.goto("https://easemate.ai/Dashboard", wait_until="load")
    page.wait_for_timeout(3000)

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
    page.wait_for_timeout(2500)

    # Validate login status
    login_err = check_login_error(page)
    if login_err:
        print(f"[{email}] LOGIN ERROR: '{login_err}'. Skipping account permanently.")
        return "INVALID_ACCOUNT"

    page.wait_for_timeout(1500)

    print(f"[{email}] Navigating to Earn Credits page...")
    page.goto("https://easemate.ai/earn-credits", wait_until="load")
    page.wait_for_timeout(4000)

    purge_popups(page)
    page.wait_for_timeout(1000)
    page.mouse.wheel(0, 500)
    page.wait_for_timeout(1000)

    if check_daily_limit_reached(page):
        print(f"[{email}] LIMIT DETECTED: Account has used all ad opportunities for today!")
        return "LIMIT_REACHED"

    print(f"[{email}] Starting ad task...")
    purge_popups(page)
    if not click_watch_ad(page):
        print(f"[{email}] ERROR: Could not click 'Go Now'. Skipping...")
        return "ERROR"

    page.wait_for_timeout(2000)
    if check_daily_limit_reached(page):
        print(f"[{email}] LIMIT DETECTED: 'You have used all your ad watch opportunities for today.'")
        return "LIMIT_REACHED"

    print(f"[{email}] Watching video ad (35s)...")
    time.sleep(35)

    print(f"[{email}] Closing ad player...")
    ad_closed = click_close_button(page)
    if ad_closed:
        print(f"[{email}] Ad closed successfully.")
    else:
        print(f"[{email}] Warning: Close button click failed.")

    page.wait_for_timeout(2000)

    print(f"[{email}] Claiming reward...")
    ok_clicked = click_ok_button(page)
    if ok_clicked:
        print(f"[{email}] SUCCESS: Reward claimed!")
        return "SUCCESS"
    else:
        print(f"[{email}] Warning: OK button not found.")
        return "NO_OK_BUTTON"


def run_all_accounts():
    remaining_pool = list(ACCOUNTS)
    active_batch = []
    account_stats = {}

    while remaining_pool and len(active_batch) < TARGET_BATCH_SIZE:
        active_batch.append(remaining_pool.pop(0))

    cycle_count = 1
    current_idx = 0

    with sync_playwright() as p:
        print(f"Total Accounts Loaded: {len(ACCOUNTS)}")
        
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
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
            email = account["email"]

            if email not in account_stats:
                account_stats[email] = {"total_runs": 0, "no_ok_count": 0}

            account_stats[email]["total_runs"] += 1

            print(f"\n[Cycle {cycle_count} | Slot {current_idx + 1}/{len(active_batch)}] Account: {email} (Run #{account_stats[email]['total_runs']})")

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                status = process_single_account(page, account)
            except Exception as e:
                print(f"Error executing {email}: {e}")
                status = "ERROR"

            context.close()

            if status == "NO_OK_BUTTON":
                account_stats[email]["no_ok_count"] += 1

            should_remove = False
            if status == "INVALID_ACCOUNT":
                print(f"--> [REMOVING INVALID EMAIL] {email} does not exist. Permanently dropping from batch.")
                should_remove = True
            elif status == "LIMIT_REACHED":
                print(f"--> [REMOVING] {email} hit daily limit text alert.")
                should_remove = True
            elif account_stats[email]["no_ok_count"] >= 2:
                print(f"--> [REMOVING] {email} missed OK button twice in a row (Limit likely reached quietly).")
                should_remove = True
            elif account_stats[email]["total_runs"] >= 11:
                print(f"--> [REMOVING] {email} reached maximum 11 attempt safety cap.")
                should_remove = True

            if should_remove:
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
        print("ALL ACCOUNTS PROCESSED AND EXHAUSTED FOR TODAY!")
        print("=" * 60)
        browser.close()


if __name__ == "__main__":
    run_all_accounts()
