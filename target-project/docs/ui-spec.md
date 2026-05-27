# UI Spec

## Reference Direction

The UI should closely match the provided grocery-list reference:

- bright white app surface,
- soft lavender action accents,
- oversized title with a light gray progress count,
- rounded task cards with subtle borders and shadows,
- generous vertical spacing,
- a lightweight mobile-first composition centered on the page.

## Component Map

- Header
  List title, progress count, edit icon, overflow icon.
- Composer card
  Plus icon and muted placeholder text.
- Todo row
  Toggle circle, task title, favorite star.

## Layout Notes

- Keep the page visually close to a phone-width list even on desktop.
- Preserve stacked cards with large corner radii and soft shadows.
- Use a pale neutral background around the main list surface.

## Wireframe

```text
+--------------------------------------------------+
| Groceries                             edit  more |
| 5/9                                              |
|                                                  |
| +  Add a task...                                 |
|                                                  |
| ( ) Manuka honey                            ☆    |
| (✓) Peanut butter                           ☆    |
| (✓) Extra virgin olive oil                  ★    |
| ( ) Blueberries                             ☆    |
| ( ) Dark chocolate                          ★    |
| (✓) Coffee beans                            ★    |
| ( ) Whipped cream                           ☆    |
| (✓) Strawberries                            ☆    |
| (✓) Organic maple syrup                     ★    |
+--------------------------------------------------+
```

## Practical Note

In practice, teams usually keep a screenshot reference plus a short component
spec like this one. A simple ASCII wireframe is useful as a supplement, but it
is not enough by itself for visual fidelity.
