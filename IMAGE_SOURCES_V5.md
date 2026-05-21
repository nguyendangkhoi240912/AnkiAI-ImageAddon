# Image Sources v5.0

AnkiAI Image Addon integrates 20+ image APIs with AI domain routing.

## General sources (10)

| ID | API | Auth |
|----|-----|------|
| yandex | yandex.com/images (HTML) | None |
| duckduckgo | duckduckgo.com/i.js | None |
| google_cse | googleapis.com/customsearch/v1 | API key + cx |
| wikimedia | commons.wikimedia.org/w/api.php | None |
| unsplash | api.unsplash.com | Access key |
| pexels | api.pexels.com | API key |
| pixabay | pixabay.com/api | API key |
| flickr | flickr.com/services/rest | API key |
| noun_project | api.thenounproject.com/v2 | OAuth1 key+secret |
| openverse | api.openverse.engineering/v1 | Optional token |

## Scientific sources (10)

| ID | API | Auth |
|----|-----|------|
| wikimedia_smart | Wikimedia + Servier Medical Art category | None |
| bioicons | GitHub bioicons manifest | None |
| pubchem | pubchem.ncbi.nlm.nih.gov/rest/pug | None (5 req/s) |
| chembl | ebi.ac.uk/chembl/api/data | None |
| rcsb | search.rcsb.org + CDN images | None |
| phylopic | api.phylopic.org/images | None |
| isic | api.isic-archive.com/api/v2 | None |
| europe_pmc | europepmc.org/webservices/rest | None |
| nasa | images-api.nasa.gov/search | None |
| codecogs | latex.codecogs.com | None (math/LaTeX) |

## Legacy free (kept)

- lorem_picsum, loc, metmuseum, europeana (optional key)

## AI domain routing

AI returns JSON: `domain`, `keyword`, `precise_term`.

Domains: `general`, `medical`, `chemistry`, `biology`, `taxonomy`, `dermatology`, `space`, `math`.

Config: `enable_ai_provider_routing` (default: true).

## Config keys

```
pexels_api_key, unsplash_api_key, pixabay_api_key, flickr_api_key
google_api_key, google_cx
noun_project_api_key, noun_project_api_secret
openverse_api_token, europeana_api_key
enable_ai_provider_routing, max_concurrent_providers
```
