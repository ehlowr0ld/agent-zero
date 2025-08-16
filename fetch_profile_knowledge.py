#!/usr/bin/env python3
import asyncio
import os
from urllib.parse import urlparse
from dataclasses import replace as dc_replace

from agent import Agent
from initialize import initialize_agent
from python.helpers.document_query import DocumentQueryHelper
from python.helpers import files
from python.helpers.print_style import PrintStyle


PROFILES_TO_URLS: dict[str, list[str]] = {

    "default": [
        "https://www.miralishahidi.ir/resources/Kali%20Linux%20(102).pdf",
        "https://elhacker.info/manuales/Hacking%20y%20Seguridad%20informatica/Offensive%20Security/Mastering%20Kali%20Linux%20for%20Advanced%20Penetration%20Testing%20-%20Beggs,%20Robert.pdf",
        "https://dl.hellodigi.ir/dl.hellodigi.ir/dl/book/Kali%20Linux%20Cookbook%20(Second%20Edition).pdf",
        "https://pontus.digipen.edu/~mmead/www/public/linux/linuxmint18-UserManual.pdf",

    ]
}


def infer_markdown_filename(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    base = os.path.basename(path) if path else "index"
    if not base:
        base = parsed.netloc.replace(".", "_")
    # swap extension to .md
    if "." in base:
        base_no_ext = base.rsplit(".", 1)[0]
    else:
        # if path has no file, slugify full path
        slug = (parsed.netloc + path).replace("/", "_") or "document"
        base_no_ext = slug
    safe = files.safe_file_name(base_no_ext)
    return f"{safe}.md"


# Load base application configuration once
_BASE_CONFIG = initialize_agent()


def build_agent(profile: str) -> Agent:
    # Use the application configuration and override only the profile for this run
    cfg = dc_replace(_BASE_CONFIG, profile=profile)
    return Agent(0, cfg)


async def fetch_and_save_for_profile(profile: str, urls: list[str]):
    agent = build_agent(profile)
    helper = DocumentQueryHelper(agent)
    out_dir = files.get_abs_path("agents", profile, "knowledge", "main")
    os.makedirs(out_dir, exist_ok=True)

    sem = asyncio.Semaphore(8)  # 8 concurrent fetches per profile

    async def fetch_one(url: str):
        async with sem:
            try:
                PrintStyle.standard(f"Fetching: {url}")
                content_md = await helper.document_get_content(url, add_to_db=False)
                if not content_md or not content_md.strip():
                    PrintStyle.standard("Empty content, skipping")
                    return
                fname = infer_markdown_filename(url)
                rel_path = os.path.join("agents", profile, "knowledge", "main", fname)
                header = f"<!-- Source: {url} -->\n\n"
                files.write_file(rel_path, header + content_md)
                PrintStyle.standard(f"Saved: {rel_path}")
            except Exception as e:
                PrintStyle.error(f"Failed for {url}: {e}")

    await asyncio.gather(*(fetch_one(u) for u in urls))


async def main():
    await asyncio.gather(
        *(fetch_and_save_for_profile(profile, urls) for profile, urls in PROFILES_TO_URLS.items())
    )
    PrintStyle.standard("\nAll profiles processed.")


if __name__ == "__main__":
    asyncio.run(main())
