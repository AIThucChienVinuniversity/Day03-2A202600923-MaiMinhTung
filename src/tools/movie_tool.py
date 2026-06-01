import requests
import re
from typing import Dict, Any, List


def _clean_html(raw_html: str) -> str:
    """
    Remove simple HTML tags from TVmaze summaries.
    """
    if not raw_html:
        return "No summary available."

    text = re.sub(r"<.*?>", "", raw_html)
    return text.strip()


def search_movie_web(query: str) -> Dict[str, Any]:
    """
    Search movies/TV shows from the web using TVmaze API.

    Input:
        query: movie or TV show name, e.g. "Breaking Bad", "The Last of Us"

    Output:
        A dictionary containing search results.
    """
    url = "https://api.tvmaze.com/search/shows"

    try:
        response = requests.get(
            url,
            params={"q": query},
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        if not data:
            return {
                "found": False,
                "query": query,
                "message": f"No movie or show found for '{query}'."
            }

        results: List[Dict[str, Any]] = []

        for item in data[:5]:
            show = item.get("show", {})

            results.append({
                "name": show.get("name"),
                "type": show.get("type"),
                "language": show.get("language"),
                "genres": show.get("genres", []),
                "status": show.get("status"),
                "premiered": show.get("premiered"),
                "ended": show.get("ended"),
                "rating": show.get("rating", {}).get("average"),
                "official_site": show.get("officialSite"),
                "summary": _clean_html(show.get("summary")),
                "url": show.get("url")
            })

        return {
            "found": True,
            "query": query,
            "results": results
        }

    except requests.exceptions.Timeout:
        return {
            "found": False,
            "query": query,
            "error": "Request timed out while searching the web."
        }

    except requests.exceptions.RequestException as e:
        return {
            "found": False,
            "query": query,
            "error": f"Web request failed: {str(e)}"
        }

    except Exception as e:
        return {
            "found": False,
            "query": query,
            "error": f"Unexpected error: {str(e)}"
        }


def recommend_movie_by_requirement(requirement: str) -> Dict[str, Any]:
    """
    Search for movies/TV shows based on a user's requirement.

    Example:
        "I want a dark crime series like Breaking Bad"
        "Find me a romantic Korean drama"
        "I want a sci-fi show about space"

    This tool maps the requirement to a search query and calls TVmaze.
    """
    requirement_lower = requirement.lower()

    keyword_map = {
        "crime": "crime",
        "dark": "dark",
        "mafia": "mafia",
        "romantic": "romance",
        "romance": "romance",
        "korean": "korean drama",
        "drama": "drama",
        "sci-fi": "science fiction",
        "science fiction": "science fiction",
        "space": "space",
        "zombie": "zombie",
        "horror": "horror",
        "comedy": "comedy",
        "sitcom": "sitcom",
        "superhero": "superhero",
        "detective": "detective",
        "anime": "anime"
    }

    search_query = requirement

    for key, value in keyword_map.items():
        if key in requirement_lower:
            search_query = value
            break

    return search_movie_web(search_query)


search_movie_tool = [
    {
        "name": "search_movie_web",
        "description": (
            "DÙNG KHI: Người dùng muốn tìm thông tin, tóm tắt, đánh giá của các bộ phim bộ, phim truyền hình, "
            "phim trực tuyến (Netflix, HBO, phim lậu...) HOẶC các bộ phim CŨ ĐÃ HẾT CHIẾU RẠP TỪ LÂU. "
            "TUYỆT ĐỐI KHÔNG dùng công cụ này nếu người dùng có ý định xem phim ngoài rạp hiện tại hoặc đặt vé. "
            "Input: Tên phim dạng string. Ví dụ: search_movie_web(\"Breaking Bad\")"
        ),
        "func": search_movie_web
    },
    {
        "name": "recommend_movie_by_requirement",
        "description": (
            "Find movie or TV show recommendations based on user requirements such as genre, mood, country, or topic. "
            "Input: requirement as a string. "
            "Use this when the user asks for recommendations, not an exact title. "
            "Example Action: recommend_movie_by_requirement(\"I want a dark crime series\")"
        ),
        "func": recommend_movie_by_requirement
    }
]