# -*- coding: utf-8 -*-
"""Agent Search Lite — Video Intelligence Layer.

Extracts metadata, subtitles, and transcripts from video platforms.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# yt-dlp Video Metadata Extraction
# ---------------------------------------------------------------------------

def extract_video_metadata(url: str) -> Dict[str, Any]:
    """Extract video metadata using yt-dlp.
    
    Supports:
    - YouTube
    - Vimeo
    - Dailymotion
    - Twitter/X video
    - Instagram video
    - TikTok
    - And 1000+ other sites
    """
    result = {
        "url": url,
        "title": "",
        "description": "",
        "duration": 0,
        "view_count": 0,
        "like_count": 0,
        "upload_date": "",
        "uploader": "",
        "thumbnail": "",
        "formats": [],
        "subtitles": [],
        "chapters": [],
        "tags": [],
        "categories": [],
    }
    
    try:
        # Check if yt-dlp is available
        cmd = ["yt-dlp", "--dump-json", "--no-download", url]
        
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if proc.returncode != 0:
            result["error"] = f"yt-dlp error: {proc.stderr[:200]}"
            return result
        
        # Parse JSON output
        data = json.loads(proc.stdout)
        
        result["title"] = data.get("title", "")
        result["description"] = data.get("description", "")
        result["duration"] = data.get("duration", 0)
        result["view_count"] = data.get("view_count", 0)
        result["like_count"] = data.get("like_count", 0)
        result["upload_date"] = data.get("upload_date", "")
        result["uploader"] = data.get("uploader", "")
        result["thumbnail"] = data.get("thumbnail", "")
        result["tags"] = data.get("tags", [])
        result["categories"] = data.get("categories", [])
        
        # Extract chapters
        chapters = data.get("chapters", [])
        for chapter in chapters:
            result["chapters"].append({
                "title": chapter.get("title", ""),
                "start_time": chapter.get("start_time", 0),
                "end_time": chapter.get("end_time", 0),
            })
        
        # Extract subtitles
        subtitles = data.get("subtitles", {})
        for lang, subs in subtitles.items():
            for sub in subs:
                result["subtitles"].append({
                    "language": lang,
                    "url": sub.get("url", ""),
                    "ext": sub.get("ext", ""),
                })
        
        # Extract formats (limited)
        formats = data.get("formats", [])
        for fmt in formats[-5:]:  # Last 5 formats
            result["formats"].append({
                "format_id": fmt.get("format_id", ""),
                "ext": fmt.get("ext", ""),
                "resolution": fmt.get("resolution", ""),
                "filesize": fmt.get("filesize", 0),
            })
        
    except FileNotFoundError:
        result["error"] = "yt-dlp not installed"
    except subprocess.TimeoutExpired:
        result["error"] = "yt-dlp timeout"
    except json.JSONDecodeError:
        result["error"] = "Failed to parse yt-dlp output"
    except Exception as exc:
        result["error"] = f"Video extraction failed: {exc}"
    
    return result


def extract_video_subtitles(url: str, lang: str = "en") -> Optional[str]:
    """Extract subtitles from a video."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as f:
            temp_path = f.name
        
        cmd = [
            "yt-dlp",
            "--write-subs",
            "--sub-langs", lang,
            "--sub-format", "srt",
            "--skip-download",
            "-o", temp_path.replace(".srt", ""),
            url,
        ]
        
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if proc.returncode == 0:
            # Find the subtitle file
            for f in os.listdir(os.path.dirname(temp_path)):
                if f.endswith(f".{lang}.srt"):
                    with open(os.path.join(os.path.dirname(temp_path), f), "r") as sf:
                        content = sf.read()
                    os.unlink(os.path.join(os.path.dirname(temp_path), f))
                    return content
        
        return None
        
    except Exception as exc:
        logger.debug(f"Subtitle extraction failed: {exc}")
        return None


def extract_video_thumbnail(url: str) -> Optional[str]:
    """Download video thumbnail."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            temp_path = f.name
        
        cmd = [
            "yt-dlp",
            "--write-thumbnail",
            "--skip-download",
            "-o", temp_path.replace(".jpg", ""),
            url,
        ]
        
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if proc.returncode == 0:
            # Find the thumbnail
            for f in os.listdir(os.path.dirname(temp_path)):
                if f.endswith((".jpg", ".webp", ".png")):
                    thumb_path = os.path.join(os.path.dirname(temp_path), f)
                    # Return as data URL or save path
                    return thumb_path
        
        return None
        
    except Exception as exc:
        logger.debug(f"Thumbnail extraction failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# YouTube-specific helpers
# ---------------------------------------------------------------------------

def youtube_search(query: str, limit: int = 10) -> Optional[Dict[str, Any]]:
    """Search YouTube using yt-dlp."""
    try:
        cmd = [
            "yt-dlp",
            f"ytsearch{limit}:{query}",
            "--dump-json",
            "--no-download",
        ]
        
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if proc.returncode != 0:
            return None
        
        results = []
        for line in proc.stdout.strip().split("\n"):
            if line:
                try:
                    data = json.loads(line)
                    results.append({
                        "title": data.get("title", ""),
                        "url": f"https://www.youtube.com/watch?v={data.get('id', '')}",
                        "duration": data.get("duration", 0),
                        "view_count": data.get("view_count", 0),
                        "uploader": data.get("uploader", ""),
                        "thumbnail": data.get("thumbnail", ""),
                        "source": "youtube",
                        "position": len(results) + 1,
                    })
                except json.JSONDecodeError:
                    continue
        
        if results:
            return {"success": True, "data": {"web": results}}
        
        return None
        
    except Exception as exc:
        logger.debug(f"YouTube search failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Video Platform Detection
# ---------------------------------------------------------------------------

def detect_video_platform(url: str) -> Optional[str]:
    """Detect which video platform a URL belongs to."""
    platforms = {
        "youtube.com": "youtube",
        "youtu.be": "youtube",
        "vimeo.com": "vimeo",
        "dailymotion.com": "dailymotion",
        "tiktok.com": "tiktok",
        "twitter.com": "twitter",
        "x.com": "twitter",
        "instagram.com": "instagram",
        "facebook.com": "facebook",
        "bilibili.com": "bilibili",
        "twitch.tv": "twitch",
    }
    
    url_lower = url.lower()
    for domain, platform in platforms.items():
        if domain in url_lower:
            return platform
    
    return None
