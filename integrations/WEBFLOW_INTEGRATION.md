# Webflow CMS Integration Guide

## Overview

The NRHOF kiosk integrates with Webflow CMS to fetch and display band, album, and song data. This document provides everything you need to know about working with Webflow data in this project.

## Architecture

### Components

1. **`integrations/webflow_client.py`** - API client for Webflow v2
2. **[integrations/webflow_cache.py](cci:7://file:///Users/ianheidt/CascadeProjects/nrhof-matrix-kiosk/integrations/webflow_cache.py:0:0-0:0)** - Local caching with pagination
3. **Cache Storage** - [runtime/webflow_cache/](cci:7://file:///Users/ianheidt/CascadeProjects/nrhof-matrix-kiosk/runtime/webflow_cache:0:0-0:0) (JSON files, gitignored)

### Data Flow
App Startup → Webflow API (paginated) → Local Cache (JSON) → Scenes (instant read) ↓ 24hr refresh cycle


## Webflow API v2 Key Concepts

### 1. Field Naming Convention

Webflow converts field names to **kebab-case** (hyphenated):

| CMS Field Name | API Field Name |
|----------------|----------------|
| `nerdRockList` | `nerd-rock-list` |
| `albumArt` | `album-art` |
| `membersCurrent` | `members---current` |
| `dateFormed` | `date-formed-2` |

**Rule**: Spaces and capitals become hyphens. Multiple capitals = multiple hyphens.

### 2. Reference Fields (CRITICAL)

Reference/link fields store **UUIDs**, not readable text:

```python
# ❌ WRONG - This won't work
filter_list='NR-38'

# ✅ CORRECT - Use the UUID
filter_list='a44a925c638540818d3602d8fd017a64'

How to find UUIDs:

Enable debug logging (see Debugging section)
Run app and check logs for field values
Store UUIDs as constants
3. Data Structure
All Webflow items follow this structure:

{
  "id": "item-uuid",
  "cmsLocaleId": "locale-uuid",
  "lastPublished": "2024-01-01T00:00:00.000Z",
  "lastUpdated": "2024-01-01T00:00:00.000Z",
  "createdOn": "2024-01-01T00:00:00.000Z",
  "isArchived": false,
  "isDraft": false,
  "fieldData": {
    "name": "Band Name",
    "slug": "band-name",
    "rank": 1,
    "nerd-rock-list": "uuid-reference",
    "albums": ["uuid1", "uuid2"],
    "color": "#ff0000"
  }
}

NRHOF Collections
Bands Collection
Collection ID: 66594971465c86eb74b1d898
Items: 38
Pagination: 1 API call

Key Fields

fieldData = {
    'name': str,                    # Band name
    'slug': str,                    # URL-friendly name
    'rank': int,                    # 1-38 ranking
    'nerd-rock-list': str,          # UUID reference to list (NR-38, NR-18, etc.)
    'logo': str,                    # Logo URL or UUID
    'logo-lottie': str,             # Lottie animation URL
    'color': str,                   # Hex color code
    'complimentary-color---dark': str,  # Dark theme color
    'spotify-embed': str,           # Spotify embed code
    'members---current': str,       # Current members text
    'location': str,                # Band location
    'date-formed-2': str,           # Formation date
    'short': str,                   # Short description
    'lyric-1': str,                 # Featured lyric
    'lyrics---scrolling': str,      # Scrolling lyrics
    'card-pic-1': str,              # Card image URL
    'card-attributes': str,         # Card metadata
    'band-nerdstage-3': str,        # Nerdstage level 3
    'band-nerdstage-4': str,        # Nerdstage level 4
    'quote-lottie': str,            # Quote animation
}

Known UUID References
# Nerd Rock Lists
NR38_LIST_UUID = 'a44a925c638540818d3602d8fd017a64'
# Add more as discovered

Albums Collection
Collection ID: 665fb5a92a7824458817d3c8
Items: 487
Pagination: ~5 API calls

Key Fields
fieldData = {
    'name': str,                # Album name
    'slug': str,                # URL-friendly name
    'band': str,                # Band name (text, not UUID)
    'year': str,                # Release year
    'score': str | None,        # Album score
    'coverPic': str | None,     # Cover art URL
    'thumbnailPic': str | None, # Thumbnail URL
    'nerdstage': str | None,    # Nerdstage level
    'type': str,                # Album type (LP, EP, etc.)
    'discogs': str | None,      # Discogs URL
    'vinyl': bool,              # Available on vinyl
    'cd': bool,                 # Available on CD
    'cassette': bool,           # Available on cassette
    'digital': bool,            # Available digitally
    'spotify': str | None,      # Spotify URL
    'appleMusic': str | None,   # Apple Music URL
    'amazonMusic': str | None,  # Amazon Music URL
}

Songs Collection
Collection ID: 66c681c5ad30e56ad9e658c8
Items: 10
Pagination: 1 API call

Key Fields
fieldData = {
    'name': str,        # Song title
    'slug': str,        # URL-friendly name
    'album': str,       # UUID reference to album
    'time': str,        # Duration (e.g., "3:45")
    'score': str,       # Song score
}

Usage Examples
Fetching Filtered Bands
from integrations.webflow_cache import WebflowCache, WebflowCacheManager
from integrations.webflow_client import create_webflow_client

# Initialize
client = create_webflow_client(config, logger)
cache = WebflowCache(logger=logger)
manager = WebflowCacheManager(client, cache, logger)

# Refresh cache (respects 24hr staleness)
manager.refresh_all(force=False)

# Get NR-38 bands (using UUID)
nr38_bands = manager.get_bands(filter_list='a44a925c638540818d3602d8fd017a64')

# Get all bands
all_bands = manager.get_bands()

# Get albums
albums = manager.get_albums()

# Get songs
songs = manager.get_songs()

Adding New Filtered Lists
Find the UUID:
# Add temporary debug logging
for band in all_bands:
    list_val = band.get('fieldData', {}).get('nerd-rock-list')
    name = band.get('fieldData', {}).get('name')
    print(f"{name}: {list_val}")

Add constant:
# In your scene or constants file
NR18_LIST_UUID = 'your-uuid-here'

Use it:
nr18_bands = manager.get_bands(filter_list=NR18_LIST_UUID)

Cache Management
Cache Behavior
Location:
runtime/webflow_cache/
Format: JSON files per collection
Staleness: 24 hours (configurable)
Refresh: Background thread on app startup
Offline: Works with cached data

Cache Files
runtime/webflow_cache/
├── metadata.json       # Cache metadata and timestamps
├── bands.json         # 38 band items (~186KB)
├── albums.json        # 487 album items (~579KB)
└── songs.json         # 10 song items (~5KB)

Force Refresh
# In app_initializer.py
manager.refresh_all(force=True)  # Ignores staleness check

Clear Cache
# Clear specific collection
cache.clear('bands')

# Clear all
cache.clear()

Rate Limits
Webflow API v2 Limits:

~60 requests per minute per token
100 items per page (max)
Our Usage:

Bands: 1 request (38 items)
Songs: 1 request (10 items)
Albums: 5 requests (487 items)
Total: 7 requests per refresh
Frequency: Once per 24 hours
Result: Well within limits! 🎉

Debugging
Enable Debug Logging
In
webflow_cache.py
, add to
_fetch_all_pages()
:_
if collection_name == 'bands' and offset == 0:
    first = items[0]
    self.logger.info(f"First item keys: {list(first.keys())}")
    self.logger.info(f"fieldData keys: {list(first['fieldData'].keys())}")
    for key, val in first['fieldData'].items():
        self.logger.info(f"  {key}: {val}")

In
webflow_cache.py
, add to
get_bands()
:
unique_vals = set(b.get('fieldData', {}).get('nerd-rock-list') for b in bands)
self.logger.info(f"Unique nerd-rock-list values: {unique_vals}")

Common Issues
Problem: Filter returns 0 results
Solution: You're using a string instead of UUID. Check logs for actual UUID value.

Problem: Cache not refreshing
Solution: Delete
runtime/webflow_cache/metadata.json
 or set force=True

Problem: Missing fields
Solution: Check kebab-case conversion. membersCurrent → members---current

Configuration
Environment Variables (.env)
WEBFLOW_API_TOKEN=your_token_here
WEBFLOW_SITE_ID=your_site_id
WEBFLOW_COLLECTION_ID_BANDS=66594971465c86eb74b1d898
WEBFLOW_COLLECTION_ID_ALBUMS=665fb5a92a7824458817d3c8
WEBFLOW_COLLECTION_ID_SONGS=66c681c5ad30e56ad9e658c8

Config File (config.yaml)
integrations:
  webflow:
    enabled: true
    sync_window: 86400.0      # 24 hours in seconds
    retry_backoff_max: 300    # Max backoff for errors

    Future Enhancements
Potential Improvements
ETag Support: Use conditional requests to save API calls
Webhook Integration: Real-time updates when CMS changes
UUID Resolver: Auto-resolve reference fields to readable names
Manual Refresh Hotkey: Force refresh without restarting (e.g., F5)
Cache Prewarming: Fetch on first install before app starts
Adding New Collections
Add collection ID to .env
Add to
WebflowCacheManager.refresh_all()
Add getter method (e.g., get_venues())
Document field structure here

Resources
Webflow API v2 Docs
Rate Limits
Collection Items Endpoint

Quick Reference
# Constants
NR38_LIST_UUID = 'a44a925c638540818d3602d8fd017a64'

# Get filtered bands
bands = cache_manager.get_bands(filter_list=NR38_LIST_UUID)

# Access band data
for band in bands:
    name = band['fieldData']['name']
    rank = band['fieldData']['rank']
    color = band['fieldData']['color']
Last Updated: 2025-11-06
Webflow API Version: v2
Cache Version: 1.0
