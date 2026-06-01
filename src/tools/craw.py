import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://moveek.com/phim/ba-tron/"

def extract(page):
    return page.evaluate("""
    () => Array.from(document.querySelectorAll("a.btn-showtime")).map(a => ({
        time: a.querySelector(".time")?.innerText.trim() || "",
        href: a.href,
        cinema: a.dataset.cinema || "",
        cineplex: a.dataset.cineplex || "",
        disabled: a.classList.contains("disabled")
    })).filter(x => x.time)
    """)

def main():
    all_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="vi-VN")

        # Chặn tài nguyên nặng để tăng tốc độ cào
        page.route("**/*", lambda route: (
            route.abort()
            if route.request.resource_type in ["image", "stylesheet", "font", "media"]
            else route.continue_()
        ))

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("#showtimes", timeout=20000)

        # Chọn Hà Nội (value="9")
        page.select_option("select.btn-select-region", value="9")
        page.wait_for_timeout(1500)

        # Chọn 2D (value="2d")
        page.select_option("select.btn-select-version", value="2d")
        page.wait_for_timeout(1000)

        cineplex_count = page.locator("a.btn-select-cineplex").count()

        for i in range(cineplex_count):
            cineplex = page.locator("a.btn-select-cineplex").nth(i)

            try:
                cineplex.click(timeout=3000)
                page.wait_for_timeout(1000)
            except Exception:
                continue

            cineplex_key = cineplex.get_attribute("data-cineplex") or ""
            cinemas = page.locator(f".btn-select-cinema[data-cineplex='{cineplex_key}']")

            for j in range(cinemas.count()):
                cinema = cinemas.nth(j)

                try:
                    cinema.click(timeout=3000)
                    
                    # FIX 1: Chờ biểu tượng loading (spinner) biến mất thay vì sleep cứng
                    # Tránh việc cào trượt khi API của Moveek trả về chậm
                    page.wait_for_selector(".spinner-border", state="hidden", timeout=5000)
                    page.wait_for_timeout(300) # Đợi thêm 1 chút để DOM render nút bấm
                except Exception:
                    pass

                # Cào dữ liệu suất chiếu ngay sau khi đã đảm bảo load xong
                rows = extract(page)
                all_rows.extend(rows)

        browser.close()

    # FIX 2: Lọc trùng lặp bằng Key duy nhất (Kết hợp Rạp + Giờ chiếu + Link)
    # Tránh tình trạng các rạp dùng chung link ZaloPay bị đè dữ liệu của nhau
    unique = {}
    for r in all_rows:
        key = f'{r["cinema"]}-{r["time"]}-{r["href"]}'
        unique[key] = r

    result = list(unique.values())

    # Lưu kết quả ra file JSON
    Path("showtimes_all.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # In kết quả ra console để kiểm tra
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n[+] Tổng cộng tìm thấy: {len(result)} suất chiếu.")

if __name__ == "__main__":
    main()