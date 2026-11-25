# Research-driven UX redesign

## Design choices

The clinical workspace prioritizes task retrieval and operational awareness. The patient experience uses a distinct lighter palette and explicit task labels. Both use original inline SVG artwork. Dashboard and appointment summaries derive from existing authorized API endpoints rather than example counts; empty, loading, and unavailable states are separate.

The initial redesign is informed by [NIST health IT interface guidance](https://www.nist.gov/publications/technical-basis-user-interface-design-health-it), the [systematic review of patient portal suggestions](https://pmc.ncbi.nlm.nih.gov/articles/PMC8075519/), and [WCAG 2.2](https://www.w3.org/TR/WCAG22/). These support user-centered organization and measurable accessibility, not a universally optimal layout. Patient controls target at least 44 CSS pixels where possible; this is a project target, not an assertion of conformance.

## Validation

Exercise actual sign-in, chart access, appointment navigation, patient home, preferences and reset in both browser modes. Distinguish automated regression checks from actual clinician and patient usability studies. No claim of clinical approval, certification, or representative-user validation is made.

## Clinical chart context

The summary presents active conditions, active medications and the latest dated vital record above existing clinical activity and lifecycle controls. Each panel loads independently and distinguishes missing records from request failure. The latest vital record is selected by recorded date (ID breaks same-date ties); values are not combined across dates or interpreted. The chart header stays visible on larger screens, and an allergy context panel displays recorded active allergies and distinguishes historical, empty and unavailable records. Empty records are not evidence of confirmed absence. The existing detailed chart sections remain the authoritative editing surfaces. These original components use existing patient-scoped endpoints and do not add dependencies or change authorization.
