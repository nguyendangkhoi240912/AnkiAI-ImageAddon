# Publishing AnkiAI on AnkiWeb

## Package

```bash
./update.sh --bump-minor
# Creates dist/AnkiAI_ImageAddon-5.1.0.ankiaddon
```

## Upload

1. Log in at [https://ankiweb.net/shared/addons](https://ankiweb.net/shared/addons)
2. Upload the `.ankiaddon` file
3. Set **Minimum Anki version** to `25.09.2` (see `manifest.json`)
4. Paste the add-on description from `README.md` (Features section)

## Auto-update for users

After publication, set in `AnkiAI_ImageAddon/manifest.json`:

```json
"homepage": "https://ankiweb.net/shared/info/<YOUR_ADDON_ID>"
```

Users install via **Tools → Add-ons → Get Add-ons** with your code.

Bump `"mod"` (Unix timestamp) in `manifest.json` whenever you release a new build so Anki checks for updates.
