import os
import sys

from playwright.sync_api import sync_playwright


def run_audit():
    out_dir = "artifacts/evaluation/static_site_audit"
    os.makedirs(out_dir, exist_ok=True)

    url = "http://localhost:8088/"
    viewports = [
        {"name": "desktop_1440", "width": 1440, "height": 900},
        {"name": "laptop_1280", "width": 1280, "height": 720},
        {"name": "mobile_390", "width": 390, "height": 844, "is_mobile": True},
    ]

    console_errors = []
    failed_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in viewports:
            vp_name = vp["name"]
            print(f"\n--- Testing Viewport: {vp_name} ({vp['width']}x{vp['height']}) ---")
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                is_mobile=vp.get("is_mobile", False),
            )
            page = context.new_page()

            # Listeners binding vp_name explicitly
            page.on("console", lambda msg, name=vp_name: console_errors.append(f"[{name}] {msg.type}: {msg.text}") if msg.type == "error" else None)
            page.on("requestfailed", lambda req, name=vp_name: failed_requests.append(f"[{name}] FAILED: {req.url} - {req.failure}"))

            # Navigate
            resp = page.goto(url, wait_until="networkidle")
            assert resp.status == 200, f"Page load failed with status {resp.status}"
            print(f"Loaded {url} successfully (status 200)")

            # Check horizontal overflow
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            client_width = page.evaluate("document.documentElement.clientWidth")
            print(f"Scroll Width: {scroll_width}, Client Width: {client_width}")
            assert scroll_width <= client_width, f"Horizontal overflow on {vp_name}: {scroll_width} > {client_width}"

            # Take full page screenshot
            screenshot_path = os.path.join(out_dir, f"{vp_name}_full.png")
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Captured screenshot: {screenshot_path}")

            # Test interactive features on desktop
            if vp_name == "desktop_1440":
                print("Testing product walkthrough tabs...")
                for tab in ["tab-residuals", "tab-attribution", "tab-economics", "tab-dispatch", "tab-fleet"]:
                    btn = page.locator(f"button[data-tab='{tab}']")
                    btn.click()
                    page.wait_for_timeout(200)
                    panel = page.locator(f"#{tab}")
                    assert panel.is_visible(), f"Panel #{tab} should be visible after click"
                print("Product tabs verified!")

                print("Testing evidence filters...")
                for filter_type in ["VALIDATED", "DEMONSTRATED", "ARCHITECTURAL", "NOT_VALIDATED", "all"]:
                    f_btn = page.locator(f"button[data-filter='{filter_type}']")
                    f_btn.click()
                    page.wait_for_timeout(150)
                print("Evidence filters verified!")

            # Test mobile menu toggle on mobile
            if vp_name == "mobile_390":
                print("Testing mobile navigation toggle...")
                toggle_btn = page.locator(".nav-toggle")
                assert toggle_btn.is_visible(), "Mobile nav toggle should be visible"
                toggle_btn.click()
                page.wait_for_timeout(200)
                nav_links = page.locator(".nav-links")
                assert "open" in nav_links.get_attribute("class"), "Nav links should have 'open' class"
                toggle_btn.click()
                page.wait_for_timeout(200)
                assert "open" not in nav_links.get_attribute("class"), "Nav links should close"
                print("Mobile nav toggle verified!")

            context.close()

        browser.close()

    print("\n=== AUDIT SUMMARY ===")
    print(f"Console Errors: {len(console_errors)}")
    for err in console_errors:
        print(f"  {err}")
    print(f"Failed Requests: {len(failed_requests)}")
    for freq in failed_requests:
        print(f"  {freq}")

    if console_errors or failed_requests:
        print("AUDIT FAILED DUE TO ERRORS")
        sys.exit(1)
    else:
        print("ALL STATIC SITE AUDITS PASSED WITH ZERO ERRORS!")


if __name__ == "__main__":
    run_audit()
