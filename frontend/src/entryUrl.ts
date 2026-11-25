/** Keep the visible URL free of marketing attribution without changing routes. */
export function cleanEntryUrl(href: string): string {
  const url = new URL(href)
  for (const key of [...url.searchParams.keys()]) {
    if (key.toLowerCase().startsWith('utm_')) url.searchParams.delete(key)
  }
  return url.href
}
