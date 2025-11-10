#!/usr/bin/env python3
"""Webflow CMS constants and UUID references.

This file contains known UUID references for Webflow CMS reference fields.
Reference fields in Webflow store UUIDs, not readable text, so we maintain
this mapping for filtering and lookups.

See integrations/WEBFLOW_INTEGRATION.md for more details.
"""

# Collection IDs (also in .env, but useful here for reference)
COLLECTION_ID_BANDS = "66594971465c86eb74b1d898"
COLLECTION_ID_ALBUMS = "665fb5a92a7824458817d3c8"
COLLECTION_ID_SONGS = "66c681c5ad30e56ad9e658c8"

# Nerd Rock List UUIDs
# The 'nerd-rock-list' field in bands contains these UUID references
NR38_LIST_UUID = "a44a925c638540818d3602d8fd017a64"  # The NR-38 list
# Add more list UUIDs as discovered:
# NR18_LIST_UUID = 'uuid-here'  # The NR-18 list
# NRHOF_LIST_UUID = 'uuid-here'  # Hall of Fame list

# Album Type UUIDs
# The 'type' field in albums contains these UUID references
ALBUM_TYPE_UUIDS = {
    "4262ef38e544375abd8743977f57d67c": "album",  # Studio albums
    "b62bf6bb291d5526756a107fe9ed8c14": "ep",  # EPs
    "de33be7c10d99644ab2e35542353e48f": "live",  # Live albums
    "0df73aee8d73a899700d9f276f4bb85b": "etc",  # Demos/Acoustic
    "8a6762e167ab1cca1451ff9a36f21b7e": "etc",  # Singles
}
