import time
from playwright.sync_api import sync_playwright

# ============================================================
# UPDATED ACCOUNTS LIST (41 ACCOUNTS)
# ============================================================
ALL_EMAILS = [
    "5l8e6h4km7@ooynib.com",
    "2cv9ccpsxr@lnovic.com",
    "cisywyri@denipl.net",
    "er6jf77d70@ooynib.com",
    "facofa@denipl.com",
    "gasemu@denipl.com",
    "golihyti@forexzig.com",
    "hozylyji@denipl.com",
    "jesafago@forexzig.com",
    "jolopam942@hebase.com",
    "kufywexe@denipl.net",
    "kuvyxa@forexzig.com",
    "liluloxe@denipl.net",
    "lizisu@fxzig.com",
    "lojyfoxy@forexzig.com",
    "maweqo@denipl.net",
    "naqiki@forexzig.com",
    "nbpqax7rlr@lnovic.com",
    "nysesu@fxzig.com",
    "pokuky@denipl.com",
    "punamo@denipl.com",
    "qob00mzui7@yzcalo.com",
    "qe1zvivj3q@lnovic.com",
    "qyrijida@denipl.com",
    "raluxyqa@fxzig.com",
    "rexoxyza@fxzig.com",
    "rixakibo@forexzig.com",
    "rorehyzi@forexzig.com",
    "rotehavu@denipl.net",
    "rovofama@fxzig.com",
    "saxoc96700@hilostar.com",
    "sikexyli@denipl.net",
    "tuxaxalu@denipl.com",
    "venafolu@forexzig.com",
    "wasose@forexzig.com",
    "wukocavo@denipl.net",
    "wylesyro@fxzig.com",
    "xagymyho@denipl.net",
    "xehawefe@fxzig.com",
    "xokevufy@fxzig.com",
    "xylexu@forexzig.com",
]

ACCOUNTS = [{"email": email, "password": "Chetan@2026"} for email in ALL_EMAILS]
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
            const overlays = document.querySelectorAll('[class*="backdrop"], [class*="overlay"], div[role="dialog"]');
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


def click_close_button(page):
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
            frame.locator("[role='button']:has-text('Close')"),
            frame.locator("[aria-label*='close' i]"),
            frame.locator(".close-btn, .closeButton, .btn-close"),
            frame.locator("text='×'")
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
    page.wait_for_timeout(2000)
    
    # Try pressing Enter first to dismiss reward modals
    try:
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
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
    page.wait_for_timeout(4000)

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

    print(f"[{email}] Watching video ad (32s)...")
    time.sleep(32)

    print(f"[{email}] Closing ad player...")
    if click_close_button(page):
        print(f"[{email}] Ad closed successfully.")
    else:
        print(f"[{email}] Warning: Close button click failed.")

    page.wait_for_timeout(2000)

    print(f"[{email}] Claiming reward...")
    if click_ok_button(page):
        print(f"[{email}] SUCCESS: Reward claimed!")
    else:
        print(f"[{email}] Warning: OK button not found.")

    return "SUCCESS"


def run_all_accounts():
    remaining_pool = list(ACCOUNTS)
    active_batch = []

    while remaining_pool and len(active_batch) < TARGET_BATCH_SIZE:
        active_batch.append(remaining_pool.pop(0))

    cycle_count = 1
    current_idx = 0

    with sync_playwright() as p:
        print(f"Total Accounts Loaded: {len(ACCOUNTS)}")
        
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
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

            # Set explicit 1080p desktop viewport for cloud headless mode
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
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
        print("ALL 41 ACCOUNTS HAVE REACHED THEIR DAILY AD LIMIT FOR TODAY!")
        print("=" * 60)
        browser.close()


if __name__ == "__main__":
    run_all_accounts()
    
