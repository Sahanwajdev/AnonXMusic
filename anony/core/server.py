import os
from aiohttp import web
from anony import logger


async def health_check(request):
    return web.Response(
        text="<html><body><h1>AnonXMusic Bot is Online & Running!</h1></body></html>",
        content_type="text/html",
        status=200,
    )


async def start_web_server():
    port = int(os.getenv("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    try:
        await site.start()
        logger.info(f"Web health server started on port {port} (0.0.0.0:{port})")
    except Exception as e:
        logger.warning(f"Could not start web server on port {port}: {e}")
