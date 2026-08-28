# H2 alignment implementation plan

This temporary implementation note records the approved H2 alignment scope while the code changes are applied. It will remain as a concise design record after implementation.

1. Fix Step 4 HTML-to-Markdown list normalization so paragraphs nested inside list items do not break list markers onto separate lines.
2. Keep normalized ICE resource state for downstream semantics, but stop treating unlabelled Foundry resource internals (`type`, `value`, `max`) as automatically reader-facing.
3. Normalize ICE action presentation semantics so generic `Target: any` is omitted and Foundry damage targets such as `hitPoints` become reader vocabulary such as `HP`.
4. Suppress deterministic duplicate parent/action prose in the Step 6 ICE view: exact equality yields no repeated action prose; normalized parent-prefix overlap yields only the action-specific remainder.
5. Align the ICE renderer with the accepted Cybermancy rulebook shell: warm paper, Lato display typography, Noto Serif rules text, dark chapter band, GM-violet chapter/running marker, running header/footer, and outer page numbers.
6. Preserve the compact two-column H2 reference grammar, 10.5 pt minimum rules text, Sentry/Wall grouping, and source-fidelity/overflow regression gates.
7. Update regression tests so the approved behavior is deterministic and fail-closed before regenerating the six-entry visual proof.
