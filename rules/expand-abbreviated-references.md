# Expand abbreviated references

> **User preference — Robin (durable, all sessions/scopes/harnesses): every
> response expands each abbreviated reference it uses, at least once, in a
> table with one or two sentences of context per reference.**

Long sessions accrete codes — plan slices (`S3`), rulings (`R-32`), plan
commits (`c4`), open items (`P-18`), grill questions (`Q7`), PR numbers
(`#1616`), ADR sections (`ADR-0077 §7.3`), invariant codes (`IC-35`, `ME-11`,
`RR-3`), workflow or metric names used as shorthand. A reader cannot hold
them; Robin: "the context is impossible to follow otherwise."

## Rule

- Before sending, scan the draft for every token of those shapes.
- Add a **References** table — one row per distinct reference: the short
  form, then one or two sentences saying what it is and why it matters in
  this response. Fold it into a table the response already carries if one
  fits (a slice table, a status table); otherwise add it, at the top of a
  short response or the bottom of a long one.
- Prose may use the short form once the table is present.
- Never rely on an expansion given in an earlier response; each response
  stands alone.
- Repo docs, PR bodies and commit messages keep their own conventions
  (`core:pr-descriptions` already requires self-contained PR bodies); this
  rule is for chat-facing replies to Robin.
