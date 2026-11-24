"""Browser smoke checks for the public synthetic demo, not the clinical API."""
from pathlib import Path
import re
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = (ROOT / "demo" / "index.html").as_uri()

with sync_playwright() as p:
    browser = p.chromium.launch()
    # Use a real HTTP origin supplied by CI; file URLs are a local fallback.
    import os
    url = os.environ.get("EMR_DEMO_URL", URL)
    for width in (360, 1280):
        page = browser.new_page(viewport={"width": width, "height": 900},
                                reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        expect(page.get_by_role("heading", name="Good morning, Dr. Rivera")).to_be_visible()
        notice = page.get_by_role("note", name="Legal notice")
        expect(notice).to_have_count(1)
        expect(notice).to_be_visible()
        expect(notice).to_contain_text("All provided patient records are fictional.")
        expect(notice).to_contain_text("Do not enter real patient information.")
        for mode in ("staff", "patient"):
            page.locator(f'[data-mode-target="{mode}"]').click()
            for button in page.locator(f'[data-mode-nav="{mode}"] button').all():
                button.click()
                expect(notice).to_be_visible()
                assert page.evaluate("document.querySelector('.legal-notice').getBoundingClientRect().top >= 0 && document.querySelector('.legal-notice').getBoundingClientRect().top < 1")
                body = page.locator("body").inner_text().replace(notice.inner_text(), "", 1)
                assert not re.search(r"\b(synthetic|mock|fake|fictional|demo|portfolio|simulat\w*)\b", body, re.I), body
        page.locator('[data-mode-target="staff"]').click()
        page.get_by_role("button", name="Open today’s schedule").click()
        page.get_by_role("searchbox").fill("Jordan")
        expect(page.locator("#schedule-body tr:visible")).to_have_count(1)
        page.get_by_role("button", name="Open chart").click()
        summary = page.get_by_role("tab", name="Summary")
        summary.focus()
        summary.press("ArrowRight")
        expect(page.get_by_role("tab", name="Medications")).to_be_focused()
        expect(page.get_by_role("tab", name="Medications")).to_have_attribute("aria-selected", "true")
        expect(page.get_by_role("tabpanel", name="Medications")).to_be_visible()
        page.get_by_role("button", name="Audit & lifecycle").click()
        page.get_by_role("button", name="Reactivate chart").click()
        expect(page.locator("#lifecycle-chip")).to_have_text("Active")
        page.get_by_role("button", name="Patient portal", exact=True).click()
        page.get_by_role("button", name="Appointments", exact=True).click()
        request = page.get_by_role("button", name="Request a change", exact=True)
        request.click()
        expect(request).to_have_attribute("aria-expanded", "true")
        page.get_by_role("button", name="Request reschedule").click()
        expect(request).to_have_attribute("aria-expanded", "false")
        expect(request).to_be_focused()
        expect(page.locator("#request-status")).to_contain_text("Nothing was sent")
        page.get_by_role("button", name="Preferences", exact=True).click()
        page.get_by_role("radio", name="Email").check()
        page.get_by_role("button", name="Save preferences").click()
        expect(page.locator("#preferences-status")).to_contain_text("No message will be sent")
        page.reload()
        page.get_by_role("button", name="Patient portal", exact=True).click()
        page.get_by_role("button", name="Preferences", exact=True).click()
        expect(page.get_by_role("radio", name="Email")).to_be_checked()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Horizontal overflow at {width}px"
        assert not errors, errors
        page.close()
    browser.close()
print("Public demo browser smoke passed at 360px and 1280px.")
