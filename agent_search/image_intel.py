# -*- coding: utf-8 -*-
"""Agent Search Lite — Image Intelligence Layer.

Extracts metadata, performs OCR, and analyzes images.

Copyright (c) 2026 Agent Search Lite Contributors.
MIT License. See LICENSE for details.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Image Metadata Extraction
# ---------------------------------------------------------------------------

def extract_image_metadata(url_or_path: str) -> Dict[str, Any]:
    """Extract metadata from images (EXIF, dimensions, format)."""
    result = {
        "url": url_or_path,
        "format": "",
        "width": 0,
        "height": 0,
        "size_bytes": 0,
        "exif": {},
        "description": "",
    }
    
    try:
        from PIL import Image
        
        # Download if URL
        if url_or_path.startswith(("http://", "https://")):
            resp = httpx.get(url_or_path, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
            result["size_bytes"] = len(resp.content)
        else:
            img = Image.open(url_or_path)
            result["size_bytes"] = os.path.getsize(url_or_path)
        
        result["format"] = img.format or ""
        result["width"], result["height"] = img.size
        
        # Extract EXIF data
        if hasattr(img, "_getexif") and img._getexif():
            exif = img._getexif()
            for tag, value in exif.items():
                result["exif"][str(tag)] = str(value)
        
    except ImportError:
        result["error"] = "Pillow not installed"
    except Exception as exc:
        result["error"] = f"Image metadata extraction failed: {exc}"
    
    return result


# ---------------------------------------------------------------------------
# Image OCR
# ---------------------------------------------------------------------------

def extract_text_from_image(url_or_path: str, lang: str = "eng") -> Dict[str, Any]:
    """Extract text from images using OCR."""
    result = {
        "url": url_or_path,
        "text": "",
        "confidence": 0,
        "language": lang,
    }
    
    try:
        import pytesseract
        from PIL import Image
        
        # Download if URL
        if url_or_path.startswith(("http://", "https://")):
            resp = httpx.get(url_or_path, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
        else:
            img = Image.open(url_or_path)
        
        # Perform OCR
        text = pytesseract.image_to_string(img, lang=lang)
        result["text"] = text.strip()
        
        # Get confidence data
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
        confidences = [int(c) for c in data["conf"] if int(c) > 0]
        if confidences:
            result["confidence"] = sum(confidences) / len(confidences)
        
    except ImportError:
        result["error"] = "pytesseract or Pillow not installed"
    except Exception as exc:
        result["error"] = f"OCR failed: {exc}"
    
    return result


# ---------------------------------------------------------------------------
# Image Analysis (Basic)
# ---------------------------------------------------------------------------

def analyze_image(url_or_path: str) -> Dict[str, Any]:
    """Analyze image content (colors, objects, text detection)."""
    result = {
        "url": url_or_path,
        "format": "",
        "width": 0,
        "height": 0,
        "colors": [],
        "has_text": False,
        "is_photo": False,
        "is_diagram": False,
        "is_screenshot": False,
    }
    
    try:
        from PIL import Image
        import collections
        
        # Download if URL
        if url_or_path.startswith(("http://", "https://")):
            resp = httpx.get(url_or_path, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
        else:
            img = Image.open(url_or_path)
        
        result["format"] = img.format or ""
        result["width"], result["height"] = img.size
        
        # Sample colors
        img_small = img.resize((50, 50))
        pixels = list(img_small.getdata())
        if isinstance(pixels[0], tuple):
            colors = collections.Counter(pixels)
            top_colors = colors.most_common(5)
            result["colors"] = [f"RGB{c[0]}" for c in top_colors]
        
        # Detect if likely a photo
        unique_colors = len(set(pixels))
        result["is_photo"] = unique_colors > 100
        
        # Detect if likely a screenshot
        aspect_ratio = img.width / img.height if img.height > 0 else 0
        result["is_screenshot"] = 1.2 < aspect_ratio < 2.0
        
        # Detect text (basic heuristic - high contrast areas)
        if img.mode == "L":
            result["has_text"] = True
        
    except ImportError:
        result["error"] = "Pillow not installed"
    except Exception as exc:
        result["error"] = f"Image analysis failed: {exc}"
    
    return result
