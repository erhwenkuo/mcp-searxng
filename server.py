from logging import info
import logging
from typing import Optional
from httpx import AsyncClient, HTTPStatusError
from os import getenv
from typing import Any
from markdownify import markdownify as md
import mcp.types as types
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
import uvicorn
from pydantic import BaseModel, Field

# 設定日誌
logger = logging.getLogger(__name__)

# 為 SearXNG (SSE) 服務構建 FastMCP 實例
mcp = FastMCP("mcp-searxng")

### 1. 構建呼叫 SearXNG 服務 API 的方法與返回結果的序列化類別 ####
class SearchResult(BaseModel):
    url: str
    title: str
    content: str
    # thumbnail: Optional[str] = None
    # engine: str
    # parsed_url: list[str]
    # template: str
    # engines: list[str]
    # positions: list[int]
    # publishedDate: Optional[str] = None
    # score: float
    # category: str


class InfoboxUrl(BaseModel):
    title: str
    url: str


class Infobox(BaseModel):
    infobox: str
    id: str
    content: str
    # img_src: Optional[str] = None
    urls: list[InfoboxUrl]
    # attributes: list[str]
    # engine: str
    # engines: list[str]


class Response(BaseModel):
    query: str
    number_of_results: int
    results: list[SearchResult]
    # answers: list[str]
    # corrections: list[str]
    infoboxes: list[Infobox]
    # suggestions: list[str]
    # unresponsive_engines: list[str]

# 呼叫 SearXNG 服務 API
async def search(query: str, limit: int = 3) -> str:
    client = AsyncClient(base_url=str(getenv("SEARXNG_URL", "http://localhost:8080")))

    params: dict[str, str] = {"q": query, "format": "json"}

    response = await client.get("/search", params=params)
    response.raise_for_status()

    data = Response.model_validate_json(response.text)

    text = ""

    for index, infobox in enumerate(data.infoboxes):
        text += f"Infobox: {infobox.infobox}\n"
        text += f"ID: {infobox.id}\n"
        text += f"Content: {infobox.content}\n"
        text += "\n"

    if len(data.results) == 0:
        text += "No results found\n"

    for index, result in enumerate(data.results):
        text += f"Title: {result.title}\n"
        text += f"URL: {result.url}\n"
        text += f"Content: {result.content}\n"
        text += "\n"

        if index == limit - 1:
            break

    return str(text)


### 2. 構建呼叫 MCP 規格中的 list_tools 與 call_tool() 的實作 ####
@mcp.tool()
async def web_search(query: str, 
                     count: int = 3) -> str:
    """Performs a web search using the SearxNG API, ideal for general queries, news, articles, and online content. Use this for broad information gathering, recent events, or when you need diverse web sources."""
    client = AsyncClient(base_url=str(getenv("SEARXNG_URL", "http://localhost:8080")))

    params: dict[str, str] = {"q": query, "format": "json", "engines": "google"}

    response = await client.get("/search", params=params)

    response.raise_for_status()

    data = Response.model_validate_json(response.text)

    text = ""

    for index, infobox in enumerate(data.infoboxes):
        text += f"Infobox: {infobox.infobox}\n"
        text += f"ID: {infobox.id}\n"
        text += f"Content: {infobox.content}\n"
        text += "\n"

    if len(data.results) == 0:
        text += "No results found\n"

    for index, result in enumerate(data.results):
        text += f"Title: {result.title}\n"
        text += f"URL: {result.url}\n"
        text += f"Content: {result.content}\n"
        text += "\n"

        if index == count - 1:
            break

    return str(text)


@mcp.tool()
async def web_url_read(url: str) -> str:
    """Read the content from an URL. Use this for further information retrieving to understand the content of each URL."""
    headers = {
        "User-Agent": "MCP-SEARXNG"
    }

    try:
        async with AsyncClient(follow_redirects=True, headers=headers, timeout=10.0, max_redirects=5) as client:
                response = await client.get(url)
                # check if any exception
                response.raise_for_status()
                # convert html to markdown
                return md(response.text)
    except HTTPStatusError as e:
        logger.error(f"HTTP error fetching URL {url}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching URL {url}: {str(e)}")
        return None

# 設定讓 mcp sever 啟用 sse transport 允許 AI Agent 遠端連線使用
def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

# 服務啟動的進入點
if __name__ == "__main__":
    mcp_server = mcp._mcp_server

    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Run MCP-SearXNG SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5488, help='Port to listen on')
    parser.add_argument('--searxng_url', default='http://localhost:8888', help='SearXNG url to connect to')
    
    args = parser.parse_args()

    if os.environ.get('SEARXNG_URL') is None:
        os.environ['SEARXNG_URL']=args.searxng_url

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    uvicorn.run(starlette_app, host=args.host, port=args.port)