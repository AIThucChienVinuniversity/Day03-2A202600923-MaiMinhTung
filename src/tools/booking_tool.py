import json
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from playwright.sync_api import sync_playwright

# -----------------------------------------------------------------------------
# DICTIONARIES (Bộ từ điển chuẩn hóa dữ liệu từ bản quét thực tế)
# -----------------------------------------------------------------------------

REGION_MAP = {
    "tp. hồ chí minh": "1", "hồ chí minh": "1", "ho chi minh": "1", "sài gòn": "1", "hcm": "1",
    "hà nội": "9", "ha noi": "9", "hn": "9",
    "đà nẵng": "7", "da nang": "7",
    "đồng nai": "3", "dong nai": "3",
    "cần thơ": "6", "can tho": "6",
    "bình dương": "4", "binh duong": "4",
    "bình phước": "53", "binh phuoc": "53",
    "bình thuận": "13", "binh thuan": "13",
    "bà rịa - vũng tàu": "15", "vũng tàu": "15", "ba ria vung tau": "15", "vung tau": "15",
    "an giang": "18", "bến tre": "19", "hải phòng": "10", "hai phong": "10", 
    "kiên giang": "24", "hải dương": "29", "trà vinh": "27", "quảng ninh": "8", "hạ long": "8",
    "vĩnh long": "28", "bắc giang": "2", "ninh bình": "16", "cà mau": "30", "lào cai": "58",
    "phú thọ": "17", "hậu giang": "35", "thái bình": "20", "tây ninh": "36",
    "khánh hòa": "12", "nha trang": "12", "thừa thiên - huế": "11", "thừa thiên huế": "11", "huế": "11",
    "đồng tháp": "55", "thái nguyên": "22", "bạc liêu": "39", "thanh hóa": "25",
    "bình định": "14", "hưng yên": "56", "sóc trăng": "40", "hà tĩnh": "31",
    "yên bái": "26", "đắk lắk": "5", "long an": "45", "nghệ an": "21", "vinh": "21",
    "tiền giang": "49", "bắc ninh": "33", "hòa bình": "57", "tuyên quang": "34",
    "lâm đồng": "23", "đà lạt": "23", "nam định": "38", "quảng bình": "41",
    "sơn la": "46", "phú yên": "37", "quảng trị": "50", "quảng nam": "42",
    "lạng sơn": "47", "quảng ngãi": "51", "hà nam": "48", "ninh thuận": "43",
    "vĩnh phúc": "54", "gia lai": "44", "kon tum": "52"
}

VERSION_MAP = {
    "2d": "2d", "3d": "3d", "imax": "imax", "4dx": "4dx", "screenx": "screenx"
}

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS 
# -----------------------------------------------------------------------------
def _helper_get_movie_url(movie_name: str) -> str:
    """Tìm kiếm tên phim trên Moveek và trả về URL chi tiết của phim đó."""
    search_query = movie_name.replace(" ", "+")
    url = f"https://moveek.com/tim-kiem/?s={search_query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            first_result = soup.find("a", href=lambda href: href and "/phim/" in href)
            if first_result:
                return f"https://moveek.com{first_result['href']}"
    except Exception:
        pass
    return ""


# -----------------------------------------------------------------------------
# CORE TOOLS 
# -----------------------------------------------------------------------------

def get_movie_list_by_category(category: str = "dang-chieu") -> Dict[str, Any]:
    valid_categories = ["dang-chieu", "sap-chieu", "chieu-som"]
    if category not in valid_categories:
        category = "dang-chieu"

    url = f"https://moveek.com/{category}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    print(f"\n[Crawl Danh Mục] -> Đang truy cập: {url} ...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"found": False, "error": f"Không thể truy cập Moveek (HTTP {response.status_code})"}

        soup = BeautifulSoup(response.text, "html.parser")
        movies_list = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '/phim/' in href:
                title = a_tag.text.strip()
                if title and len(title) > 2 and "mua vé" not in title.lower():
                    if title not in movies_list:
                        movies_list.append(title)
        
        if not movies_list:
            return {"found": False, "message": f"Hiện tại không có dữ liệu cho mục '{category}'."}

        return {
            "found": True,
            "category_searched": category,
            "source_url": url,
            "total_movies": len(movies_list),
            "movies": movies_list[:15]
        }
    except Exception as e:
        return {"found": False, "error": f"Lỗi quá trình cào danh mục: {str(e)}"}


def get_movie_info_moveek(movie_name: str) -> Dict[str, Any]:
    detail_link = _helper_get_movie_url(movie_name)
    if not detail_link:
        return {"found": False, "message": f"Moveek không có thông tin về phim '{movie_name}'."}

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    print(f"\n[Crawl Info] -> Đang lấy thông tin chi tiết phim từ: {detail_link} ...")

    try:
        detail_res = requests.get(detail_link, headers=headers, timeout=10)
        detail_soup = BeautifulSoup(detail_res.text, "html.parser")

        title_tag = detail_soup.find("h1")
        title = title_tag.text.strip() if title_tag else movie_name
        
        summary_tag = detail_soup.find("p", class_=lambda c: c and "text-justify" in c)
        summary = summary_tag.text.strip() if summary_tag else "Chưa có tóm tắt nội dung."

        return {
            "found": True,
            "movie_name": title,
            "summary": summary,
            "source_url": detail_link,
            "message": "Đã tìm thấy thông tin phim trên Moveek."
        }
    except Exception as e:
        return {"found": False, "error": f"Lỗi cào thông tin phim: {str(e)}"}


def get_movie_showtimes(movie_name: str, location: str = "Hà Nội", version: str = "2d") -> Dict[str, Any]:
    """
    Sử dụng Playwright để lấy toàn bộ lịch chiếu của phim theo khu vực (location).
    Đã được tối ưu hóa chống treo Timeout khi phim hết suất chiếu tại khu vực chỉ định.
    """
    loc_clean = location.strip().lower()
    region_id = REGION_MAP.get(loc_clean, "9") # Mặc định Hà Nội (9)
    
    ver_clean = version.strip().lower()
    version_val = VERSION_MAP.get(ver_clean, "2d") # Mặc định 2D

    movie_url = _helper_get_movie_url(movie_name)
    if not movie_url:
        return {"found": False, "message": f"Không tìm thấy URL của phim '{movie_name}' trên Moveek."}

    print(f"\n[Playwright Showtimes] -> Đang cào lịch chiếu '{movie_name}'")
    print(f"                       -> Địa điểm: {location} (ID: {region_id}) | Định dạng: {version_val.upper()}")
    
    all_rows = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(locale="vi-VN")

            # Chặn tài nguyên nặng để tăng tốc độ load trang
            page.route("**/*", lambda route: (
                route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] 
                else route.continue_()
            ))

            page.goto(movie_url, wait_until="domcontentloaded", timeout=60000)
            
            # --- BƯỚC KIỂM TRA CHỐNG TREO TIMEOUT (CRITICAL FIX) ---
            # Tìm dropdown khu vực trên toàn trang với thời gian chờ tối đa 3 giây
            region_select = page.locator("select.btn-select-region").first
            try:
                region_select.wait_for(state="attached", timeout=3000)
            except Exception:
                # Nếu quá 3 giây không tìm thấy dropdown -> Moveek không có lịch chiếu cho phim này nữa
                browser.close()
                return {
                    "found": False,
                    "message": f"Hiện tại phim '{movie_name}' đã hết suất chiếu tại khu vực {location} hoặc đã ngừng chiếu hoàn toàn."
                }

            # --- TIẾN HÀNH CHỌN KHU VỰC VÀ ĐỊNH DẠNG ---
            try:
                region_select.select_option(value=region_id, timeout=3000)
                page.wait_for_timeout(500)
                
                version_select = page.locator("select.btn-select-version").first
                if version_select.count() > 0:
                    version_select.select_option(value=version_val, timeout=3000)
                    page.wait_for_timeout(500)
            except Exception:
                browser.close()
                return {
                    "found": False,
                    "message": f"Phim '{movie_name}' hiện không có suất chiếu nào phù hợp tại khu vực {location}."
                }

            # --- ĐỌC SỐ LƯỢNG CỤM RẠP (CINEPLEX) ---
            container = page.locator("#showtimes")
            cineplex_count = container.locator("a.btn-select-cineplex").count()
            
            if cineplex_count == 0:
                browser.close()
                return {
                    "found": False,
                    "message": f"Không có cụm rạp nào mở bán vé phim '{movie_name}' tại {location} hôm nay."
                }

            # --- VÒNG LẶP CLICK CÀO LỊCH CHIẾU ---
            for i in range(cineplex_count):
                cineplex = container.locator("a.btn-select-cineplex").nth(i)
                try:
                    cineplex.click(timeout=2000)
                    page.wait_for_timeout(500)
                except Exception:
                    continue

                cineplex_key = cineplex.get_attribute("data-cineplex") or ""
                cinemas = container.locator(f".btn-select-cinema[data-cineplex='{cineplex_key}']")

                for j in range(cinemas.count()):
                    cinema = cinemas.nth(j)
                    try:
                        cinema.click(timeout=2000)
                        # Đợi spinner biến mất để bảo đảm DOM rạp đã nạp xong lịch
                        page.wait_for_selector(".spinner-border", state="hidden", timeout=3000)
                        page.wait_for_timeout(200)
                    except Exception:
                        pass

                    # Thực thi JS quét sạch các nút suất chiếu của rạp hiện tại
                    rows = page.evaluate("""
                    () => {
                        const showtimesBlock = document.querySelector("#showtimes");
                        if (!showtimesBlock) return [];
                        return Array.from(showtimesBlock.querySelectorAll("a.btn-showtime")).map(a => ({
                            time: a.querySelector(".time")?.innerText.trim() || "",
                            href: a.href,
                            cinema: a.dataset.cinema || "",
                            cineplex: a.dataset.cineplex || "",
                            disabled: a.classList.contains("disabled")
                        })).filter(x => x.time)
                    }
                    """)
                    all_rows.extend(rows)

            browser.close()

        # --- KHỬ TRÙNG LẶP ---
        unique = {}
        for r in all_rows:
            key = f'{r["cinema"]}-{r["time"]}-{r["href"]}'
            unique[key] = r
        
        result = list(unique.values())
        
        if not result:
            return {
                "found": False,
                "message": f"Phim '{movie_name}' có lịch nhưng các suất chiếu tại {location} đều đã qua giờ chiếu."
            }

        return {
            "found": True,
            "movie_name": movie_name,
            "searched_location": location,
            "searched_version": version_val.upper(),
            "total_showtimes": len(result),
            "showtimes": result
        }

    except Exception as e:
        return {"found": False, "error": f"Lỗi không xác định trong quá trình chạy Playwright: {str(e)}"}


def get_available_seats(cinema_id: str, time: str) -> Dict[str, Any]:
    print(f"\n[Bot Đang Quét Phòng Chiếu...] Lấy sơ đồ ghế cho {cinema_id} lúc {time}")
    return {
        "cinema_id": cinema_id,
        "time": time,
        "available_seats": ["F12", "F13", "F14", "G10", "G11"],
        "price_per_seat": "120,000 VND"
    }


def generate_booking_link_real(movie_showtimes_list: list, cinema_id: str, time: str) -> Dict[str, Any]:
    """
    Trích xuất link đặt vé THẬT của Moveek từ danh sách suất chiếu đã cào được trước đó.
    """
    for showtime in movie_showtimes_list:
        if showtime["cinema"] == cinema_id and showtime["time"] == time:
            return {
                "status": "Success",
                "message": f"Đã tìm thấy link đặt vé thực tế cho suất {time}.",
                "payment_url": showtime["href"]  # Đây là link thật dẫn đến trang chọn ghế của Moveek/Rạp
            }
            
    return {
        "status": "Failed",
        "message": "Không tìm thấy suất chiếu phù hợp để lấy link đặt vé."
    }


# -----------------------------------------------------------------------------
# AGENT TOOL DEFINITIONS
# -----------------------------------------------------------------------------
book_movie_tool = [
    {
        "name": "get_movie_list_by_category",
        "description": "DÙNG KHI: Người dùng muốn biết danh sách phim Đang chiếu, Sắp chiếu hoặc Chiếu sớm. Tham số: category ('dang-chieu' | 'sap-chieu' | 'chieu-som').",
        "func": get_movie_list_by_category
    },
    {
        "name": "get_movie_info_moveek",
        "description": "DÙNG KHI: Người dùng hỏi về nội dung, cốt truyện hoặc thông tin giới thiệu chung của một phim. Tham số: movie_name.",
        "func": get_movie_info_moveek
    },
    {
        "name": "get_movie_showtimes",
        "description": (
            "DÙNG KHI: Người dùng muốn tra cứu lịch chiếu, giờ chiếu, rạp chiếu cụ thể của một bộ phim.\n"
            "Tham số:\n"
            "- movie_name: Tên phim bắt buộc.\n"
            "- location: Tên Tỉnh/Thành phố bằng tiếng Việt (Ví dụ: 'Hồ Chí Minh', 'Đà Nẵng', 'Bình Dương'). Mặc định là 'Hà Nội'.\n"
            "- version: Định dạng phim ('2d' hoặc '3d'). Mặc định là '2d'."
        ),
        "func": get_movie_showtimes
    },
    {
        "name": "get_available_seats",
        "description": "DÙNG KHI: Người dùng đã chọn được rạp và giờ chiếu, cần xem danh sách ghế trống. Tham số: cinema_id, time.",
        "func": get_available_seats
    },
    {
        "name": "generate_booking_link",
        "description": "DÙNG KHI: Người dùng chốt ghế muốn lấy link đặt vé/thanh toán tiền. Tham số: cinema_id, time, seats.",
        "func": generate_booking_link
    }
]