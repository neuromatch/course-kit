// Pure helpers for {nma-slides}. Python twins: nma_kit.media (slide_cdn_url,
// osf_slides_embed_url); both are tested against tests/fixtures/media/slide_urls.json.

/**
 * URL (jsDelivr's GitHub mirror) of a slide PDF published on the notebooks branch.
 * raw.githubusercontent.com can't be used: it sends X-Frame-Options: deny, so a
 * browser refuses to show it in an iframe. `day` is the page's folder under
 * notebooks/ ('' at the top).
 */
export function slideUrl(repo, branch, day, path) {
  const tail = ['notebooks', day, path]
    .map((part) => part.replace(/^\/+|\/+$/g, ''))
    .filter(Boolean)
    .join('/');
  return `https://cdn.jsdelivr.net/gh/${repo}@${branch}/${tail}`;
}

/** The OSF renderer URL that shows an OSF slide deck in an iframe. */
export function osfSlidesEmbedUrl(id) {
  return `https://mfr.ca-1.osf.io/render?url=https://osf.io/${id}/?direct%26mode=render%26action=download%26mode=render`;
}
