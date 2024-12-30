import logging
import os
import hashlib
from aiohttp import web, ClientSession
from typing import List, Optional, Awaitable
from functools import wraps


log = logging.getLogger(__name__)
HEADER_LENGTH = 16

async def get_proxy_request_stream(request: web.Request, url:str) -> Awaitable[web.StreamResponse|None]:
    """
    This function requests a resource and proxies its response
    """
    # The resource must be transmitted as is, without decompression due to a browser rejects a request which length of body do not match the value specified in the Content-length header
    async with ClientSession(auto_decompress=False) as session:
        async with await session.request(request.method, url) as proxy_request:
            if proxy_request.status not in {201, 202, 200}:
                return None
            proxy_response = web.StreamResponse(
                status=proxy_request.status,
                reason=proxy_request.reason,
            )
            proxy_response.headers.update(proxy_request.headers)
            await proxy_response.prepare(request)
            while chunk := await proxy_request.content.read():
                await proxy_response.write(chunk)
            proxy_response._request = proxy_request
            await proxy_response.write_eof()
            return proxy_response

def cache_request(id_cb, cache_dir:str="/tmp"):
    """
    This decorator caches the response of a request action used to return the dtalab thumbnail
    """
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            resource_id = id_cb(args[0])
            resource_path = cache_dir + "/" + resource_id
            # Check if cache is available for the resource
            if os.path.exists(resource_path):
                try:
                    with open(resource_path, "rb") as file:
                        content_type = file.read(HEADER_LENGTH)
                        content_type = content_type.decode().rstrip()
                        body = file.read()

                        if "/" in content_type:
                            return web.Response(
                                headers={"Cache-Control": "max-age=31536000, immutable"},
                                body=body,
                                content_type=content_type,
                            )
                except Exception as exc:
                    log.error("Failed to read image cache due to error %s", str(exc))
            
            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                raise
            print(f"Cache {result}/{type(result)}")
            
            # Make an attempt to save cache of the resource
            if isinstance(result, web.Response):
                # The image MIME type must be no longer than 16 characters, the rest must be filled with spaces:
                # b"image/jpg      "
                content_type:bytes = result.content_type.ljust(HEADER_LENGTH).encode("utf-8")
                try:
                    with open(resource_path, "wb") as file:
                        file.write(content_type)
                        file.write(result.body)
                except Exception as exc:
                    print("Failed to save image cache to file system due to error ", str(exc))
                else:
                    print("Create cache ", resource_path)
            elif isinstance(result, web.StreamResponse) and not isinstance(result, web.FileResponse):
                content_type:bytes = result.content_type.ljust(HEADER_LENGTH).encode("utf-8")
                # The file must be uncompressed if the server provides a compressed file
                async with ClientSession(auto_decompress=True) as session:
                    async with await session.request(result._request.method, result._request.url) as request:
                        try:
                            with open(resource_path, "wb") as file:
                                file.write(content_type)
                                while chunk := await request.content.read():
                                    file.write(chunk)
                        except Exception as exc:
                            print("Failed to save image cache to file system due to error ", str(exc))
                        else:
                            print("Create cache ", resource_path)
            return result
        return wrapped
    return wrapper

def identify_request(request: web.Request) -> str:
    url = request.match_info.get("url")
    id = hashlib.md5(url.encode())
    return id.hexdigest()

@cache_request(id_cb=identify_request)
async def cache_handler(request: web.Request):
    protocol = request.match_info.get("protocol")
    url = request.match_info.get("url")
    print(f"{protocol=}, {url=}")
    
    response = await get_proxy_request_stream(request, protocol + "://" + url)
    
    if response is not None:
        return response

    return web.FileResponse(
        headers={"Cache-Control": "max-age=6000, immutable"},
        path="/opt/image.svg",
    )