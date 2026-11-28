"""Check deferred screens, focus after reveal and a failed chunk in Chromium."""
from playwright.sync_api import expect


def exercise_screen_loading(browser, url):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    try:
        page = context.new_page()
        requested = []
        page.on("request", lambda request: requested.append(request.url))
        page.goto(url)
        expect(page.get_by_text("Workspace ready.", exact=True)).to_be_visible(timeout=120_000)
        for deferred in ("StaffDashboard-", "EncounterList-", "PatientPortal-"):
            assert not any(deferred in request for request in requested), deferred

        page.get_by_role("button", name="Sign in as Clinician", exact=True).click()
        expect(page.get_by_role("heading", name="Dashboard", exact=True)).to_be_focused()
        assert any("StaffDashboard-" in request for request in requested)
        assert not any("EncounterList-" in request for request in requested)
        assert not any("PatientPortal-" in request for request in requested)

        # A network failure in one screen must leave account controls and the
        # rest of the workspace usable without resetting its database.
        page.route("**/assets/PendingReferralWorklist-*.js", lambda route: route.abort())
        navigation = page.get_by_role("navigation", name="Staff workspace")
        page.locator(".dashboard-queue").filter(has_text="Pending referrals").click()
        expect(page.get_by_role("heading", name="This screen could not be loaded")).to_be_focused()
        expect(page.get_by_role("alert")).to_contain_text("Reloading resets all changes")
        expect(page.get_by_role("button", name="Sign out", exact=True)).to_be_visible()
        navigation.get_by_role("button", name="Patients", exact=True).click()
        expect(page.get_by_role("heading", name="Patient Search", exact=True)).to_be_focused()
        expect(page.get_by_text("400 patients found", exact=False)).to_be_visible()
        navigation.get_by_role("button", name="Dashboard", exact=True).click()
        expect(page.get_by_role("heading", name="Dashboard", exact=True)).to_be_focused()

        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(page.get_by_role("heading", name="Staff sign in")).to_be_focused()
        page.get_by_role("button", name="Switch to patient sign-in").click()
        page.get_by_role("button", name="Sign in as Jordan Lee", exact=True).click()
        expect(page.get_by_role("heading", name="Your patient portal", exact=True)).to_be_focused()
        assert any("PatientPortal-" in request for request in requested)
        print("Deferred screens passed: on-demand downloads, revealed heading focus, failed-screen recovery and patient sign-in.")
    finally:
        context.close()
