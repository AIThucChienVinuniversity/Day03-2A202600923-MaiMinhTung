import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://moveek.com/phim/ba-tron/"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="vi-VN")

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        regions = page.evaluate("""
        () => Array.from(document.querySelectorAll("select.btn-select-region option")).map(o => ({
            value: o.value,
            text: o.innerText.trim(),
            selected: o.selected
        }))
        """)

        versions = page.evaluate("""
        () => Array.from(document.querySelectorAll("select.btn-select-version option")).map(o => ({
            value: o.value,
            text: o.innerText.trim(),
            selected: o.selected
        }))
        """)

        browser.close()

    result = {
        "url": URL,
        "regions": regions,
        "versions": versions
    }

    Path("region_version.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()