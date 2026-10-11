# Mapping Rows to Cells Without Lying to the User

The write side is easy; the *classification* side is what makes a sync trusted. A
report that mislabels its own gaps starts an investigation into data loss that
never happened.

## Build two indexes, not one

- **Event index** — what the source rows say to write (the cells to tick).
- **Existence index** — every entity row that exists, built from the entity table
  regardless of whether it has events yet.

Classify each target row against both, and never derive "this row is missing from
the database" from the event index: a row with no events yet looks absent. Report
three distinct groups per sheet:

1. matched and written,
2. **exists but has no events yet** (normal, no action),
3. **not found** — split further by role/kind, because support/admin accounts that
   legitimately have no group should not read as lost students.

For group 3, also check whether the identifier appears *anywhere* in the target
sheet: "present in the data but no sheet for its group" needs a new sheet or a
re-grouping, while "not in this dataset at all" (another cohort, a test account)
needs nothing. Those two lead to opposite actions, so never merge them.

## Match every identity alias

An entity's identifier often lives in more than one column, and the application
itself joins on the alternatives (`a = b OR a = c`). Index **all** of them and
write the mark for every value found, or half the roster reports as missing.

Only accept values that are shaped like the identifier (digits-only and long
enough for a NIM-style id) — otherwise a display name or e-mail becomes a phantom
row that matches nothing.

## Group keys arrive in mixed formats

The same group reaches the spreadsheet as `A`, `TE A`, or
`S1 Teknologi Listrik A`, depending on when and how the row was imported. Generate
candidate sheet names from the parts (prefix from the department, letter from the
code, the raw code itself) and resolve them against the sheet names that **exist**
in the workbook. Building one string and comparing it fails on every import that
used another convention.

## Free-text rows live in the key column

Rosters carry note rows under the list — a day name, a time range, a room. Skip
values that are not identifier-shaped and count them as "skipped non-id rows"
instead of listing them as missing entities.

## Non-boolean states in a checkbox grid

A checkbox carries exactly ONE fact (the one worth counting — usually "attended").
Every other domain state (permission, illness, unexcused absence, approved
reschedule) has to live in the cell's **formatting**: colour + note, checkbox left
empty.

**The palette is the user's, not yours.** If they already wrote conditional
formatting for this, their formulas ARE the spec — read them and translate the
rules (which column holds the timestamp, which holds the status, which holds the
approval flag) instead of inventing a scheme. States they did not ask for default
**off** (empty colour property = skip), so a well-meant extra colour never shows up
as noise on their sheet.

| Domain state | Checkbox | Cell |
|---|---|---|
| attended | TRUE | untouched |
| attended + approved reschedule | TRUE | green + note |
| approved reschedule (not attended yet) | empty | green + note |
| leave (permission, illness) | empty | yellow + note |
| unexcused absence | empty | off by default; opt in per property |

Note text: `Absen: <state> · <date>` plus any extra qualifier, so the cell explains
itself without the database.

**Several records can hit one cell → fix a precedence and recompute every run.**
Rank the states (approved reschedule > leave > unexcused) and pick the winner per
cell; because the colour is derived from current source state, a record moving
from "leave" to "approved" flips yellow → green on the next sync with no extra
logic. Flatten a group of same-kind states into one colour when the user's own
formulas do (they often treat permission and illness alike).

**Format only the managed block.** The cells you may touch are the ones you
compute; the row number, name, group and total columns never get a colour or a
note from you. Assert it in the harness — a stray `setBackgrounds` over a wider
range is invisible in review and edits the user's sheet.

**Records you cannot route get a marker on the row, not just a line in the log.**
When a record has no marker/session/date that maps to a managed column, do not
guess a column and do not settle for a report count the user never opens: colour
the row's **identity cell** (the key/NIM cell) with a distinct colour and put the
explanation in that cell's note — `Absen: <state> · <date> (no meeting marker —
check manually)`. One cell can list several such records (join with newlines). The
marker clears itself as soon as the record becomes routable or is deleted, and the
footer names the marker colour so the count in the log maps to something visible.

**Ownership rule (the part that bites):** on every run, only clear a colour that
matches your own palette and a note that starts with your own prefix. A re-sync
that blanks any other background wipes the user's hand-made highlighting, and they
will not notice until it matters. Keep the palette and the on/off switch in Script
Properties so they can be tuned without a code change.

Two details make the clearing actually work:

- **Compare colours case-insensitively.** The Sheets API returns lowercase hex
  (`#fff2cc`) while the constant in the code is usually uppercase: an exact
  compare silently never matches and stale colours accumulate forever.
- **Keep the colours you shipped in earlier versions in the clearable set.**
  Changing a default (or turning a state off) must still clean the marks the
  previous palette left behind, or the sheet keeps a colour that no longer means
  anything.

## Report shape

Per group: rows in the block, cells changed, "exists but no events yet", "not
found" (first few values + the total), skipped non-id rows. Footer: **which
database/project the run read** and the **origin of each written value** (chosen
meeting / session title / date match / explicit column). Those two lines are what
the user checks first, and they make a wrong target obvious in one glance.
