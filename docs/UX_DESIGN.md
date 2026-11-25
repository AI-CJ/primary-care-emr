# Research-driven UX redesign

## Design choices

The clinical workspace prioritizes task retrieval and operational awareness. The patient experience uses a distinct lighter palette and explicit task labels. Both use original inline SVG artwork. Dashboard and appointment summaries derive from existing authorized API endpoints rather than example counts; empty, loading, and unavailable states are separate.

The initial redesign is informed by [NIST health IT interface guidance](https://www.nist.gov/publications/technical-basis-user-interface-design-health-it), the [systematic review of patient portal suggestions](https://pmc.ncbi.nlm.nih.gov/articles/PMC8075519/), and [WCAG 2.2](https://www.w3.org/TR/WCAG22/). These support user-centered organization and measurable accessibility, not a universally optimal layout. Patient controls target at least 44 CSS pixels where possible; this is a project target, not an assertion of conformance.

## Validation

Browser regression tests exercise sign-in, chart access, appointment navigation, patient home, preferences and reset in the isolated browser and API-backed execution modes. The [release audit](UX_AUDIT.md) records the exact verified revision, test results and coverage limits. These automated checks are not representative clinician or patient usability studies.

## Clinical chart context

The summary presents active conditions, active medications and the latest dated vital record above existing clinical activity and lifecycle controls. Each panel loads independently and distinguishes missing records from request failure. The latest vital record is selected by recorded date (ID breaks same-date ties); values are not combined across dates or interpreted. The chart header stays visible on larger screens, and an allergy context panel displays recorded active allergies and distinguishes historical, empty and unavailable records. Empty records are not evidence of confirmed absence. The existing detailed chart sections remain the authoritative editing surfaces. These original components use existing patient-scoped endpoints and do not add dependencies or change authorization.

Visit documentation groups the editable clinical note separately from patient-facing instructions, shows a clear draft/finalized status, and retains existing explicit review and finalization controls. The browser regression exercises saving and finalizing a standalone note with patient instructions; appointment-linked notes continue to use existing safeguards.

## Patient reading and navigation

Read-only portal sections load again on return; appointment request and settings forms retain local input while navigating. Section navigation moves keyboard focus to the newly displayed heading, with larger labeled controls and text and a responsive grid. Appointment grouping distinguishes upcoming or same-day open visits, earlier open visits and closed history; calendar labels preserve recorded dates and times rather than converting them across time zones. Date-only eligibility is unchanged and the server remains authoritative. All returned medication and appointment history remains available. Released lab results lead the results page, earlier released results are expandable, and pending, unreleased and cancelled requests are separate. The API remains responsible for release and ownership; free-text results are displayed without invented units, reference ranges or interpretation. This approach draws on [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and the [review of laboratory presentation formats](https://www.jmir.org/2024/1/e53993/), while acknowledging the application does not have structured laboratory values. No new dependency or third-party asset was added. Automated tests cover appointment grouping, date formatting, lab grouping and patient navigation; full usability and accessibility evaluation still require representative users and assistive technology.

## Browser startup

The public application initializes its pinned Python runtime and tab-local database on the sign-in screen. Starting that work before credential submission overlaps initialization with the time a visitor spends choosing an account. The status text distinguishes preparation from account verification. The HTTP-backed application continues to authenticate through its server without the browser initialization step. Authentication parameters and reset semantics are unchanged.

The release audit records measured preparation and sign-in times. The initial runtime load remains a trade-off of hosting the full application on a static site.

## Reference captures

The interactive browser CI job can save screenshots of the built application at the actual staff and patient workflow states. The images are captured from the isolated local workspace, not a design mockup or a real patient system. Reproduction instructions are in the [frontend guide](../frontend/README.md#capture-reference-screenshots).

## Interface refinement

The follow-up visual pass uses actual desktop and mobile captures as its reference. A shared set of original SVG line icons identifies account roles, worklists and patient tasks without replacing text labels. The sign-in layout is more compact, preparation feedback has its own spacing and status indicator, staff queues form a balanced grid, and the legal notice retains its safety information in a shorter form. No external artwork, fonts or dependencies are introduced.

The interaction pass places the next appointment before the patient home navigation, shows five recent timeline entries with the remaining returned history available on request, and labels a capped appointment-request count as 100+ rather than an exact total. Staff navigation transfers focus to the destination heading while retaining existing appointment- and note-specific focus behavior. Mobile chart navigation distinguishes the open chart from the patient directory; the directory loads when visited and can clear its search. Sign-out uses the existing staff draft protection and checks unsaved patient preference or appointment-request inputs, including forms retained when hidden. Preference saving is disabled until a value changes. These changes are verified through the actual browser workflow and focused frontend tests, not a claim of complete clinical usability validation.
