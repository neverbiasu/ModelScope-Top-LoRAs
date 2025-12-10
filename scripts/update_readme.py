#!/usr/bin/env python3
"""
Auto-generate daily stats image and update README with Top 3 models.

This script:
1. Generates a statistics visualization image
2. Extracts top 3 models (with covers) from cache
3. Updates README.md with the image and model cards
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from top_loras.cache import load_cache
from top_loras.fetcher import DEFAULT_CACHE_FILE


def load_top_models(cache_file: str = DEFAULT_CACHE_FILE, limit: int = 3) -> List[Dict[str, Any]]:
    """Load top N models from cache."""
    results = load_cache(cache_file, ttl=60 * 60 * 24 * 365)
    if not results or not isinstance(results, list):
        return []
    
    # Filter models with covers
    models_with_covers = [
        m for m in results
        if isinstance(m, dict) and (m.get('cover_local') or m.get('cover_url'))
    ]
    
    return models_with_covers[:limit]


def generate_stats_image(models: List[Dict[str, Any]], output_path: Path) -> bool:
    """Generate a statistics visualization image.
    
    Returns True if successful, False otherwise.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Warning: PIL not installed. Skipping image generation.")
        return False
    
    if not models:
        return False
    
    # Image dimensions
    width, height = 800, 200
    bg_color = (17, 19, 34)  # Dark background
    text_color = (255, 255, 255)
    accent_color = (147, 197, 253)  # Light blue
    
    # Create image
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default if not available
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 32)
        text_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 20)
        small_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Title
    title = "Top-LoRAs Daily Stats"
    draw.text((40, 30), title, fill=text_color, font=title_font)
    
    # Date
    date_str = datetime.now().strftime("%Y-%m-%d")
    draw.text((40, 75), f"Updated: {date_str}", fill=accent_color, font=small_font)
    
    # Stats
    total_models = len(models)
    total_downloads = sum(m.get('downloads', 0) for m in models if isinstance(m, dict))
    total_likes = sum(m.get('likes', 0) for m in models if isinstance(m, dict))
    
    stats_y = 110
    stats = [
        f"Total Models: {total_models}",
        f"Total Downloads: {total_downloads:,}",
        f"Total Likes: {total_likes:,}"
    ]
    
    for i, stat in enumerate(stats):
        x = 40 + i * 250
        draw.text((x, stats_y), stat, fill=text_color, font=text_font)
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    print(f"✓ Generated stats image: {output_path}")
    return True


def format_model_card(model: Dict[str, Any], rank: int) -> str:
    """Format a model as a markdown card."""
    # Prefer English title for README readability, fall back to CN / generic
    title = model.get('title_en') or model.get('title_cn') or model.get('title') or model.get('id') or 'Unknown'
    model_id = model.get('id', 'unknown')
    author = model.get('author', 'Unknown')
    downloads = model.get('downloads', 0)
    likes = model.get('likes', 0)
    
    # Use cover_url preferably, fallback to cover_local
    cover = model.get('cover_url') or model.get('cover_local', '')
    
    # Description (truncated)
    desc = model.get('description', 'No description available.')
    if len(desc) > 150:
        desc = desc[:147] + '...'
    
    url = model.get('modelscope_url', f'https://modelscope.cn/models/{model_id}')
    
    card = f"""
### #{rank} {title}

<div align="center">
  <img src="{cover}" alt="{title}" width="400"/>
</div>

**Model ID:** `{model_id}`  
**Author:** {author}  
**Downloads:** {downloads:,} | **Likes:** {likes:,}

{desc}

[🔗 View on ModelScope]({url})

---
"""
    return card


def build_top_models_table(models: List[Dict[str, Any]], limit: int = 3) -> str:
    """Build a markdown table for the top models (English-first)."""
    headers = ["#", "Cover", "Model", "Author", "Downloads", "Likes"]
    rows: List[List[str]] = []

    for i, model in enumerate(models[:limit], 1):
        title = model.get('title_en') or model.get('title_cn') or model.get('title') or model.get('id') or 'Unknown'
        model_id = model.get('id', 'unknown')
        author = model.get('author', 'Unknown')
        downloads = f"{model.get('downloads', 0):,}"
        likes = f"{model.get('likes', 0):,}"

        # Prefer remote cover
        cover = model.get('cover_url') or model.get('cover_local') or ''
        cover_md = f"![{title}]({cover})" if cover else ""

        url = model.get('modelscope_url') or f"https://modelscope.cn/models/{model_id}"
        link_md = f"[{title}]({url})"

        rows.append([
            str(i),
            cover_md,
            link_md,
            author,
            downloads,
            likes,
        ])

    # Build markdown table
    table_lines = []
    table_lines.append("| " + " | ".join(headers) + " |")
    table_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        table_lines.append("| " + " | ".join(row) + " |")
    return "\n".join(table_lines)


def update_readme(models: List[Dict[str, Any]], stats_image_path: str = "docs/daily_stats.png") -> bool:
    """Update README.md with stats image and top models."""
    readme_path = project_root / "README.md"
    
    if not readme_path.exists():
        print(f"Error: README.md not found at {readme_path}")
        return False
    
    content = readme_path.read_text(encoding='utf-8')
    
    # Generate new sections
    stats_section = f"""
## 📊 Daily Statistics

![Daily Stats]({stats_image_path})

*Statistics updated automatically every day*
"""
    
    top_models_section = "## 🏆 Top 3 Models\n\n" + build_top_models_table(models, limit=3) + "\n"
    
    # Find insertion points
    # We'll look for markers or insert after the project summary
    
    # Strategy: Insert after "## Project Summary" or at the end of initial content
    lines = content.split('\n')
    
    # Remove old auto-generated sections if they exist
    start_marker = "## 📊 Daily Statistics"
    end_marker = "## Quick start"  # or another known section
    
    # Find and remove old content between markers
    new_lines = []
    skip = False
    for line in lines:
        if line.startswith(start_marker):
            skip = True
        elif skip and (line.startswith("## ") and not line.startswith("## 🏆")):
            skip = False
        
        if not skip:
            new_lines.append(line)
    
    # Find insertion point (after "## Project Summary" section)
    insert_idx = None
    for i, line in enumerate(new_lines):
        if line.startswith("## Project Summary"):
            # Find the end of this section (next ## heading)
            for j in range(i + 1, len(new_lines)):
                if new_lines[j].startswith("## "):
                    insert_idx = j
                    break
            break
    
    # If not found, insert after front matter / header
    if insert_idx is None:
        for i, line in enumerate(new_lines):
            if line.startswith("# Top-LoRAs"):
                insert_idx = i + 1
                break
    
    if insert_idx is None:
        insert_idx = min(20, len(new_lines))  # Fallback
    
    # Insert new sections
    new_content_parts = (
        new_lines[:insert_idx] +
        [''] +
        stats_section.split('\n') +
        [''] +
        top_models_section.split('\n') +
        [''] +
        new_lines[insert_idx:]
    )
    
    new_content = '\n'.join(new_content_parts)
    
    # Write back
    readme_path.write_text(new_content, encoding='utf-8')
    print(f"✓ Updated README.md with top {len(models)} models")
    return True


def main():
    """Main execution."""
    print("🚀 Updating README with daily stats and top models...")
    
    # Load cache for text-to-image task (most common)
    cache_file = "cache/top_loras_text-to-image-synthesis.json"
    cache_path = project_root / cache_file
    
    if not cache_path.exists():
        # Try default cache
        cache_file = DEFAULT_CACHE_FILE
        cache_path = project_root / cache_file
    
    if not cache_path.exists():
        print(f"❌ No cache found. Please run `python -m top_loras` first.")
        return 1
    
    # Load top models
    models = load_top_models(str(cache_path), limit=20)  # Load more for stats
    if not models:
        print("❌ No models found in cache.")
        return 1
    
    print(f"✓ Loaded {len(models)} models from cache")
    
    # Generate stats image
    stats_img_path = project_root / "docs" / "daily_stats.png"
    generate_stats_image(models, stats_img_path)
    
    # Update README
    top_3 = models[:3]
    success = update_readme(top_3, "docs/daily_stats.png")
    
    if success:
        print("✅ README update complete!")
        return 0
    else:
        print("⚠️ README update had issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
