"""Shared worklist regressions for the existing packaged-browser workflow."""
import os
from pathlib import Path
import re

from playwright.sync_api import expect


def exercise_worklist_usability(page):
    """Use the signed-in disposable workspace; preserve its clinical records."""
    worklists = (
        ("Open Follow-ups", "Open follow-ups", "Find a follow-up", "Open follow-up tasks", "Task"),
        ("Active Care Goals", "Active care goals", "Find a care goal", "Active care goals", "Goal"),
        ("Pending Referrals", "Pending referrals", "Find a referral", "Pending referrals", "Referral"),
    )
    original_viewport = page.viewport_size
    for destination, label, search_label, list_label, record_label in worklists:
        nav = page.get_by_role("navigation", name="Staff workspace")
        nav.get_by_role("button", name=destination, exact=True).click()
        expect(page.get_by_role("heading", name=destination, exact=True)).to_be_visible()
        rows = page.get_by_role("list", name=list_label, exact=True).get_by_role("listitem")
        expect(rows).to_have_count(6)
        print(f"{destination}: {page.locator('.worklist-pagebar [role=status]').inner_text()}")
        first_page = rows.all_text_contents()
        pages = page.get_by_role("navigation", name=label + " pages", exact=True)
        expect(pages.get_by_role("button", name="Previous", exact=True)).to_be_disabled()
        next_page = pages.get_by_role("button", name="Next", exact=True)
        next_page.focus()
        page.keyboard.press("Enter")
        summary = page.locator(".worklist-pagebar [role=status]")
        expect(summary).to_be_focused()
        expect(summary).to_contain_text("Showing 7–")
        assert rows.first.inner_text() != first_page[0]

        # Pick an actual off-page record, then find it from page one. This
        # verifies filtering spans the entire queue and still opens its chart.
        patient = rows.first.locator(".schedule-patient-link").inner_text()
        match = re.search(record_label + r" #(\d+)", rows.first.inner_text())
        assert match, "Worklist record identifier is missing"
        identifier = match.group(1)
        pages.get_by_role("button", name="Previous", exact=True).click()
        search = page.get_by_role("searchbox", name=search_label, exact=True)
        query = f"{patient} {identifier}"
        search.fill(query)
        expect(rows).to_have_count(1)
        expect(rows.first).to_contain_text(record_label + " #" + identifier)
        expect(summary).to_contain_text("1 matching")
        expect(search).to_be_focused()

        page.get_by_role("button", name="Refresh", exact=True).click()
        expect(search).to_have_value(query)
        expect(rows).to_have_count(1)
        expect(rows.first).to_contain_text(record_label + " #" + identifier)
        search.fill("no-such-worklist-record-qa")
        expect(rows).to_have_count(0)
        expect(summary).to_contain_text("0 matching")
        clear = page.get_by_role("button", name="Clear search", exact=True)
        clear.focus()
        page.keyboard.press("Enter")
        expect(search).to_be_focused()
        expect(search).to_have_value("")
        expect(rows).to_have_count(6)
        assert rows.all_text_contents() == first_page

        page.set_viewport_size({"width": 320, "height": 800})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        for control in (search, clear, pages.get_by_role("button", name="Next", exact=True)):
            assert control.bounding_box()["height"] >= 44, "Worklist control below 44 CSS px"
        screenshots = os.environ.get("EMR_SCREENSHOT_DIR")
        if screenshots and destination == "Open Follow-ups":
            output = Path(screenshots)
            output.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(output / "15-follow-ups-mobile.png"), full_page=True,
                            animations="disabled", caret="hide")
        assert original_viewport is not None
        page.set_viewport_size(original_viewport)
        search.fill(query)
        chart = rows.first.get_by_role("button", name="Open chart for " + patient, exact=True)
        chart.focus()
        page.keyboard.press("Enter")
        # Charts retain legal and middle names as well as a preferred name;
        # the shorter worklist name must still identify that chart heading.
        expect(page.locator(".chart-identity h1")).to_contain_text(
            re.compile(".*".join(re.escape(part) for part in patient.split())))
    page.get_by_role("navigation", name="Staff workspace").get_by_role("button", name="Dashboard", exact=True).click()
    print("Three worklists passed full-queue search, six-row paging, keyboard focus, refresh, chart access and 320px reflow.")
