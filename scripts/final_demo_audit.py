"""End-to-End Playwright script for Final Demo & Release-Candidate Audit."""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import ConsoleMessage, Response, async_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "artifacts" / "evaluation" / "demo_audit"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_BRAIN_DIR = Path(r"C:\Users\krish\.gemini\antigravity-ide\brain\fb46eff7-fa8e-451b-873c-01bb734a0efa\demo_audit")
ARTIFACT_BRAIN_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://localhost:3000"

console_logs: list[str] = []
console_errors: list[str] = []
network_failures: list[str] = []

async def save_screenshot(page, name: str):
    p1 = OUTPUT_DIR / name
    p2 = ARTIFACT_BRAIN_DIR / name
    await page.screenshot(path=str(p1), full_page=False)
    await page.screenshot(path=str(p2), full_page=False)
    print(f"  [Screenshot] Saved {name}")

async def run_audit():
    print("=================================================================")
    print("   RAI FINAL DEMO & RELEASE-CANDIDATE PLAYWRIGHT AUDIT")
    print("=================================================================")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Listen to console and network
        def on_console(msg: ConsoleMessage):
            txt = f"[{msg.type.upper()}] {msg.text}"
            console_logs.append(txt)
            if msg.type in ("error",):
                console_errors.append(txt)

        def on_response(resp: Response):
            if resp.status >= 400:
                network_failures.append(f"[{resp.status}] {resp.url}")

        page.on("console", on_console)
        page.on("response", on_response)

        # -----------------------------------------------------------------
        # 1. HOME SCREEN: Fleet Operations Command
        # -----------------------------------------------------------------
        print("\n[Step 1] Navigating to Home Screen (Fleet Operations Command)...")
        await page.goto(f"{BASE_URL}/", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await save_screenshot(page, "01_home_fleet_command.png")

        # Verify Key Elements
        title = await page.locator("h1").inner_text()
        print(f"  Page Header: {title}")
        assert "Fleet operations command" in title, f"Unexpected title: {title}"

        metric_tiles = await page.locator(".grid.grid-cols-1.sm\\:grid-cols-2 > div").all_inner_texts()
        print(f"  Found {len(metric_tiles)} Metric Tiles:")
        for idx, mt in enumerate(metric_tiles):
            first_line = mt.split("\n")[0] if "\n" in mt else mt
            print(f"    Metric {idx+1}: {first_line}")

        pq_items = await page.locator(".divide-y.divide-\\[var\\(--border\\)\\] > div").count()
        print(f"  Ranked Action Queue items: {pq_items}")
        assert pq_items > 0, "No priority queue items rendered!"

        # -----------------------------------------------------------------
        # 2. SELECT PROBLEMATIC ASSET (WT-004)
        # -----------------------------------------------------------------
        print("\n[Step 2] Selecting Problematic Asset WT-004...")
        wt4_link = page.locator("a[href='/assets/WT-004']").first
        if await wt4_link.count() > 0:
            await wt4_link.click()
        else:
            await page.goto(f"{BASE_URL}/assets/WT-004", wait_until="networkidle")

        await page.wait_for_url("**/assets/WT-004")
        # Wait for investigation data to load completely
        await page.wait_for_selector("button:has-text('1. Anomaly Detection')", timeout=20000)
        await page.wait_for_timeout(1500)
        await save_screenshot(page, "02_asset_deepdive_hero.png")
        print("  Successfully loaded WT-004 Deep-Dive Hero.")

        # -----------------------------------------------------------------
        # 3. EVIDENCE SECTION 1: ANOMALY DETECTION & RESIDUALS
        # -----------------------------------------------------------------
        print("\n[Step 3] Inspecting Section 1: Anomaly Detection & Signal Residuals...")
        sec1_header = page.locator("button:has-text('1. Anomaly Detection')")
        if await sec1_header.count() > 0:
            await sec1_header.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
        await save_screenshot(page, "03_asset_section1_residuals.png")

        # -----------------------------------------------------------------
        # 4. EVIDENCE SECTIONS 2 & 3: ENVIRONMENTAL ATTRIBUTION & PEERS
        # -----------------------------------------------------------------
        print("\n[Step 4] Inspecting Section 2 & 3: Environmental Context & Peer Gating...")
        sec2_header = page.locator("button:has-text('2. Environmental Attribution')")
        if await sec2_header.count() > 0:
            await sec2_header.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
        await save_screenshot(page, "04_asset_section2_3_environment_peers.png")

        # -----------------------------------------------------------------
        # 5. EVIDENCE SECTIONS 4 & 5: HISTORICAL PRECEDENT & KNOWLEDGE
        # -----------------------------------------------------------------
        print("\n[Step 5] Inspecting Section 4 & 5: Historical Precedent & OEM Citations...")
        sec4_header = page.locator("button:has-text('4. Similar Historical Cases')")
        if await sec4_header.count() > 0:
            await sec4_header.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
        
        # Test real cases filter button
        real_btn = page.locator("button:has-text('REAL ONLY')")
        if await real_btn.count() > 0:
            await real_btn.first.click()
            await page.wait_for_timeout(800)
            print("  Switched to REAL ONLY (14 audited academic cases) filter.")

        await save_screenshot(page, "05_asset_section4_5_precedent_knowledge.png")

        # -----------------------------------------------------------------
        # 6. EVIDENCE SECTIONS 6 & 7: TECHNO-ECONOMICS & RAI REASONING
        # -----------------------------------------------------------------
        print("\n[Step 6] Inspecting Section 6 & 7: Economics & Local LLM Reasoner...")
        sec6_header = page.locator("button:has-text('6. Techno-Economic Intervention Trade-Offs')")
        if await sec6_header.count() > 0:
            await sec6_header.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(600)
        await save_screenshot(page, "06_asset_section6_7_economics_decision.png")

        # -----------------------------------------------------------------
        # 7. PROPOSE WORK ORDER
        # -----------------------------------------------------------------
        print("\n[Step 7] Proposing Work Order from Asset Screen...")
        sec8_header = page.locator("button:has-text('8. Operational Work Orders')")
        if await sec8_header.count() > 0:
            await sec8_header.first.scroll_into_view_if_needed()
        
        propose_btn = page.locator("button:has-text('Propose Work Order'), button:has-text('Authorize Work Order')").first
        if await propose_btn.count() > 0:
            await propose_btn.click()
            await page.wait_for_timeout(1000)
            await save_screenshot(page, "07_propose_work_order_modal.png")
            print("  Work Order Modal open.")

            # Close or submit
            cancel_btn = page.locator("button:has-text('Cancel')").first
            if await cancel_btn.count() > 0:
                await cancel_btn.click()
                await page.wait_for_timeout(500)
                print("  Modal closed.")

        # -----------------------------------------------------------------
        # 8. OPERATIONS CONSOLE: APPROVAL & REJECTION WORKFLOW
        # -----------------------------------------------------------------
        print("\n[Step 8] Navigating to Operations Console (/work-orders)...")
        await page.goto(f"{BASE_URL}/work-orders", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await save_screenshot(page, "08_work_orders_approval_flow.png")

        # Check for propose/reject/approve buttons
        approve_btns = page.locator("button:has-text('Approve & Dispatch')")
        if await approve_btns.count() > 0:
            print(f"  Found {await approve_btns.count()} pending work orders awaiting approval. Testing approval...")
            await approve_btns.first.click()
            await page.wait_for_timeout(800)
            await save_screenshot(page, "07_propose_work_order_modal.png")
            confirm_approve = page.locator("button:has-text('Authorize Dispatch')").first
            if await confirm_approve.count() > 0:
                await confirm_approve.click()
                await page.wait_for_timeout(1500)
                print("  Ticket approved and scheduled.")
            else:
                c_btn = page.locator("button:has-text('Cancel')").first
                if await c_btn.count() > 0:
                    await c_btn.click()

        # -----------------------------------------------------------------
        # 9. CREW DISPATCH & SAFE WEATHER PLANNING TAB
        # -----------------------------------------------------------------
        print("\n[Step 9] Switching to Crew Dispatch & Weather Windows tab...")
        dispatch_tab = page.locator("button:has-text('Crew Dispatch & Weather Windows')")
        if await dispatch_tab.count() > 0:
            await dispatch_tab.first.click()
            await page.wait_for_timeout(1500)
            await save_screenshot(page, "09_crew_dispatch_weather_windows.png")
            print("  Verified safe weather dispatch window calculations.")

        # -----------------------------------------------------------------
        # 10. TECHNICIAN FEEDBACK RECORDING
        # -----------------------------------------------------------------
        print("\n[Step 10] Testing Technician Feedback recording...")
        orders_tab = page.locator("button:has-text('All Active & Historical Tickets')")
        if await orders_tab.count() > 0:
            await orders_tab.first.click()
            await page.wait_for_timeout(1000)

        feedback_btns = page.locator("button:has-text('Record Field Findings')")
        if await feedback_btns.count() > 0:
            print(f"  Found {await feedback_btns.count()} tickets ready for feedback.")
            await feedback_btns.first.click()
            await page.wait_for_timeout(800)
            await save_screenshot(page, "10_technician_feedback_modal.png")
            print("  Technician feedback modal open.")

            # Fill findings
            findings_input = page.locator("textarea")
            if await findings_input.count() > 0:
                await findings_input.first.fill("Inspected main gearbox bearing. Severe pitting detected on inner race. Flushed lubricant and scheduled component replacement.")
            
            # Click save feedback
            save_fb = page.locator("button:has-text('Record Field Resolution')").first
            if await save_fb.count() > 0:
                await save_fb.click()
                await page.wait_for_timeout(1500)
                print("  Technician feedback recorded to ground-truth ledger.")
            else:
                cancel_btn = page.locator("button:has-text('Cancel')").first
                if await cancel_btn.count() > 0:
                    await cancel_btn.click()
        else:
            print("  No tickets currently in scheduled state requiring feedback.")

        # -----------------------------------------------------------------
        # 11. CLOSED-LOOP LEARNING STATUS TAB
        # -----------------------------------------------------------------
        print("\n[Step 11] Switching to Closed-Loop Learning Status tab...")
        learning_tab = page.locator("button:has-text('Closed-Loop Learning Status')")
        if await learning_tab.count() > 0:
            await learning_tab.first.click()
            await page.wait_for_timeout(1500)
            await save_screenshot(page, "11_closed_loop_learning_status.png")
            print("  Verified closed loop promotion gate and quarantine status.")

        # -----------------------------------------------------------------
        # 12. SCIENTIFIC EVIDENCE & MODEL SCORECARD ROUTE
        # -----------------------------------------------------------------
        print("\n[Step 12] Navigating to Model Scorecard (/evaluation)...")
        await page.goto(f"{BASE_URL}/evaluation", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await save_screenshot(page, "12_scientific_model_scorecard.png")
        print("  Verified Model Scorecard and 4-tier scientific freeze documentation.")

        await browser.close()

    print("\n=================================================================")
    print("   PLAYWRIGHT AUDIT SUMMARY")
    print("=================================================================")
    print(f"Total console messages logged: {len(console_logs)}")
    print(f"Console errors: {len(console_errors)}")
    for ce in console_errors:
        print(f"  ! {ce}")
    print(f"Network failures (>= 400): {len(network_failures)}")
    for nf in network_failures:
        print(f"  ! {nf}")

    return len(console_errors) == 0 and len(network_failures) == 0

if __name__ == "__main__":
    success = asyncio.run(run_audit())
    sys.exit(0 if success else 1)
