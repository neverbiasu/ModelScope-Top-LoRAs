import argparse
from pathlib import Path
from .download import sanitize_filename
from . import fetcher as fetch_module


def run_cli(argv=None):
    parser = argparse.ArgumentParser(description='Fetch Top LoRA models from ModelScope')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--tag', type=str, default='lora')
    parser.add_argument('--task', type=str, default=None, help='Task filter, e.g. text-to-image-synthesis or image-to-video')
    parser.add_argument('--all-tasks', action='store_true', help='Run fetch for all preset tasks (text-to-image, image-to-video)')
    parser.add_argument('--cache-file', type=str, default=fetch_module.DEFAULT_CACHE_FILE)
    parser.add_argument('--images-dir', type=str, default=fetch_module.DEFAULT_IMAGES_DIR)
    # per-task cache behavior: by default enabled when --task is provided and no explicit cache-file/images-dir
    parser.add_argument('--no-per-task-cache', action='store_false', dest='per_task_cache',
                        help='Do not auto-select per-task cache file and images dir (use global paths)')
    parser.add_argument('--page-size', type=int, default=None, help='Override per-request page size')
    parser.add_argument('--max-pages', type=int, default=5, help='Maximum pages to fetch when aggregating results')
    parser.add_argument('--ttl', type=int, default=300, help='Cache TTL in seconds')
    parser.add_argument('--force-refresh', action='store_true')
    # images are downloaded by default and are required for cover_local to be populated
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args(argv)

    # Default behavior: if neither --task nor --all-tasks is provided,
    # run for all preset tasks so that caches and images are written
    # per task (e.g., cache/top_loras_text-to-image-synthesis.json and
    # cache/images/text-to-image-synthesis/).
    if not args.all_tasks and not args.task:
        args.all_tasks = True

    if args.all_tasks:
        for key, task_val in fetch_module.TASK_PRESETS.items():
            # Use the actual task name (task_val) for cache/images naming so
            # files reflect the real ModelScope task (e.g. text-to-image-synthesis)
            safe = sanitize_filename(task_val)
            cache_file = Path(args.cache_file).with_name(f"top_loras_{safe}.json")
            images_dir = Path(args.images_dir) / safe
            print(f"Fetching task={task_val} -> cache={cache_file} images={images_dir}")
            fetch_module.fetch_top_loras(limit=args.limit, tag=args.tag, debug=args.debug,
                                         cache_file=str(cache_file), images_dir=str(images_dir),
                                         ttl=args.ttl, force_refresh=args.force_refresh,
                                         download_images=True, task=task_val,
                                         page_size=args.page_size, max_pages=args.max_pages,
                                         per_task_cache=args.per_task_cache)
        return

    top_loras = fetch_module.fetch_top_loras(limit=args.limit, tag=args.tag, debug=args.debug,
                                             cache_file=args.cache_file, images_dir=args.images_dir,
                                             ttl=args.ttl, force_refresh=args.force_refresh,
                                             download_images=True, task=args.task,
                                             page_size=args.page_size, max_pages=args.max_pages,
                                             per_task_cache=args.per_task_cache)

    if not top_loras:
        print('No LoRA models found (0 results). If you expected results, try increasing PageSize or check your token/permissions.')
        return

    print(f"\nTop {len(top_loras)} LoRA Models:")
    print("-" * 100)

    for i, model in enumerate(top_loras, 1):
        title_cn = model.get('title_cn')
        title_en = model.get('title_en')
        title = title_cn if title_cn and title_cn != title_en else title_en

        print(f"{i:2d}. {title}")
        if title_cn and title_cn != title_en:
            print(f"    EN: {title_en}")

        print(f"    ID: {model.get('id')}")
        print(f"    Author: {model.get('author')}")
        print(f"    Downloads: {model.get('downloads')}")
        print(f"    Likes: {model.get('likes')}")
        print(f"    License: {model.get('license')}")
        print(f"    Updated: {model.get('updated_at')}")
        print(f"    URL: {model.get('modelscope_url')}")
        print(f"    Cover Local: {model.get('cover_local')}")
        print()


def main():
    run_cli()
