from aiohttp import web, ClientSession
import os
import logging

log = logging.getLogger(__name__)


async def index_handler(request):
    log.info('[Index handler]')
    return web.Response(text="""\
<html>
    <head>
        <title>Test lab</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Test lab</h1>
        <a href="/page1">Page1</a><br>
        <a href="./page2">Page2</a>
    </body>
<html>
""", content_type='text/html')

async def test1_handler(request):
    log.info('[Test handler]')
    response = web.Response(text=f"""\
<html>
    <head>
        <title>Test page</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Test page</h1>
        <a href="/">Homepage</a><br/><a href="/page3">Page3</a>
    </body>
<html>
""")
    response.content_type = "text/html"
    return response

async def test2_handler(request):
    log.info('[Test handler]')
    response = web.Response(text=f"""\
<html>
    <head>
        <title>Page with relative paths</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Test page</h1>
        <a href="./">Back</a>
    </body>
<html>
""")
    response.content_type = "text/html"
    return response

async def test3_handler(request):
    log.info('[Test handler]')
    response = web.Response(text=f"""\
<html>
    <head>
        <title>Test page</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Test page</h1>
        <a href="/">Homepage</a>
    </body>
<html>
""")
    response.content_type = "text/html"
    return response

async def proxy(request, url:str):
    async with ClientSession(auto_decompress=False) as session:
        async with await session.request(request.method, url) as proxy_request:
            if proxy_request.status not in {201, 202, 200}:
                return None
            log.debug("Prequest h: %s %s", proxy_request.headers, proxy_request)
            print(proxy_request)
            print(request)
            proxy_response = web.StreamResponse(
                status=proxy_request.status,
                reason=proxy_request.reason,
            )
            proxy_response.headers.update(proxy_request.headers)
            await proxy_response.prepare(request)
            while True:
                chunk = await proxy_request.content.read()
                if not chunk:
                    break
                await proxy_response.write(chunk)
            await proxy_response.write_eof()
            return proxy_response

async def proxy_handler(request):
    host = request.match_info.get("host")
    path = request.match_info.get("path")
    log.debug("Host %s, Path %s", host, path)
    print(f"{host=}, {path=}")
    response = await proxy(request, "https://" + host + "/" + path)
    if response is not None:
        return response
    return web.FileResponse(
        headers={"Cache-Control": "max-age=6000, immutable"},
        path=(os.path.dirname(__file__) or ".") + "/image.svg",
    )
    

app = web.Application()
app.add_routes([
    web.get("/", index_handler),
    web.get("/page1", test1_handler),
    web.get("/page2", test2_handler),
    web.get("/page3", test3_handler),
    web.get("/proxy/{host:[^\\/]+}/{path:.*}", proxy_handler)
])


env_port = os.environ.get('PORT')
port_number = int(env_port) if env_port and env_port.isdigit() else 10000

web.run_app(app, port=port_number)
