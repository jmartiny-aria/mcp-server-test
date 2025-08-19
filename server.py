#!/usr/bin/env python3
"""
Curated MCP Server for Testing
Provides tools using carefully selected free APIs
"""

import asyncio
import json
import sys
from typing import Any, Dict, List

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

# Initialize the MCP server
app = Server("curated-mcp-server")


@app.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="weather://current",
            name="Current Weather",
            description="Get current weather information",
            mimeType="application/json",
        ),
        Resource(
            uri="nasa://apod",
            name="NASA Picture of the Day",
            description="NASA's Astronomy Picture of the Day",
            mimeType="application/json",
        ),
        Resource(
            uri="jokes://random",
            name="Random Jokes",
            description="Get random jokes",
            mimeType="application/json",
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a specific resource"""
    if uri == "weather://current":
        # Using free weather API (no key required)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast?latitude=40.7128&longitude=-74.0060&current_weather=true"
            )
            return json.dumps(response.json(), indent=2)

    elif uri == "nasa://apod":
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"
            )
            return json.dumps(response.json(), indent=2)

    elif uri == "jokes://random":
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://official-joke-api.appspot.com/random_joke"
            )
            return json.dumps(response.json(), indent=2)

    return "Resource not found"


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_weather",
            description="Get weather for a city",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name",
                    }
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="get_random_joke",
            description="Get a random joke",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Type of joke: general, programming, or dad (optional)",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="get_random_fact",
            description="Get a random interesting fact",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_nasa_apod",
            description="Get NASA's Astronomy Picture of the Day",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (optional, defaults to today)",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="search_spotify_artist",
            description="Search for an artist on Spotify and get basic info",
            inputSchema={
                "type": "object",
                "properties": {
                    "artist_name": {
                        "type": "string",
                        "description": "Name of the artist to search for",
                    }
                },
                "required": ["artist_name"],
            },
        ),
        Tool(
            name="search_recipes",
            description="Search for food recipes",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Recipe search query (e.g., 'chicken pasta', 'chocolate cake')",
                    },
                    "diet": {
                        "type": "string",
                        "description": "Dietary restriction (optional): vegetarian, vegan, gluten-free, etc.",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_books",
            description="Search for books using Open Library",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Book title, author, or keyword to search for",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (1-10, default: 5)",
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute a tool"""

    if name == "get_weather":
        city = arguments.get("city", "New York")
        # Use free geocoding API to get coordinates
        async with httpx.AsyncClient() as client:
            try:
                # Get coordinates for the city
                geo_response = await client.get(
                    f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
                )
                geo_data = geo_response.json()

                if geo_data.get("results"):
                    result = geo_data["results"][0]
                    lat = result["latitude"]
                    lon = result["longitude"]
                    country = result.get("country", "")

                    # Get weather data
                    weather_response = await client.get(
                        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,precipitation&timezone=auto"
                    )
                    weather_data = weather_response.json()

                    current = weather_data.get("current_weather", {})
                    temp_c = current.get("temperature", 0)
                    temp_f = (temp_c * 9 / 5) + 32

                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"🌤️ Weather in {city}, {country}\n\n"
                                f"🌡️ Temperature: {temp_c}°C ({temp_f:.1f}°F)\n"
                                f"💨 Wind Speed: {current.get('windspeed', 'N/A')} km/h\n"
                                f"🧭 Wind Direction: {current.get('winddirection', 'N/A')}°\n"
                                f"⏰ Time: {current.get('time', 'N/A')}"
                            ),
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"❌ City '{city}' not found. Please check the spelling.",
                        )
                    ]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error getting weather data: {str(e)}")]

    elif name == "get_random_joke":
        joke_type = arguments.get("type", "general").lower()

        async with httpx.AsyncClient() as client:
            try:
                if joke_type == "programming":
                    response = await client.get(
                        "https://official-joke-api.appspot.com/jokes/programming/random"
                    )
                    jokes = response.json()
                    joke = jokes[0] if jokes else {}
                elif joke_type == "dad":
                    response = await client.get(
                        "https://icanhazdadjoke.com/", headers={"Accept": "application/json"}
                    )
                    data = response.json()
                    # FIX: avoid backslash escaping inside f-string expression
                    return [
                        TextContent(
                            type="text",
                            text=f"😄 Dad Joke:\n\n{data.get('joke', \"Why don't scientists trust atoms? Because they make up everything!\")}",
                        )
                    ]
                else:
                    response = await client.get(
                        "https://official-joke-api.appspot.com/random_joke"
                    )
                    joke = response.json()

                if joke_type != "dad":
                    setup = joke.get("setup", "")
                    punchline = joke.get("punchline", "")
                    return [
                        TextContent(
                            type="text",
                            text=f"😂 {joke_type.title()} Joke:\n\n{setup}\n\n{punchline}",
                        )
                    ]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Couldn't fetch a joke: {str(e)}")]

    elif name == "get_random_fact":
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://uselessfacts.jsph.pl/random.json?language=en"
                )
                fact_data = response.json()
                return [
                    TextContent(
                        type="text",
                        text=(
                            "🤓 Random Fact:\n\n"
                            f"{fact_data.get('text', 'Did you know? Octopuses have three hearts!')}"
                        ),
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Couldn't fetch a fact: {str(e)}")]

    elif name == "get_nasa_apod":
        date_param = arguments.get("date", "")
        url = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"
        if date_param:
            url += f"&date={date_param}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                data = response.json()

                if "error" not in data:
                    explanation = data.get("explanation", "No description available")
                    # Truncate long explanations
                    if len(explanation) > 400:
                        explanation = explanation[:400] + "..."

                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"🚀 NASA APOD - {data.get('date', 'Today')}\n\n"
                                f"✨ {data.get('title', 'Amazing Space Image')}\n\n"
                                f"📝 {explanation}\n\n"
                                f"🔗 Image URL: {data.get('url', 'N/A')}\n"
                                f"🔗 HD URL: {data.get('hdurl', 'Same as above')}"
                            ),
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"❌ NASA API Error: {data.get('error', {}).get('message', 'Unknown error')}",
                        )
                    ]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error fetching NASA APOD: {str(e)}")]

    elif name == "search_spotify_artist":
        artist_name = arguments.get("artist_name", "")

        async with httpx.AsyncClient() as client:
            try:
                # Using a free music API instead of Spotify (which requires auth)
                response = await client.get(
                    f"https://musicbrainz.org/ws/2/artist/?query={artist_name}&fmt=json&limit=3"
                )
                data = response.json()

                if data.get("artists"):
                    artist = data["artists"][0]

                    # Get additional info
                    artist_info = f"🎵 Artist: {artist.get('name', 'Unknown')}\n\n"

                    if artist.get("disambiguation"):
                        artist_info += f"🏷️ Type: {artist['disambiguation']}\n"

                    if artist.get("country"):
                        artist_info += f"🌍 Country: {artist['country']}\n"

                    if artist.get("life-span", {}).get("begin"):
                        begin = artist["life-span"]["begin"]
                        end = artist["life-span"].get("end", "present")
                        artist_info += f"📅 Active: {begin} - {end}\n"

                    if artist.get("tags"):
                        genres = [tag["name"] for tag in artist["tags"][:3]]
                        artist_info += f"🎼 Genres: {", ".join(genres)}\n"

                    artist_info += f"⭐ Score: {artist.get('score', 0)}/100"

                    return [TextContent(type="text", text=artist_info)]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"🔍 No artist found for '{artist_name}'. Try a different name or spelling.",
                        )
                    ]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error searching for artist: {str(e)}")]

    elif name == "search_recipes":
        query = arguments.get("query", "")
        diet = arguments.get("diet", "")

        async with httpx.AsyncClient() as client:
            try:
                # Using TheMealDB (free recipe API)
                response = await client.get(
                    f"https://www.themealdb.com/api/json/v1/1/search.php?s={query}"
                )
                data = response.json()

                if data.get("meals"):
                    meal = data["meals"][0]  # Get the first result

                    # Get ingredients
                    ingredients: List[str] = []
                    for i in range(1, 21):  # API has up to 20 ingredients
                        ingredient = meal.get(f"strIngredient{i}")
                        measure = meal.get(f"strMeasure{i}")
                        if ingredient and ingredient.strip():
                            m = (measure or "").strip()
                            line = f"• {m} {ingredient}".strip()
                            ingredients.append(line)

                    recipe_info = f"🍳 Recipe: {meal.get('strMeal', 'Delicious Dish')}\n\n"
                    recipe_info += f"🏷️ Category: {meal.get('strCategory', 'N/A')}\n"
                    recipe_info += f"🌍 Origin: {meal.get('strArea', 'International')}\n\n"

                    if ingredients:
                        recipe_info += "📋 Ingredients:\n" + "\n".join(ingredients[:10]) + "\n\n"

                    instructions = meal.get("strInstructions", "Instructions not available")
                    if len(instructions) > 300:
                        instructions = instructions[:300] + "..."
                    recipe_info += f"👩‍🍳 Instructions:\n{instructions}\n\n"

                    if meal.get("strYoutube"):
                        recipe_info += f"📺 Video: {meal['strYoutube']}\n"

                    if meal.get("strMealThumb"):
                        recipe_info += f"🖼️ Image: {meal['strMealThumb']}"

                    return [TextContent(type="text", text=recipe_info)]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=(
                                f"🔍 No recipes found for '{query}'. "
                                "Try searching for common dishes like 'pasta', 'chicken', 'cake', etc."
                            ),
                        )
                    ]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error searching recipes: {str(e)}")]

    elif name == "search_books":
        query = arguments.get("query", "")
        limit = min(arguments.get("limit", 5), 10)  # Max 10 results

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://openlibrary.org/search.json?q={query}&limit={limit}"
                )
                data = response.json()

                if data.get("docs"):
                    books_info = f"📚 Found {len(data['docs'])} books for '{query}':\n\n"

                    for i, book in enumerate(data["docs"][:limit], 1):
                        title = book.get("title", "Unknown Title")
                        authors = book.get("author_name", ["Unknown Author"])
                        pub_year = book.get("first_publish_year", "Unknown")

                        books_info += f"{i}. 📖 {title}\n"
                        books_info += f"   ✍️ By: {', '.join(authors[:2])}\n"  # Max 2 authors
                        books_info += f"   📅 Published: {pub_year}\n"

                        if book.get("isbn"):
                            books_info += f"   📄 ISBN: {book['isbn'][0]}\n"

                        if book.get("subject"):
                            subjects = book["subject"][:3]  # Max 3 subjects
                            books_info += f"   🏷️ Subjects: {', '.join(subjects)}\n"

                        books_info += "\n"

                    return [TextContent(type="text", text=books_info.strip())]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"📚 No books found for '{query}'. Try different keywords or author names.",
                        )
                    ]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error searching books: {str(e)}")]

    return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]  # fallback


async def main():
    """Main entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream, write_stream, app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
