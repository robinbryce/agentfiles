# Decision data format

One JSON object. `build.py check` validates it and lists every problem; `build.py init` prints a
complete example.

| Key | Shape | Rules |
|---|---|---|
| `meta.title` | string | The page's name, at most 60 characters |
| `meta.eyebrow` | string | Optional context line: plan id, session, "as of" date |
| `meta.lede` | string | Optional; one or two sentences on what the map covers |
| `meta.pivot` | `{id, text}` | Optional; the decision that reshaped most others, and why |
| `themes` | `[{id, name, blurb}]` | 1 to 8 design areas, in display order; each gets a colour slot |
| `layers` | `[{id, name}]` | Groups of components, in display order |
| `components` | `[{id, name, layer, desc}]` | Parts of the system; `name` at most 32 characters |
| `decisions` | see below | At least one |
| `open` | `[{id, title, text, rec, relates}]` | Open questions; ids must not reuse decision ids |
| `resolved` | `[string]` | Conflicts settled because one decision replaced another |
| `fold` | `[string]` | Doc text to fix where the decisions land |

A decision:

| Field | Rules |
|---|---|
| `id` | Unique; the session's own id |
| `theme` | A theme id |
| `title` | At most 36 characters; it must fit a graph chip |
| `status` | `in force`, `amended`, `superseded` or `proposed` |
| `text` | The decision as it stands, one to three sentences |
| `impacts` | Component ids it shapes; at least one unless superseded |
| `lands` | Where it is recorded (doc section, ADR, slice) |
| `supersededBy` | Decision ids; set exactly when `status` is `superseded` |
| `amendedBy` | Decision ids; set exactly when `status` is `amended` |

The builder computes the inverse links (`supersedes`, `amends`) and the theme colour slots. `extract`
strips them again, so its output is valid input.

```json
{
  "id": "Q27", "theme": "binding", "title": "Bind the salt to the transfer",
  "status": "in force",
  "text": "The salted delegation pins exactly one transfer and carries a one-use limit.",
  "impacts": ["leaf", "gate"], "lands": "ARC §5.3", "supersededBy": [], "amendedBy": []
}
```
