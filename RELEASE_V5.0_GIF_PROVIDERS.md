# 🎉 AnkiAI ImageAddon v5.0 - Release Notes

**Release Date**: May 26, 2026

---

## ✨ Major Features Added

### 🎬 5 GIF/Animated Image Providers Integrated

We're thrilled to announce full integration of **5 professional animated image sources**:

1. ✅ **KLIPY** - Free GIF platform with localization support
2. ✅ **Pixabay GIFs** - High-quality GIFs with excellent copyright handling
3. ✅ **IconScout** - Animated icons (335,000+ options) - perfect for concepts
4. ✅ **GIPHY** - World's largest GIF library (reaction GIFs, motion assets)
5. ✅ **Tenor** - Smart search with keyword suggestions (deprecating 2026-06-30)

---

## 🎯 What's New in v5.0

### New Capabilities

- 🎬 **Search for GIFs** alongside static images
- 🌍 **Localization support** (KLIPY) for culturally-appropriate learning materials
- 🎭 **Animated Icons** (IconScout) for vocabulary & concept visualization
- ⚡ **Smart Provider Routing** - automatically selects best provider for "gif", "animated", "motion" searches
- 🛡️ **Adaptive Delay Manager** - intelligent rate limiting with automatic backoff

### Improvements

- 📈 **20+ image sources total** (was 4-10 before)
- 🔄 **Automatic Provider Fallback** - if GIPHY fails, try Tenor/KLIPY
- 📊 **Smart Domain Routing** - AI determines if search needs GIF vs static image
- 🚀 **Deprecation Handling** - Tenor support with automatic disable after 2026-06-30
- 💾 **Optimized concurrent requests** - max 10 providers in parallel

---

## 📋 Complete Provider List (20+)

### Animated Providers (NEW)
- KLIPY (Free, Localized)
- Pixabay GIFs (Free, Copyright-friendly)
- GIPHY (Free Beta, Huge library)
- Tenor (Free*, Deprecating 2026-06-30)
- IconScout (Limited free)

### General Image Providers
- Pexels, Unsplash, Pixabay, Flickr
- Google Custom Search, DuckDuckGo, Yandex
- Openverse, Wikimedia, Lorem Picsum
- Library of Congress, Met Museum, Europeana
- Noun Project

### Scientific Providers
- PubChem, ChEMBL, RCSB, PhyloPic
- ISIC, Europe PMC, NASA Images
- CodeCogs, Bioicons

---

## 🔧 Technical Integration

### Code Changes

**File**: `AnkiAI_ImageAddon/modules/providers/animated.py`
- Added 5 new provider classes
- Integrated with existing session management
- Rate limiting & error handling

**File**: `AnkiAI_ImageAddon/modules/provider_registry.py`
- Added domain routing for "animated" searches
- Created fallback provider list
- Added `has_any_animated_provider()` function
- Tenor deprecation check

**File**: `AnkiAI_ImageAddon/config.json`
- Added API keys:
  - `klipy_app_key`
  - `giphy_api_key`
  - `tenor_api_key`
  - `iconscout_api_token`
  - *pixabay_api_key (existing, now supports GIFs)*

### Domain Routing
```python
DOMAIN_PROVIDERS["animated"] = [
    "klipy",
    "giphy", 
    "tenor",
    "pixabay_animated",
    "iconscout"
]
```

---

## 📚 Documentation

New documentation files created:

1. **GIF_ANIMATED_PROVIDERS_GUIDE.md** 
   - Complete guide to each provider
   - API key retrieval steps
   - Use cases & examples
   - Pricing & limitations
   - Troubleshooting

2. **GIF_INTEGRATION_SUMMARY.md**
   - Technical integration details
   - Provider implementations
   - Domain routing explanation
   - Testing information

3. **GIF_QUICK_REFERENCE.md**
   - Quick 5-minute setup guide
   - API key quick links
   - Use case examples
   - Keyword suggestions

4. **Updated README.md**
   - Added v5.0 features section
   - GIF provider overview
   - Usage instructions

---

## 🚀 Usage

### Quick Start
1. Get API keys from 1-2 providers (KLIPY & Pixabay recommended)
2. Update `config.json` with your API keys
3. Restart Anki
4. Browse → Select cards → AnkiAI → **Search for GIFs**
5. Enter keyword → Select GIF → Done!

### Examples
```
Vocabulary: "running" → KLIPY GIF with culturally appropriate motion
Science: "photosynthesis" → Pixabay animated process diagram
Emoji: "happy" → GIPHY reaction GIF
```

---

## 💡 Key Features

### Smart Provider Selection
- User types "animated cat" → Automatically routes to GIF providers
- User types "cat" → Balanced between static images & GIFs
- Adaptive selection based on search terms

### Rate Limiting Protection
- Automatic 100-2000ms delays between requests
- Exponential backoff on 429 errors
- Per-provider reset after 1 hour
- Maximum 10 concurrent providers

### Fallback Strategy
```
Primary: KLIPY
Fallback: GIPHY
Final Fallback: Tenor (until 2026-06-30)
```

### Quality Assurance
- All URLs validated before adding
- Timeout protection (6-8 seconds per provider)
- Automatic error logging for debugging

---

## 🛡️ Tenor Deprecation

Google announced Tenor API will close on **June 30, 2026**.

**What we did:**
- Added `is_tenor_deprecated()` function
- Automatic disable after deprecation date
- Warning logged when attempting to use deprecated Tenor
- Users encouraged to switch to KLIPY/Pixabay

**Migration path:**
```
Now → Use Tenor (still works)
After 2026-06-30 → Automatic fallback to GIPHY/KLIPY
```

---

## 📊 Compatibility & Performance

### Supported Platforms
- ✅ Windows (with Anki 24.04+)
- ✅ macOS (with Anki 24.04+)
- ✅ Linux (with Anki 24.04+)

### Performance Metrics
- Average search time: 1-3 seconds (5 providers)
- Batch processing 100 cards: ~2-3 minutes
- Memory usage: ~50-100MB for 20+ providers

### Concurrent Requests
- Default: 10 providers in parallel
- Configurable via `max_concurrent_providers`
- Thread-safe with connection pooling

---

## 🔗 API Information

### KLIPY
- Base: `https://api.klipy.ai/api/v1/{app_key}/gifs/search`
- Formats: GIF, MP4
- Localization: ✅ Yes
- Rate limit: Generous for personal use

### Pixabay
- Base: `https://pixabay.com/api/`
- Formats: JPG, PNG, GIF (filtered by image_type)
- Rate limit: 100 requests/hour
- Copyright: CC0 (no attribution needed)

### GIPHY
- Base: `https://api.giphy.com/v1/gifs/search`
- Formats: GIF, WebP, MP4
- Rate limit: Depends on plan
- Note: Beta key for personal use

### Tenor
- Base: `https://tenor.googleapis.com/v2/search`
- Formats: GIF, WebP, MP4
- ⚠️ Deprecated: June 30, 2026
- Automatic fallback after date

### IconScout
- Base: Multiple endpoints (with fallback logic)
- Formats: GIF, Lottie JSON, SVG, MP4
- Defensive approach: Gracefully handles API changes

---

## 📝 Configuration Examples

### Minimal Setup (2 providers)
```json
{
    "klipy_app_key": "YOUR_KEY",
    "giphy_api_key": "YOUR_KEY"
}
```

### Maximum Coverage (5 providers)
```json
{
    "klipy_app_key": "YOUR_KEY",
    "giphy_api_key": "YOUR_KEY",
    "tenor_api_key": "YOUR_KEY",
    "pixabay_api_key": "YOUR_KEY",
    "iconscout_api_token": "YOUR_TOKEN"
}
```

### Optimized for Speed
```json
{
    "max_concurrent_providers": 5,
    "base_delay_ms": 50,
    "enable_adaptive_delay": true,
    "klipy_app_key": "YOUR_KEY"
}
```

---

## 🧪 Testing

### Unit Tests
- ✅ `tests/core/test_delay_and_rate_limit.py` - Rate limiting validation

### Integration Examples
```python
from AnkiAI_ImageAddon.modules.providers import KLIPYProvider

provider = KLIPYProvider("YOUR_KEY")
results = provider.search("running", per_page=3)
# Returns: [{"url": "...", "title": "...", "provider": "klipy"}]
```

---

## 🐛 Bug Fixes & Improvements

- ✅ Fixed provider initialization error handling
- ✅ Improved session pooling for concurrent requests
- ✅ Enhanced error logging for debugging
- ✅ Better timeout management across providers
- ✅ Consistent URL validation

---

## 📈 Future Roadmap

### Planned for v5.1+
- [ ] Video provider support (MP4/WebM)
- [ ] Pinecone vector DB for smart caching
- [ ] Custom domain routing via AI analysis
- [ ] Batch GIF optimization
- [ ] GIF animation frame selection

### Under Consideration
- [ ] Local GIF cache with TTL
- [ ] GIF-to-WebP conversion for smaller sizes
- [ ] Animated icon library sync
- [ ] Provider health monitoring

---

## 📞 Support Resources

- **Full Guide**: See `GIF_ANIMATED_PROVIDERS_GUIDE.md`
- **Quick Start**: See `GIF_QUICK_REFERENCE.md`
- **Technical**: See `GIF_INTEGRATION_SUMMARY.md`
- **FAQ**: Check addon's error logs in Anki console

---

## 🎓 Learn More

### Recommended Keywords by Domain

**Vocabulary**
```
Verbs: running, jumping, dancing, writing, reading
Adjectives: happy, sad, angry, tired, hungry
Prepositions: above, below, beside, between, inside
```

**Science**
```
Biology: photosynthesis, mitosis, evolution, digestion
Chemistry: reaction, bonding, acid, base
Physics: gravity, motion, wave, particle
```

**Languages**
```
Common: hello, goodbye, thank you, please
Emotions: love, hate, fear, joy, surprise
Culture: festival, tradition, custom, holiday
```

---

## ✅ Deployment Checklist

- ✅ All providers implemented in `animated.py`
- ✅ All providers exported from `providers/__init__.py`
- ✅ All providers registered in `provider_registry.py`
- ✅ Domain routing configured
- ✅ Config template updated
- ✅ Documentation complete
- ✅ Testing ready
- ✅ Backward compatibility maintained

---

## 📄 Migration Guide for Users

### From v4.x to v5.0

1. **Update addon** - Download latest version
2. **Restart Anki** - Full initialization
3. **New API keys optional** - Still works with old static providers
4. **Try GIFs** - Browse → Search for GIFs (new feature)

### No Breaking Changes
- All existing configs work as before
- Old provider names still valid
- Image search functionality unchanged
- Backward compatible with all v4.x decks

---

## 🎉 Thank You

Thanks to the Anki community for inspiration and feedback!

Special thanks to KLIPY, Pixabay, GIPHY, Tenor, and IconScout for excellent APIs.

---

**Happy Learning with Animated Images! 🎬✨**

**AnkiAI ImageAddon v5.0**
