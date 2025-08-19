#!/usr/bin/env python3
# MCP SSE server for Aria / Claude / MCP Inspector

import os
import json
from typing import List, Optional
import random

import httpx
from mcp.server.fastmcp import FastMCP

# Create server
mcp = FastMCP(
    name="Curated MCP Server",
    instructions="Utilities: weather, jokes, NASA APOD, recipes, books, artists, TV shows, trivia, numbers facts, quotes, ISS, countries, sunrise/sunset."
)

# ---------- Resources (read-only data) ----------
@mcp.resource("weather://current")
async def current_weather() -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=40.7128&longitude=-74.0060&current_weather=true"
        )
        return json.dumps(r.json(), indent=2)

@mcp.resource("nasa://apod")
async def nasa_apod_resource() -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get("https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY")
        return json.dumps(r.json(), indent=2)

@mcp.resource("jokes://random")
async def joke_resource() -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get("https://official-joke-api.appspot.com/random_joke")
        return json.dumps(r.json(), indent=2)

# ---------- Tools (do things / computed) ----------

# Weather (Open-Meteo)
@mcp.tool()
async def get_weather(city: str = "New York") -> str:
    """Get current weather for a city (Open-Meteo + geocoding)."""
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            # Geocode
            gr = await client.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}")
            g = gr.json()
            if not g.get("results"):
                return f"❌ City '{city}' not found."
            lat = g["results"][0]["latitude"]
            lon = g["results"][0]["longitude"]
            country = g["results"][0].get("country", "")

            # Weather
            wr = await client.get(
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={lat}&longitude={lon}"
                "&current_weather=true&timezone=auto"
            )
            w = wr.json().get("current_weather", {})
            temp_c = w.get("temperature")
            temp_f = (temp_c * 9 / 5) + 32 if temp_c is not None else None
            return (
                f"🌤️ Weather in {city}, {country}\n"
                f"🌡️ {temp_c}°C ({temp_f:.1f}°F)\n"
                f"💨 Wind {w.get('windspeed','N/A')} km/h  🧭 {w.get('winddirection','N/A')}°\n"
                f"⏰ {w.get('time','N/A')}"
            )
        except Exception as e:
            return f"❌ Error: {e}"

# Jokes (Official Joke API + icanhazdadjoke)
@mcp.tool()
async def get_random_joke(type: str = "general") -> str:
    """Get a random joke. type: general | programming | dad"""
    t = (type or "general").lower()
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            if t == "programming":
                r = await client.get("https://official-joke-api.appspot.com/jokes/programming/random")
                jokes = r.json() or []
                joke = jokes[0] if jokes else {}
                return f"💻 {joke.get('setup','')} — {joke.get('punchline','')}".strip()
            if t == "dad":
                r = await client.get("https://icanhazdadjoke.com/", headers={"Accept": "application/json"})
                data = r.json() or {}
                default = "Why don't scientists trust atoms? Because they make up everything!"
                return f"👨‍🍼 {data.get('joke', default)}"
            r = await client.get("https://official-joke-api.appspot.com/random_joke")
            joke = r.json() or {}
            return f"😂 {joke.get('setup','')} — {joke.get('punchline','')}".strip()
        except Exception as e:
            return f"❌ Error: {e}"

# Random fact (Useless Facts)
@mcp.tool()
async def get_random_fact() -> str:
    """Get a random interesting fact (uselessfacts)."""
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get("https://uselessfacts.jsph.pl/random.json?language=en")
            return f"🤓 {r.json().get('text', 'Did you know? Octopuses have three hearts!')}"
        except Exception as e:
            return f"❌ Error: {e}"

# NASA APOD
@mcp.tool()
async def get_nasa_apod(date: Optional[str] = None) -> str:
    """Get NASA Astronomy Picture of the Day (optional YYYY-MM-DD)."""
    url = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"
    if date:
        url += f"&date={date}"
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            data = (await client.get(url)).json() or {}
            if "error" in data:
                return f"❌ NASA API Error: {data['error'].get('message','Unknown')}"
            desc = data.get("explanation", "No description")
            if len(desc) > 400:
                desc = desc[:400] + "..."
            return (
                f"🚀 NASA APOD - {data.get('date','Today')}\n"
                f"✨ {data.get('title','')}\n\n"
                f"📝 {desc}\n"
                f"🔗 {data.get('url','N/A')}"
            )
        except Exception as e:
            return f"❌ Error: {e}"

# Books (Open Library)
@mcp.tool()
async def search_books(query: str, limit: int = 5) -> List[dict]:
    """Search books via Open Library."""
    limit = max(1, min(limit, 10))
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            data = (await client.get(f"https://openlibrary.org/search.json?q={query}&limit={limit}")).json() or {}
            out = []
            for d in (data.get("docs") or [])[:limit]:
                out.append({
                    "title": d.get("title"),
                    "authors": (d.get("author_name") or [])[:3],
                    "first_publish_year": d.get("first_publish_year"),
                    "isbn": (d.get("isbn") or [None])[0],
                })
            return out or [{"message": f"No results for '{query}'"}]
        except Exception as e:
            return [{"error": str(e)}]

# ---------------- Your requested additions (1,2,3,5,6,7,8,11,12,18) ----------------

# (1) TheMealDB - search_recipes
@mcp.tool()
async def search_recipes(query: str, first_n: int = 1) -> List[dict]:
    """
    Search recipes via TheMealDB. Returns up to first_n results with core fields.
    query: e.g. "chicken", "arrabiata"
    """
    first_n = max(1, min(first_n, 5))
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(f"https://www.themealdb.com/api/json/v1/1/search.php?s={query}")
            data = r.json() or {}
            meals = data.get("meals") or []
            out = []
            for m in meals[:first_n]:
                # Collect ingredients + measures (up to 20)
                ings = []
                for i in range(1, 21):
                    ing = m.get(f"strIngredient{i}")
                    mea = m.get(f"strMeasure{i}")
                    if ing and ing.strip():
                        ings.append({"ingredient": ing.strip(), "measure": (mea or "").strip()})
                out.append({
                    "id": m.get("idMeal"),
                    "name": m.get("strMeal"),
                    "category": m.get("strCategory"),
                    "area": m.get("strArea"),
                    "instructions": m.get("strInstructions"),
                    "ingredients": ings,
                    "thumb": m.get("strMealThumb"),
                    "youtube": m.get("strYoutube"),
                    "source": m.get("strSource"),
                })
            return out or [{"message": f"No recipes found for '{query}'"}]
        except Exception as e:
            return [{"error": str(e)}]

# (2) MusicBrainz - search_artist
@mcp.tool()
async def search_artist(artist_name: str, limit: int = 3) -> List[dict]:
    """
    Search for an artist via MusicBrainz.
    Returns basic metadata for up to 'limit' results.
    """
    limit = max(1, min(limit, 10))
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "mcp-curated/1.0"}) as client:
        try:
            r = await client.get(
                "https://musicbrainz.org/ws/2/artist/",
                params={"query": artist_name, "fmt": "json", "limit": limit},
            )
            data = r.json() or {}
            artists = data.get("artists") or []
            out = []
            for a in artists[:limit]:
                out.append({
                    "id": a.get("id"),
                    "name": a.get("name"),
                    "disambiguation": a.get("disambiguation"),
                    "country": a.get("country"),
                    "life_span": a.get("life-span"),
                    "score": a.get("score"),
                    "type": a.get("type"),
                    "tags": [t.get("name") for t in (a.get("tags") or [])],
                })
            return out or [{"message": f"No artist found for '{artist_name}'"}]
        except Exception as e:
            return [{"error": str(e)}]

# (3) Dog CEO - random image / by breed
@mcp.tool()
async def get_dog_image(breed: Optional[str] = None) -> dict:
    """
    Get a random dog image. If 'breed' provided (e.g., 'husky'), fetch from that breed.
    """
    base = "https://dog.ceo/api"
    url = f"{base}/breed/{breed}/images/random" if breed else f"{base}/breeds/image/random"
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            data = (await client.get(url)).json() or {}
            return {"status": data.get("status"), "image": data.get("message")}
        except Exception as e:
            return {"error": str(e)}

# (5) TVMaze - search shows
@mcp.tool()
async def search_tv_shows(query: str, limit: int = 5) -> List[dict]:
    """
    Search TV shows via TVMaze and return compact results.
    """
    limit = max(1, min(limit, 10))
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(f"https://api.tvmaze.com/search/shows?q={query}")
            data = r.json() or []
            out = []
            for item in data[:limit]:
                s = item.get("show", {})
                out.append({
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "type": s.get("type"),
                    "language": s.get("language"),
                    "genres": s.get("genres"),
                    "status": s.get("status"),
                    "premiered": s.get("premiered"),
                    "officialSite": s.get("officialSite"),
                    "rating": (s.get("rating") or {}).get("average"),
                    "summary": (s.get("summary") or "").replace("<p>", "").replace("</p>", "").strip(),
                })
            return out or [{"message": f"No TV shows found for '{query}'"}]
        except Exception as e:
            return [{"error": str(e)}]

# (6) Open Trivia DB - trivia questions
@mcp.tool()
async def get_trivia(amount: int = 1,
                     category: Optional[int] = None,
                     difficulty: Optional[str] = None,
                     type: Optional[str] = None) -> dict:
    """
    Fetch trivia questions.
    - amount: 1..10
    - category: numeric category id (optional)
    - difficulty: easy|medium|hard (optional)
    - type: multiple|boolean (optional)
    """
    amount = max(1, min(amount, 10))
    params = {"amount": amount}
    if category is not None:
        params["category"] = category
    if difficulty:
        params["difficulty"] = difficulty
    if type:
        params["type"] = type
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get("https://opentdb.com/api.php", params=params)
            data = r.json() or {}
            return data
        except Exception as e:
            return {"error": str(e)}

# (7) Numbers API - number/date/year/math facts
@mcp.tool()
async def get_number_fact(number: str = "random", fact_type: str = "trivia") -> str:
    """
    Get a number fact.
    - number: "random" or a specific number or date (e.g., "6/28" for June 28 with type='date')
    - fact_type: trivia | math | date | year
    """
    fact_type = fact_type.lower().strip()
    if fact_type not in {"trivia", "math", "date", "year"}:
        fact_type = "trivia"
    path = f"{number}/{fact_type}" if number != "random" else f"random/{fact_type}"
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(f"http://numbersapi.com/{path}")
            return r.text
        except Exception as e:
            return f"❌ Error: {e}"

# (8) Quotable - random quote or by author
@mcp.tool()
async def get_random_quote(author: Optional[str] = None) -> dict:
    """
    Get a random quote, optionally filtered by author (partial name match).
    """
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            if author:
                r = await client.get("https://api.quotable.io/quotes", params={"author": author, "limit": 1})
                data = r.json() or {}
                results = data.get("results") or []
                if not results:
                    return {"message": f"No quote found for author '{author}'"}
                q = results[0]
            else:
                r = await client.get("https://api.quotable.io/random")
                q = r.json() or {}
            return {
                "content": q.get("content"),
                "author": q.get("author"),
                "tags": q.get("tags"),
            }
        except Exception as e:
            return {"error": str(e)}

# (11) Open Notify - ISS info
@mcp.tool()
async def get_iss_location() -> dict:
    """Get current ISS latitude/longitude."""
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            data = (await client.get("http://api.open-notify.org/iss-now.json")).json() or {}
            return data
        except Exception as e:
            return {"error": str(e)}

@mcp.tool()
async def get_people_in_space() -> dict:
    """Get current people in space."""
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            data = (await client.get("http://api.open-notify.org/astros.json")).json() or {}
            return data
        except Exception as e:
            return {"error": str(e)}

# (12) REST Countries v3
@mcp.tool()
async def get_country(name: str) -> dict:
    """Lookup country info by name (REST Countries v3)."""
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get(f"https://restcountries.com/v3.1/name/{name}")
            data = r.json() or []
            if not data or isinstance(data, dict) and data.get("status") == 404:
                return {"message": f"No country data for '{name}'"}
            c = data[0]
            return {
                "name": (c.get("name") or {}).get("common"),
                "official_name": (c.get("name") or {}).get("official"),
                "cca2": c.get("cca2"),
                "cca3": c.get("cca3"),
                "region": c.get("region"),
                "subregion": c.get("subregion"),
                "capital": c.get("capital"),
                "population": c.get("population"),
                "currencies": c.get("currencies"),
                "languages": c.get("languages"),
                "flag_png": (c.get("flags") or {}).get("png"),
                "maps": c.get("maps"),
            }
        except Exception as e:
            return {"error": str(e)}

# (18) Sunrise-Sunset.org
@mcp.tool()
async def get_sunrise_sunset(lat: float, lon: float, date: str = "today") -> dict:
    """
    Get sunrise/sunset times.
    - lat, lon: coordinates
    - date: 'today' or 'YYYY-MM-DD'
    """
    params = {"lat": lat, "lng": lon, "date": date, "formatted": 0}
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get("https://api.sunrise-sunset.org/json", params=params)
            return r.json() or {}
        except Exception as e:
            return {"error": str(e)}

# ---------- Run as SSE server ----------
if __name__ == "__main__":
    # Bind to Codespaces
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = int(os.getenv("PORT", "8080"))
    # Default SSE mount path is "/sse"; keep it so Aria can connect with .../sse
    mcp.run(transport="sse")