#!/usr/bin/env python3
# MCP SSE server for Aria / Claude / MCP Inspector
import os
import json
from typing import List
import httpx
from mcp.server.fastmcp import FastMCP

# Create server
mcp = FastMCP(
    name="Curated MCP Server",
    instructions="Utilities: weather, jokes, facts, NASA APOD, recipes, books."
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
@mcp.tool()
async def get_weather(city: str = "New York") -> str:
    """Get current weather for a city"""
    async with httpx.AsyncClient(timeout=20) as client:
        # 1) geocode
        gr = await client.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}")
        g = gr.json()
        if not g.get("results"):
            return f"❌ City '{city}' not found."
        lat = g["results"][0]["latitude"]
        lon = g["results"][0]["longitude"]
        country = g["results"][0].get("country", "")

        # 2) weather
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

@mcp.tool()
async def get_random_joke(type: str = "general") -> str:
    """Get a random joke. type: general | programming | dad"""
    t = (type or "general").lower()
    async with httpx.AsyncClient(timeout=20) as client:
        if t == "programming":
            r = await client.get("https://official-joke-api.appspot.com/jokes/programming/random")
            jokes = r.json()
            joke = jokes[0] if jokes else {}
            return f"💻 {joke.get('setup','')} — {joke.get('punchline','')}".strip()
        if t == "dad":
            r = await client.get("https://icanhazdadjoke.com/", headers={"Accept": "application/json"})
            data = r.json()
            default = "Why don't scientists trust atoms? Because they make up everything!"
            return f"👨‍🍼 {data.get('joke', default)}"
        r = await client.get("https://official-joke-api.appspot.com/random_joke")
        joke = r.json()
        return f"😂 {joke.get('setup','')} — {joke.get('punchline','')}".strip()

@mcp.tool()
async def get_random_fact() -> str:
    """Get a random interesting fact"""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get("https://uselessfacts.jsph.pl/random.json?language=en")
        return f"🤓 {r.json().get('text', 'Did you know? Octopuses have three hearts!')}"

@mcp.tool()
async def get_nasa_apod(date: str | None = None) -> str:
    """Get NASA Astronomy Picture of the Day (optional YYYY-MM-DD)"""
    url = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"
    if date:
        url += f"&date={date}"
    async with httpx.AsyncClient(timeout=20) as client:
        data = (await client.get(url)).json()
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

@mcp.tool()
async def search_books(query: str, limit: int = 5) -> List[dict]:
    """Search books via Open Library"""
    limit = max(1, min(limit, 10))
    async with httpx.AsyncClient(timeout=20) as client:
        data = (await client.get(f"https://openlibrary.org/search.json?q={query}&limit={limit}")).json()
        out = []
        for d in (data.get("docs") or [])[:limit]:
            out.append({
                "title": d.get("title"),
                "authors": (d.get("author_name") or [])[:3],
                "first_publish_year": d.get("first_publish_year"),
                "isbn": (d.get("isbn") or [None])[0],
            })
        return out or [{"message": f"No results for '{query}'"}]

# ---------- Run as SSE server ----------
if __name__ == "__main__":
    # Bind to Codespaces
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = int(os.getenv("PORT", "3258"))
    # Default SSE mount path is "/sse"; keep it so Aria can connect with .../sse
    mcp.run(transport="sse")