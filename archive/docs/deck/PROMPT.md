# Master prompt — interactive pitch deck

The reusable prompt that generated the decks in this folder. Copy the block below, fill the
`«...»` slots, and paste it into a fresh session.

Two slots carry most of the weight. **"What I have actually built today"** is what keeps the
status slide trustworthy and stops the deck inventing results. **The raw material dump** should
be messy and specific — real numbers and citations beat a tidy outline, because the model can
structure your facts but cannot invent them.

---

````text
Build me a single-file, self-contained interactive scrollytelling deck about «SUBJECT».

════════════════════════════════════════════════════════
CONTEXT
════════════════════════════════════════════════════════
Audience:                 «WHO — e.g. my academic supervisor / investors / a hiring panel»
What they should do next: «THE ONE ACTION OR BELIEF YOU WANT»
Sections:                 «N, e.g. 12-15»
Tone:                     «e.g. rigorous and confident, not salesy»

What I have ACTUALLY built today (be blunt — this is the most important field here):
«e.g. accountant works and is tested; generators are stubs; no real datasets yet; X untested»

Raw material — dump it messily, structuring it is your job:
«architecture, tech stack, novelty, use cases, roadmap, hypotheses, risks, real numbers,
citations, team names, repo URL»

════════════════════════════════════════════════════════
STEP 1 — DESIGN PLAN FIRST. NO CODE YET.
════════════════════════════════════════════════════════
Output a short plan before writing anything:

1. SUBJECT WORLD — What are this subject's own materials, instruments, and vernacular?
   Derive the entire visual identity from that, not from generic "deck" conventions.
   (e.g. a privacy-certificate project → calibration certificates and lab assay reports.)
2. SIGNATURE DEVICE — Invent ONE visual motif that encodes something true about the
   content, and repeat it as rules, frames, brackets, and dividers throughout.
3. PALETTE — 4-6 named hex values. Bind colors to CONCEPTS, not decoration, and hold them
   consistent everywhere so a reader can decode a chart without a legend.
4. TYPE — 2+ roles (display / body / data-caption). System font stacks ONLY. Make the
   pairing deliberate and slightly unusual.
5. LAYOUT — the concept in one or two sentences.

AVOID these AI-default looks: warm cream + serif + terracotta; near-black with one acid-green
pop; purple-to-blue gradient hero; Inter or Space Grotesk as the "safe" pick; emoji as section
markers; everything centered; rounded corners everywhere; accent bar on rounded cards.

Then review your own plan: if any part reads like the generic default you'd produce for any
similar topic, revise it and tell me what you changed and why.

════════════════════════════════════════════════════════
STEP 2 — NARRATIVE, NOT A TOPIC LIST
════════════════════════════════════════════════════════
Structure it in ACTS with real tension and resolution:
  Act I   — the problem, made visceral
  Act II  — why the existing answers fall short
  Act III — what we build (the interactive core)
  Act IV  — the plan, honest status, and the ask

════════════════════════════════════════════════════════
STEP 3 — INTERACTIVITY THAT COMPUTES SOMETHING REAL
════════════════════════════════════════════════════════
Build 3-5 interactive moments.

CRITICAL RULE: each demo must actually RUN the thing it describes and measure its real
output. Never animate a pre-baked fake. Examples that satisfy this:
  - a parameter slider that runs the real algorithm and measures what comes out
  - a crypto demo using real crypto.subtle, not a fake hash string
  - a filter that genuinely narrows a real generated dataset

VERIFY BEFORE SHIPPING: run the numbers (Python or Node) and confirm the demo produces a
meaningful, non-flat, non-degenerate result across its whole input range. If it doesn't,
DO NOT fake it — tell me, and reframe that section around the honest result. A real null
result that supports the thesis beats a fabricated dramatic one.

════════════════════════════════════════════════════════
STEP 4 — HONESTY RULES (NON-NEGOTIABLE)
════════════════════════════════════════════════════════
- Anything illustrative, mocked, or target-state must be VISIBLY LABELLED as such on the
  slide itself — not merely mentioned to me in chat.
- Never present projected numbers as measured results.
- Include a status section honestly separating Built / Partial / Not started.
- If anything in my raw material is overclaimed, say so and correct it.

════════════════════════════════════════════════════════
STEP 5 — TECHNICAL CONSTRAINTS
════════════════════════════════════════════════════════
- ONE file, fully self-contained. NO external requests of any kind — no CDN scripts, no
  webfonts, no remote images. Inline everything; system font stacks only.
- Write page content only — no <!DOCTYPE>, <html>, <head>, or <body> wrapper tags.
- BOTH THEMES: define the palette as CSS custom properties on :root, redefine only the
  tokens under @media (prefers-color-scheme: dark), then again under :root[data-theme="dark"]
  and :root[data-theme="light"] so a toggle wins in both directions. Style components through
  tokens only — never hardcode a color inside a component rule.
- SVG GOTCHA: var() is unreliable inside SVG presentation attributes like fill="var(--x)".
  Style SVG through CSS classes instead.
- FLEX GOTCHA: use `justify-content: safe center` on full-height sections, or content taller
  than the viewport becomes unscrollable.
- Wide content (tables, diagrams, code) scrolls inside its own overflow-x:auto container.
  The page body must never scroll sideways.
- Keyboard nav (arrows / space / Home / End), visible focus states, scroll progress bar,
  section rail.
- Respect prefers-reduced-motion: kill ambient animation, keep interactivity.
- font-variant-numeric: tabular-nums anywhere digits are compared.
- Pause every requestAnimationFrame loop when its section is offscreen (IntersectionObserver).

════════════════════════════════════════════════════════
STEP 6 — VALIDATE BEFORE SHOWING ME
════════════════════════════════════════════════════════
Check and report: balanced braces/parens; every JS-referenced element ID exists in the HTML;
no dead or unreachable code; no connector lines crossing boxes in any diagram; no section
overflowing unreachably. Tell me what you verified and anything you had to fix.
````

---

## Follow-up prompts worth keeping

Once a first version exists, these are what actually improve it:

```text
Add one more interactive section that lets the reader «DO X» — same rule, it must run
the real computation and report measured output.
```

```text
The «SECTION» section feels flat. Give it a genuine "wait, what?" moment — something
that reframes what the reader assumed a sentence earlier.
```

```text
Verify every number on this page against the actual codebase. Flag anything that is stale,
projected, or unverifiable, and label or remove it.
```

```text
Review the design plan you wrote against the finished page. Where did the execution drift
toward a generic default? Fix those spots.
```

Run the third one before any real presentation — it is the check that catches a status slide
quietly going out of date.

---

## If you build this in a real repo instead of a chat artifact

React is not usable inside a chat artifact: the sandbox blocks every external host, so there is
no CDN to load it from, and inlining it costs ~140 KB for no benefit. In a normal project with
npm available, swap Step 5 for:

- Vite + React + TypeScript
- Framer Motion for scroll-triggered reveals and orchestrated sequences
- Tailwind for layout, but keep the palette in a CSS custom-property token layer and reference
  those — do not scatter raw color classes through components
- One component per section, plus a `<Deck>` shell owning keyboard nav and scroll progress
- Recharts or D3 for charts, with the "demos compute real values" rule intact — chart data must
  come from actually running the algorithm, not a hardcoded array

React buys component structure and better animation primitives; it costs portability, since you
can no longer paste one file somewhere and have it render.
