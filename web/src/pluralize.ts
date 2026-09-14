/**
 * Simplified English pluralization for the type-create form.
 *
 * Deliberately naive — covers the common suffix rules only; irregular
 * nouns (child/children, mouse/mice) are the user's job via the manual
 * field. The backend has its own even simpler `name + "s"` fallback,
 * so this helper exists purely to pre-fill a smarter guess as the user
 * types the singular name.
 */
export function pluralize(name: string): string {
  const trimmed = name.trim();
  if (trimmed === "") {
    return "";
  }
  const lower = trimmed.toLowerCase();
  // box → boxes, church → churches, bush → bushes, buzz → buzzes
  if (/(s|x|z|ch|sh)$/.test(lower)) {
    return `${trimmed}es`;
  }
  // city → cities (consonant + y), but boy → boys (vowel + y)
  if (/[^aeiou]y$/.test(lower)) {
    return `${trimmed.slice(0, -1)}ies`;
  }
  // leaf → leaves (single -f; -ffe words like giraffe take plain -s)
  if (/[^f]f$/.test(lower)) {
    return `${trimmed.slice(0, -1)}ves`;
  }
  // -fe → -ves holds for a handful of common nouns only; everything
  // else (cafe, safe, giraffe) just takes -s
  if (/(kni|li|wi)fe$/.test(lower)) {
    return `${trimmed.slice(0, -2)}ves`;
  }
  return `${trimmed}s`;
}
