import asyncio
from playwright.async_api import async_playwright
import os

async def run_wizard_test():
    """
    Verifies the Wizard Flow UI.
    Requires the frontend to be running at http://localhost:4200.
    Mocks backend responses to test UI in isolation.
    """
    async with async_playwright() as p:
        # Use headless=True for CI/Background
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # --- Mocks ---
        # Mock Auth User (Admin)
        await page.route("**/auth/me", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"id":"test-user","email":"test@example.com","name":"Test User","role":"admin","is_active":true}'
        ))

        # Mock Projects (Empty)
        await page.route("**/api/projects", lambda route: route.fulfill(
             status=200, content_type="application/json", body='[]'
        ))

        # Mock Evals
        await page.route("**/api/evaluations", lambda route: route.fulfill(
            status=200, content_type="application/json", body='[]'
        ))

        # Mock Health
        await page.route("**/api/health", lambda route: route.fulfill(status=200, body='{"status":"ok"}'))

        base_url = "http://localhost:4200"

        print(f"Navigating to {base_url}...")
        try:
            await page.goto(base_url)
        except Exception as e:
            print(f"Error connecting to {base_url}: {e}")
            print("Ensure the frontend is running (ng serve).")
            return

        # Inject token
        await page.evaluate("localStorage.setItem('dev_access_token', 'mock-token')")
        await page.evaluate("localStorage.removeItem('wizard_do_not_show')")

        print("Reloading to trigger auto-start...")
        await page.reload()

        # 1. Verify Dialog Appears
        print("Verifying Wizard Dialog auto-start...")
        try:
            await page.wait_for_selector("app-wizard-dialog", timeout=5000)
            print("PASS: Dialog appeared.")
        except Exception:
            print("FAIL: Dialog did not appear.")
            await browser.close()
            return

        # 2. Test Feasibility Flow
        print("Testing 'Feasibility' flow entry...")
        await page.click("button:has-text('Start Validation')")
        await page.wait_for_selector("app-wizard-project-step")
        print("PASS: Entered Feasibility Flow.")

        # Reset (Close dialog and reopen or reload)
        # Reload is easiest to reset state completely
        await page.reload()
        await page.wait_for_selector("app-wizard-dialog")

        # 3. Test Large Dataset Flow
        print("Testing 'Large Dataset' flow entry...")
        await page.click("button:has-text('Start Analysis')")
        await page.wait_for_selector("app-wizard-project-step")
        # Verify title
        header_text = await page.text_content("app-wizard-shell header h2")
        if "Analyze Large Dataset" in header_text:
             print("PASS: Header confirms Large Dataset flow.")
        else:
             print(f"FAIL: Header mismatch: {header_text}")

        # Reset
        await page.reload()
        await page.wait_for_selector("app-wizard-dialog")

        # 4. Test Prompt Dev Flow
        print("Testing 'Prompt Dev' flow entry...")
        await page.click("button:has-text('Start Developing')")
        await page.wait_for_selector("app-wizard-project-step")
        header_text = await page.text_content("app-wizard-shell header h2")
        if "Develop & Optimize Prompt" in header_text:
             print("PASS: Header confirms Prompt Dev flow.")
        else:
             print(f"FAIL: Header mismatch: {header_text}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_wizard_test())
