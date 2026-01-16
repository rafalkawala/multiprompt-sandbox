"""
E2E test for Wizard Flow using Playwright.
Run manually with: python tests/e2e/test_wizard_flow.py
Requires: pip install playwright && playwright install chromium
"""
import asyncio
import sys

import pytest

# Skip this entire module when running via pytest (Playwright not installed in CI)
pytest.skip("E2E tests require Playwright - run manually", allow_module_level=True)

from playwright.async_api import async_playwright

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

        base_url = "http://localhost:4200" # Assumes local dev server

        print(f"Navigating to {base_url}...")
        try:
            await page.goto(base_url)
        except Exception as e:
            print(f"Error connecting to {base_url}: {e}")
            print("Ensure the frontend is running (ng serve).")
            return

        # Inject token to simulate logged-in state
        await page.evaluate("localStorage.setItem('dev_access_token', 'mock-token')")
        await page.evaluate("localStorage.removeItem('wizard_do_not_show')") # Force show

        print("Reloading to trigger auto-start...")
        await page.reload()

        # 1. Verify Dialog Appears
        print("Verifying Wizard Dialog auto-start...")
        try:
            await page.wait_for_selector("app-wizard-dialog", timeout=5000)
            print("PASS: Wizard Dialog appeared automatically.")
        except Exception:
            print("FAIL: Wizard Dialog did not appear.")
            await browser.close()
            return

        # 2. Verify Selection Screen Content
        # Check titles of cards using data-testid (PR Review: Added data-testid selectors for robustness)
        if await page.query_selector("mat-card[data-testid='card-feasibility']") and \
           await page.query_selector("mat-card[data-testid='card-large-dataset']") and \
           await page.query_selector("mat-card[data-testid='card-prompt-dev']"):
            print("PASS: Wizard Selection cards present (verified via data-testid).")
        else:
            print("FAIL: Wizard Selection cards missing or incorrect.")

        # 2b. Verify "Do not show again" logic (PR Review: Recommendation item)
        print("Testing 'Do not show again' preference...")
        try:
             checkbox = await page.wait_for_selector("mat-checkbox[data-testid='checkbox-do-not-show']")
             await checkbox.click()
             
             # Verify it set localStorage
             val = await page.evaluate("localStorage.getItem('wizard_do_not_show')")
             if val == 'true':
                 print("PASS: 'Do not show again' checkbox correctly updated localStorage.")
             else:
                 print(f"FAIL: 'Do not show again' checkbox did not update localStorage. Got: {val}")
        except Exception as e:
            print(f"FAIL: Error testing checkbox: {e}")

        # 3. Test Navigation (Click 'Start Validation')
        print("Testing flow navigation...")
        try:
            # Look for the button specifically in the card
            await page.click("mat-card[data-testid='card-feasibility'] button")

            # Verify we moved to Step 1 (Project Setup)
            await page.wait_for_selector("app-wizard-project-step", timeout=2000)
            print("PASS: Navigated to Project Step.")
        except Exception as e:
             print(f"FAIL: Navigation error: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_wizard_test())
