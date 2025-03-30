# mcp-searxng

一個用來讓 AI Agent 可透過 SearXNG 服務來搜尋外部網站內容與資訊的 MCP server 。

一個給 AI Agent 使用的 MCP Server 範例，用來讓 AI Agent 可透過 SearXNG 的開源元搜尋引擎來搜尋外在新的資訊。

現時出現許多 Google 以外的搜尋引擎，他們試圖在 Google 做不好的地方搶佔市場。比如 DuckDuckGo 強調不追蹤使用者，Ecosia 搜尋就種樹，Brave Search 則是要集眾人之力打造自由的搜尋引擎。

可是這些引擎回傳的結果總是不讓人滿意，一來他們爬的網頁沒有Google多；二來中文支援度不好，儘管他們能爬到一些Google不會顯示的有趣網頁，但Google以外的搜尋引擎還是很難用的說。

那我們把多個搜尋引擎結果結合起來不就好了嗎！？這就是元搜尋引擎做的事情。SearXNG 這款開源的元搜尋引擎軟體，可以自架，也可使用熱心網友提供的站台。對於企業來說 SearXNG 是保護穩私與安全的控制之下又能夠讓 AI Agent 能夠很好地去搜尋所需要的外部數據。

參考:
- [SearXNG 官網](https://docs.searxng.org/)
- [自架開源SearXNG元搜尋引擎，一次搜尋Google、Duckduckgo多個搜尋引擎](https://ivonblog.com/posts/self-hosting-searxng-docker-instance/)

## 目的

這個 mcp server 示範了基於 SSE 的 MCP 伺服器 (結合了 SearXNG 與 微軟的 markdownify 來提供提取網頁變成 markdown 格式文字）和使用 [mcp inspector](https://modelcontextprotocol.io/docs/tools/inspector) (MCP 用戶端)的工作模式。

## 運行環境

本專案使用 [uv](https://docs.astral.sh/uv/) 來管理相關的依賴與 python 的運行環境, 如果尚未安裝 uv 可依照官網的安裝指示來安裝。

接下來的相關命令都是在 Ubuntu 24.04 的環境下執行的, 其它作業系統的操作請自行修改:

```bash
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

下載源碼:

```
$ git clone https://github.com/erhwenkuo/mcp-searxng.git

$ cd mcp-searxng

$ uv sync
```

## 運行服務

### 運行 SearXNG 服務

首先在運行的機器上安裝 Docker 與進行相關的設定, 詳細的訊息請參考: [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

在本專案目錄下有一個預先簡單配置好的 SearXNG 設定來方便測試。

```
mcp-searxng/searxng-docker/
├── docker-compose.yaml
└── searxng
    ├── settings.yml
    └── uwsgi.ini

```

切換到 `searxng-docker` 目錄并使用 Docker compose 來啟動一個 SearXNG 的服務:

```bash
$ cd searxng-docker
$ docker compose up -d
$ docker compose ps

NAME      IMAGE                              COMMAND                  SERVICE   CREATED          STATUS                    PORTS
searxng   docker.io/searxng/searxng:latest   "/sbin/tini -- /usr/…"   searxng   29 minutes ago   Up 29 minutes (healthy)   0.0.0.0:8888->8080
```

測試用的 SearXNG 服務映射到本機的 `port: 8888`。

### 啟動 MCP-SEARXNG 服務

#### 方法 1. 使用 uv 來啟動:

鍵入下列命令來啟動:

```bash
$ uv run server.py --searxng_url="http://localhost:8888"

INFO:     Started server process [219904]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5488 (Press CTRL+C to quit)
```

### 使用 Docker 來啟動

首先構建 Docker image:

```
$ docker build -t mcp-searxng .
```

啟動 mcp-searxng, 由於是使用 docker 來啟動 mcp-searxng 服務, 在設定連接到 SearXNG 的服務時就不能用 `localhost` 來指向 SearXNG 的位址了, 建議直接查詢本機的 IP 位址之後再使用 `SEARXNG_URL` 的環境變數來設定。

下面的啟動參數是假設本機的 IP 是 `192.168.54.88`:
```
$ docker run -d -e SEARXNG_URL="http://localhost:8888" -p 5488:5488 mcp-searxng
```

## 驗證結果

首先安裝 nodejs:

```bash
# Download and install nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash

# in lieu of restarting the shell
\. "$HOME/.nvm/nvm.sh"

# Download and install Node.js:
nvm install 22

# Verify the Node.js version:
node -v # Should print "v22.14.0".
nvm current # Should print "v22.14.0".

# Verify npm version:
npm -v # Should print "10.9.2".
```

接著啟動 [mcp inspector](https://github.com/modelcontextprotocol/inspector):

```bash
$ npx @modelcontextprotocol/inspector

Starting MCP inspector...
Proxy server listening on port 3000

🔍 MCP Inspector is up and running at http://localhost:5173 🚀
```

使用瀏覽器打開 `http://localhost:5173`, 然後進行下列的動作:

1. 在 Transport Type 選擇 `SSE`
2. 在 URL 鍵入 mcp server 的位址與端口, `http://localhost:5488/sse`
3. 點擊 `Connect`, 如果有看到狀態是 "Connected" 代表己經成功連線到 mcp-weather 服務了
4. 點擊上方的 "Tools" Tab
5. 點擊 "List Tools" 按鈕之後會看到有兩個工具:
    - `web_search`
    - `web_url_read`
6. 點擊 `web_search` 之後在右側會出現這個工具的說明與參數, 在 `query` 的輸入欄中鍵入想要搜尋的關鍵字, 然後點擊 "Run Tool" 按鈕

效果如下圖所示:

![](./test_web_search.png)

測試 `web_url_read`:

- 點擊 `web_url_read` 之後在右側會出現這個工具的說明與參數, 在 `url` 的輸入欄中鍵入想要取得的網頁 然後點擊 "Run Tool" 按鈕

![](./test_web_url_read.png)

## 為什麼使用 SSE

這意味著 MCP 伺服器可以是某個運行在遠端的進程服務，AI Agent（客戶端）可以隨時隨地連接、使用和斷開連接。換句話說，基於 SSE 的伺服器和客戶端可以是解耦的進程（甚至可能在解耦的節點上）。

與客戶端本身將伺服器作為子進程生成的基於 STDIO 的模式相比，這是不同的，並且更適合「雲端原生」用例。

### MCP Server

`server.py` 是 SSE-based MCP server, 預設情況下，伺服器運行在 `0.0.0.0:5488` 上運行，但可以使用命令列參數進行配置，例如：

```bash
uv run server.py --host <your host> --port <your port>
```

啟動參數:

| 啟動參數 | 必要 | 預設 | 型別 | 說明 |
|---------|-----|-----|------|-----|
|`--host`|N|`0.0.0.0`|str|Host to bind to|
|`--host`|N|`5488`|int|Port to listen on|
|`--searxng_url`|N|`http://localhost:8888`|str|SearXNG url to connect to|