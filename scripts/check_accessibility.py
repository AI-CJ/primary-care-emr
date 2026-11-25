"""Inspect Chromium's accessibility tree and exercise real keyboard navigation.

The checks complement, but do not replace, a human screen-reader evaluation.
Only the disposable local browser application is accepted.
"""
import re
from collections import Counter

from playwright.sync_api import expect, sync_playwright

from scripts.check_browser_emr import URL, TIMEOUT


def ax_nodes(page):
    session = page.context.new_cdp_session(page)
    try:
        nodes = session.send("Accessibility.getFullAXTree")["nodes"]
        # The transport does not guarantee depth-first reading order. Follow
        # ordered child IDs, traversing ignored containers as well.
        by_id = {node["nodeId"]: node for node in nodes}
        ordered = []
        visited = set()

        def visit(node):
            node_id = node["nodeId"]
            if node_id in visited:
                return
            visited.add(node_id)
            if not node.get("ignored"):
                ordered.append(node)
            for child_id in node.get("childIds", []):
                if child_id in by_id:
                    visit(by_id[child_id])

        for node in nodes:
            if node.get("parentId") not in by_id:
                visit(node)
        return ordered
    finally:
        session.detach()


def ax_value(node, field):
    return node.get(field, {}).get("value", "")


def assert_exposed(page, role, name=None):
    nodes = ax_nodes(page)
    matches = [
        node for node in nodes if ax_value(node, "role") == role
        and (name is None or ax_value(node, "name") == name)
    ]
    assert matches, f"Accessibility tree missing {role}: {name}"
    return matches


def inspect_screen(page, label):
    nodes = ax_nodes(page)
    roles = Counter(ax_value(node, "role") for node in nodes)
    assert roles["main"] == 1, f"{label}: expected one main landmark"
    headings = [node for node in nodes if ax_value(node, "role") == "heading"]
    assert headings, f"{label}: no exposed headings"
    first = headings[0]
    properties = {prop["name"]: prop.get("value", {}).get("value")
                  for prop in first.get("properties", [])}
    assert properties.get("level") == 1, (
        f"{label}: first heading must be level one; got "
        f"{ax_value(first, 'name')} (level {properties.get('level')})"
    )
    interactive = {"button", "link", "textbox", "searchbox", "checkbox",
                   "radio", "combobox", "spinbutton", "switch", "DisclosureTriangle"}
    unlabeled = [ax_value(node, "role") for node in nodes
                 if ax_value(node, "role") in interactive
                 and not str(ax_value(node, "name")).strip()]
    assert not unlabeled, f"{label}: unnamed interactive roles {unlabeled}"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
        f"{label}: horizontal overflow"
    )
    print(f"{label}: {roles['main']} main landmark, {len(headings)} headings, "
          f"{sum(roles[r] for r in interactive)} named interactive elements")


def keyboard_click(page, locator):
    locator.focus()
    expect(locator).to_be_focused()
    page.keyboard.press("Enter")


def contrast_ratio(foreground, background):
    def luminance(rgb):
        channels = [value / 255 for value in rgb]
        values = [value / 12.92 if value <= .04045
                  else ((value + .055) / 1.055) ** 2.4 for value in channels]
        return sum(value * weight for value, weight in zip(values, (.2126, .7152, .0722)))

    levels = sorted((luminance(foreground), luminance(background)))
    return (levels[1] + .05) / (levels[0] + .05)


def assert_field_boundary(locator):
    """Check the solid border against the field fill, not the surrounding page."""
    border, fill = locator.evaluate("""el => {
      const style = getComputedStyle(el);
      return [style.borderTopColor, style.backgroundColor];
    }""")
    def rgb(value):
        return [float(channel) for channel in re.findall(r"[\d.]+", value)][:3]

    ratio = contrast_ratio(rgb(border), rgb(fill))
    assert ratio >= 3, f"Control border contrast {ratio:.2f}:1 below 3:1"
    print(f"Computed field boundary contrast: {ratio:.2f}:1")


def assert_visible_keyboard_focus(locator):
    locator.focus()
    expect(locator).to_be_focused()
    result = locator.evaluate("""el => {
      const style = getComputedStyle(el);
      return [el.matches(':focus-visible'), style.outlineStyle, parseFloat(style.outlineWidth)];
    }""")
    assert result[0] and result[1] == "solid" and result[2] >= 2, (
        f"Expected visible keyboard outline, got {result}"
    )


def assert_solid_contrast(locator, minimum=4.5):
    # Sample computed solid surfaces, not gradients or composited backgrounds.
    result = locator.evaluate("""el => {
      const color = getComputedStyle(el).color;
      let surface = el;
      while (surface) {
        const style = getComputedStyle(surface);
        if (style.backgroundImage !== 'none') return null;
        const values = style.backgroundColor.match(/[\\d.]+/g)?.map(Number);
        if (values && values.length === 3) return [color, values];
        if (values && values.length === 4 && values[3] === 1)
          return [color, values.slice(0, 3)];
        if (values && values.length === 4 && values[3] !== 0) return null;
        surface = surface.parentElement;
      }
      return null;
    }""")
    assert result is not None, "Expected an opaque solid background"
    foreground = [float(value) for value in re.findall(r"[\d.]+", result[0])][:3]
    background = result[1]

    ratio = contrast_ratio(foreground, background)
    assert ratio >= minimum, f"Computed contrast {ratio:.2f}:1 below {minimum}:1"
    print(f"Computed solid contrast: {ratio:.2f}:1")


def run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900},
                                reduced_motion="reduce")
        page.set_default_timeout(30_000)
        page.route("**/*", lambda route: route.continue_()
                   if route.request.url.startswith("http://127.0.0.1:4174/")
                   else route.abort())
        page.goto(URL)
        expect(page.get_by_text("Workspace ready.", exact=True)).to_be_visible(timeout=TIMEOUT)
        expect(page.locator("html")).to_have_attribute("lang", "en")
        # The bypass is the first tab stop and moves focus past shared controls.
        page.keyboard.press("Tab")
        skip = page.get_by_role("link", name="Skip to main content", exact=True)
        expect(skip).to_be_focused()
        page.keyboard.press("Enter")
        expect(page.get_by_role("heading", name="Staff sign in", exact=True)).to_be_focused()
        inspect_screen(page, "Staff sign-in")
        assert_exposed(page, "group", "Available accounts")
        admin = assert_exposed(page, "button", "Sign in as Administrator")[0]
        assert "chart administration" in ax_value(admin, "description")
        assert_exposed(page, "textbox", "Username")
        assert_exposed(page, "status")
        assert_solid_contrast(page.get_by_role("button", name="Sign in", exact=True))
        username = page.get_by_role("textbox", name="Username")
        assert_field_boundary(username)
        assert_visible_keyboard_focus(username)
        # Verify the sign-in page reflows without hiding the legal notice.
        for width in (360, 320):
            page.set_viewport_size({"width": width, "height": 800})
            inspect_screen(page, f"Staff sign-in at {width}px")
            assert page.get_by_role("button", name="Sign in as Administrator").bounding_box()["height"] >= 44
        page.set_viewport_size({"width": 1280, "height": 900})
        keyboard_click(page, page.get_by_role("button", name="Sign in as Administrator"))
        expect(page.get_by_role("heading", name="Dashboard", exact=True)).to_be_focused(timeout=TIMEOUT)
        inspect_screen(page, "Staff dashboard")
        assert_exposed(page, "navigation", "Staff workspace")
        assert_solid_contrast(page.get_by_role("navigation", name="Staff workspace")
                              .get_by_role("button", name="Dashboard", exact=True))
        keyboard_click(page, page.get_by_role("button", name=re.compile("Find a patient")))
        expect(page.get_by_role("heading", name="Patient Search", exact=True)).to_be_focused()
        search = page.get_by_role("searchbox", name="Search patients")
        assert_field_boundary(search)
        assert_visible_keyboard_focus(search)
        search.fill("Jordan")
        keyboard_click(page, page.get_by_role("button", name="Search", exact=True))
        keyboard_click(page, page.get_by_role("button", name=re.compile("Lee, Jordan")))
        expect(page.get_by_role("heading", name="Jordan Lee", exact=True)).to_be_focused()
        inspect_screen(page, "Staff chart")
        assert_exposed(page, "region", "Chart allergy status")
        assert_exposed(page, "navigation", "Patient chart sections")
        keyboard_click(page, page.get_by_role("button", name="Sign out", exact=True))
        expect(page.get_by_role("heading", name="Staff sign in", exact=True)).to_be_focused()
        keyboard_click(page, page.get_by_role("button", name="Switch to patient sign-in"))
        expect(page.get_by_role("heading", name="Patient sign in", exact=True)).to_be_focused()
        inspect_screen(page, "Patient sign-in")
        assert_exposed(page, "button", "Sign in as Jordan Lee")
        keyboard_click(page, page.get_by_role("button", name="Sign in as Jordan Lee"))
        expect(page.get_by_role("heading", name="Your patient portal", exact=True)).to_be_focused(timeout=TIMEOUT)
        inspect_screen(page, "Patient home")
        assert_exposed(page, "navigation", "Patient portal sections")
        assert_solid_contrast(page.get_by_role("navigation", name="Patient portal sections")
                              .get_by_role("button", name="Home", exact=True))
        nav = page.get_by_role("navigation", name="Patient portal sections")
        keyboard_click(page, nav.get_by_role("button", name="Settings", exact=True))
        expect(page.locator(".portal-section-heading h2")).to_be_focused()
        channel = page.get_by_role("combobox", name="Preferred contact method")
        expect(channel).to_have_value("portal")
        assert_field_boundary(channel)
        assert_visible_keyboard_focus(channel)
        inspect_screen(page, "Patient settings")
        assert_exposed(page, "form", "Communication preferences")
        assert_exposed(page, "group", "Types of updates")
        assert_exposed(page, "checkbox", "Appointment reminders")
        channel.select_option("email")
        expect(page.get_by_text("You have unsaved changes.", exact=True)).to_be_visible()
        assert_exposed(page, "status")
        keyboard_click(page, nav.get_by_role("button", name="My health", exact=True))
        assert not any(ax_value(node, "name") == "Preferred contact method"
                       for node in ax_nodes(page)), "Hidden form exposed to assistive technology"
        keyboard_click(page, nav.get_by_role("button", name="Settings", exact=True))
        expect(channel).to_have_value("email")
        keyboard_click(page, page.get_by_role("button", name="Save preferences", exact=True))
        expect(page.get_by_text("Your communication preferences were saved.")).to_be_visible()
        assert_exposed(page, "status")
        # Narrow CSS viewport tests reflow; not a claim of actual browser zoom.
        for width in (768, 360, 320):
            page.set_viewport_size({"width": width, "height": 800})
            for section in ("Home", "Appointments & visits", "Test results & referrals",
                            "My health", "Care plan", "Settings"):
                keyboard_click(page, nav.get_by_role("button", name=section, exact=True))
                inspect_screen(page, f"Patient {section} at {width}px")
                for button in nav.get_by_role("button").all():
                    assert button.bounding_box()["height"] >= 44, "Navigation target below 44 CSS px"
        keyboard_click(page, page.get_by_role("button", name="Sign out", exact=True))
        expect(page.get_by_role("heading", name="Patient sign in", exact=True)).to_be_focused()
        browser.close()
    print("Accessibility tree, keyboard transitions, sampled contrast and reflow checks passed.")


if __name__ == "__main__":
    run()
