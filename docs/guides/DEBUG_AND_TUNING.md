# 🧪 AnkiAI v5.3 - Debugging & Performance Tuning Guide

**Version**: 5.3  
**Last Updated**: June 5, 2026

---

## 🔍 Performance Debugging

### 1. Enable Detailed Logging
Edit `config.json`:
```json
{
  "debug_mode": true,
  "log_level": "DEBUG"
}
```

Then monitor logs:
```bash
tail -f AnkiAI_ImageAddon/logs/ankiai.log | grep -E "HTTP|Session|Pool|Cache"
```

### 2. Monitor HTTP Session Health
Look for these log messages:
```
✅ Created session with pooling: 20 pools, 20 max per pool
⚠️ Session closed due to inactivity
❌ Session creation failed
```

### 3. Profile Concurrent Operations
Watch for:
```
Using 5 concurrent workers
HTTP request latency: 234 ms
Provider search time: 1200 ms
```

---

## ⚡ Performance Tuning

### For High-Speed Processing (>10 cards/second)
```json
{
  "max_concurrent_providers": 10,
  "max_concurrent_requests": 10,
  "image_download_timeout": 10,
  "image_download_retries": 1,
  "enable_image_optimization": false,
  "base_delay_ms": 50,
  "max_concurrent_providers": 10
}
```
⚠️ **Warning**: May hit rate limits with some providers

### For Stable Processing (Recommended Default)
```json
{
  "max_concurrent_providers": 8,
  "max_concurrent_requests": 8,
  "image_download_timeout": 15,
  "image_download_retries": 2,
  "enable_image_optimization": true,
  "base_delay_ms": 100,
  "max_delay_ms": 2000
}
```

### For Reliability (Slow but Safe)
```json
{
  "max_concurrent_providers": 4,
  "max_concurrent_requests": 4,
  "image_download_timeout": 20,
  "image_download_retries": 3,
  "enable_image_optimization": true,
  "base_delay_ms": 200,
  "max_delay_ms": 5000,
  "enable_rate_limit_protection": true
}
```

---

## 🚨 Common Issues & Solutions

### Issue: "All cards failed with 100% progress immediately"
**Symptoms**: 
- Progress bar shows 100% instantly
- All cards report failed

**Causes**:
1. Invalid API key
2. Field name mismatch
3. Network timeout

**Debug Steps**:
```bash
# Check logs for error type
grep -i "error\|fail" AnkiAI_ImageAddon/logs/ankiai.log | head -20

# Check specific note processing
grep "note_12345" AnkiAI_ImageAddon/logs/ankiai.log

# Check network connectivity
ping api.pexels.com
```

**Solutions**:
1. Verify API keys in config
2. Check field names match your note type
3. Check network connectivity
4. Increase timeouts if network is slow

---

### Issue: "Process is very slow (>30 seconds for 10 cards)"
**Symptoms**: 
- Takes 3+ seconds per card
- Other apps running fine

**Causes**:
1. Too many concurrent workers for system
2. Network latency
3. API rate limiting

**Debug Steps**:
```bash
# Check concurrent settings
grep "concurrent" config.json

# Check CPU/Memory
top -b -n 1 | head -10

# Check network:
curl -w "Time: %{time_total}s\n" https://api.pexels.com/
```

**Solutions**:
1. Reduce concurrent workers:
   ```json
   "max_concurrent_providers": 4,
   "max_concurrent_requests": 4
   ```
2. Check network connectivity
3. Enable adaptive delay protection
4. Try different time of day (less API load)

---

### Issue: "Memory keeps growing (~200+ MB)"
**Symptoms**:
- Memory usage constantly increasing
- Anki becomes sluggish
- Computer fans running loud

**Causes**:
1. Too many concurrent workers creating sessions
2. Image cache too large
3. Memory leak in session pooling

**Debug Steps**:
```bash
# Monitor memory in real-time
watch -n 1 'ps aux | grep -i anki'

# Check session count
grep "Creating new HTTP session" AnkiAI_ImageAddon/logs/ankiai.log | wc -l

# Expected: Should be <5 sessions total
```

**Solutions**:
1. Reduce concurrent workers
2. Clear cache: Remove `cache` from config
3. Restart Anki (clears session pool)
4. If persists: Check for provider errors

---

### Issue: "Getting rate limited (429 errors)"
**Symptoms**:
- See "429: Too Many Requests" in logs
- Processing slows down dramatically
- Some providers stop working

**Debug Steps**:
```bash
grep "429\|rate limit\|rate-limited" AnkiAI_ImageAddon/logs/ankiai.log

# Check which provider:
grep -B2 "429" AnkiAI_ImageAddon/logs/ankiai.log
```

**Solutions**:
1. **Reduce concurrent requests**:
   ```json
   "max_concurrent_providers": 4,
   "base_delay_ms": 300
   ```

2. **Enable adaptive delay** (already default):
   ```json
   "enable_adaptive_delay": true,
   "delay_increase_on_429": 500
   ```

3. **Use fewer providers**:
   - Remove expensive providers from config
   - Stick to free/fast providers: Pexels, Pixabay, Unsplash

4. **Increase wait times between batches**:
   - Process 50 cards, wait 10 minutes
   - Process 50 cards, wait 10 minutes
   - etc.

---

## 📊 Performance Metrics to Watch

### Healthy Session
```
HTTP Session: 1 created (shared)
Connection Pool: 20 connections, 20 max
Retry Strategy: 3 retries, 0.5s backoff
```

### Healthy Processing (per 100 cards)
```
Total Time: 60-80 seconds
Per Card: 0.6-0.8 seconds
Success Rate: 85-95%
Memory Used: 80-120 MB
```

### Warning Signs
```
⚠️ Multiple sessions created (>3): Reduce workers
⚠️ Memory >200 MB: Clear cache
⚠️ Time >2 sec/card: Check network
⚠️ Success <70%: Check API keys
⚠️ Many 429 errors: Reduce concurrency
```

---

## 🔧 Advanced Tuning

### HTTP Connection Pool Tuning
If you have specific network requirements, edit `http_session_manager.py`:

```python
# Current (optimal for most cases):
POOL_CONNECTIONS = 20
POOL_MAXSIZE = 20

# For cellular/WiFi (less stable):
POOL_CONNECTIONS = 10
POOL_MAXSIZE = 5

# For high-bandwidth (enterprise):
POOL_CONNECTIONS = 50
POOL_MAXSIZE = 50
```

### Cache TTL Tuning
Edit cache configuration in `api_handler.py`:

```python
# Current (good balance):
SearchContextCache(max_size=1000, ttl_hours=4)

# For frequently changing content:
SearchContextCache(max_size=500, ttl_hours=1)

# For stable content:
SearchContextCache(max_size=2000, ttl_hours=12)
```

---

## 📈 Optimization Checklists

### Before Large Batch (1000+ cards)
- [ ] Check available disk space (>2GB recommended)
- [ ] Close other applications
- [ ] Set config to "Stable" or "Reliable" profile
- [ ] Enable rate limit protection
- [ ] Have backup of Anki collection
- [ ] Start with 100 cards to test
- [ ] Monitor first 50 cards closely

### During Processing
- [ ] Watch for error patterns
- [ ] Monitor memory (should <200 MB)
- [ ] Note any provider errors
- [ ] Check success rate (should >80%)
- [ ] Save logs for analysis

### After Processing
- [ ] Verify card images loaded
- [ ] Check file sizes (should be 50-300 KB each)
- [ ] Review error messages
- [ ] Analyze performance metrics
- [ ] Adjust config for next batch if needed

---

## 🎯 Expected Performance Numbers

### Network Conditions
- **Fast (>50 Mbps)**: 0.5-0.7s per card
- **Good (10-50 Mbps)**: 0.7-1.0s per card
- **Medium (5-10 Mbps)**: 1.0-1.5s per card
- **Slow (<5 Mbps)**: 1.5-3.0s per card

### Hardware (CPU-bound)
- **Old (2-core, <2 GHz)**: 1.0-2.0s per card
- **Medium (4-core, 2-3 GHz)**: 0.6-1.0s per card
- **New (8-core, 3+ GHz)**: 0.4-0.7s per card

### Batch Sizes
- **Small (1-10)**: 5-10 seconds total
- **Medium (50-100)**: 40-60 seconds total
- **Large (500-1000)**: 400-700 seconds (~10 min)
- **Very Large (2000+)**: 800-1500 seconds (~15-25 min)

---

## 📋 Verification Tests

### Test 1: HTTP Session Consolidation
**Expected**: Single HTTP session for all providers

```bash
grep "Creating new HTTP session" ankiai.log | wc -l
# Should output: 2-3 (one for image downloads, one for API calls, one for AI)
```

### Test 2: Concurrent Worker Scaling
**Expected**: Workers increase with batch size

```bash
# For 10 cards:
grep "Using.*concurrent workers" ankiai.log
# Expected: 5 workers

# For 100 cards:
grep "Using.*concurrent workers" ankiai.log  
# Expected: 5-8 workers
```

### Test 3: Cache Efficiency
**Expected**: Good hit rate after first few searches

```bash
grep "Cache hit\|Cache miss" ankiai.log | tail -100
# Should see ~80% hits after warm-up
```

### Test 4: Memory Efficiency
**Expected**: Memory <150 MB for 100 cards

```bash
# Monitor during processing:
while true; do ps aux | grep -i anki | grep -v grep; sleep 2; done
# Look at RSS column - should not exceed 200 MB
```

---

## 🚀 Quick Performance Boost

**Change only one setting at a time and measure impact:**

1. **Fastest Possible** (with risks):
   ```json
   "max_concurrent_providers": 12,
   "image_download_timeout": 10,
   "base_delay_ms": 50
   ```
   Result: ~0.4s per card (but may get rate limited)

2. **Fast & Safe** (recommended):
   ```json
   "max_concurrent_providers": 8,
   "image_download_timeout": 15,
   "base_delay_ms": 100
   ```
   Result: ~0.7s per card

3. **Conservative** (most reliable):
   ```json
   "max_concurrent_providers": 4,
   "image_download_timeout": 20,
   "base_delay_ms": 200
   ```
   Result: ~1.2s per card (very reliable)

---

## 📞 Support

If you still have issues after trying these steps:

1. Collect logs:
   ```bash
   cp AnkiAI_ImageAddon/logs/ankiai.log ankiai_debug.log
   ```

2. Include in bug report:
   - `ankiai_debug.log` (last 500 lines)
   - `config.json` (without API keys)
   - System specs (CPU, RAM, OS)
   - Number of cards being processed
   - Error messages seen

3. Check for known issues in:
   - `BUGFIX_V5.2.md`
   - `TEST_AND_TROUBLESHOOT_V5.2.md`
   - Issue tracker on GitHub

---

**Version**: 5.3  
**Status**: Production Ready  
**Last Updated**: June 5, 2026
