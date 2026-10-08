# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch

from anony import logger
from anony.helpers import Track, utils
from config import Config

config = Config()


class DummyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"
        self.warned = False
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )

    def get_cookies(self):
        if not self.checked:
            for file in os.listdir(self.cookie_dir):
                if file.endswith(".txt"):
                    self.cookies.append(f"{self.cookie_dir}/{file}")
            self.checked = True
        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies are missing; downloads might fail.")
            return None
        return random.choice(self.cookies)

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        async with aiohttp.ClientSession() as session:
            for url in urls:
                name = url.split("/")[-1]
                link = "https://batbin.me/raw/" + name
                async with session.get(link) as resp:
                    resp.raise_for_status()
                    with open(f"{self.cookie_dir}/{name}.txt", "wb") as fw:
                        fw.write(await resp.read())
        logger.info(f"Cookies saved in {self.cookie_dir}.")

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
            if results and results.get("result"):
                data = results["result"][0]
                dur_str = data.get("duration", "00:00")
                return Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=dur_str,
                    duration_sec=utils.to_seconds(dur_str),
                    message_id=m_id,
                    title=data.get("title", "")[:25],
                    thumbnail=data.get("thumbnails", [{}])[-1].get("url", "").split("?")[0],
                    url=data.get("link", f"https://www.youtube.com/watch?v={data.get('id')}"),
                    view_count=data.get("viewCount", {}).get("short", ""),
                    video=video,
                )
        except Exception as ex:
            logger.warning(f"VideosSearch error: {ex}")

        if getattr(config, "LYRA_API_URL", None):
            try:
                timeout = aiohttp.ClientTimeout(total=8)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    api_url = f"{config.LYRA_API_URL}/api/v1/search"
                    async with session.get(api_url, params={"query": query, "limit": 1}) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            results = data.get("results", [])
                            if results:
                                res = results[0]
                                dur_str = str(res.get("duration", "00:00"))
                                return Track(
                                    id=res.get("id"),
                                    channel_name=res.get("channel", ""),
                                    duration=dur_str,
                                    duration_sec=utils.to_seconds(dur_str),
                                    message_id=m_id,
                                    title=res.get("title", "")[:25],
                                    thumbnail=res.get("thumbnail", "").split("?")[0],
                                    url=res.get("url", f"https://www.youtube.com/watch?v={res.get('id')}"),
                                    view_count=str(res.get("views", "")),
                                    video=video,
                                )
            except Exception as ex:
                logger.warning(f"Lyra search fallback error: {ex}")

        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track | None]:
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist["videos"][:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")),
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails")[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception:
            pass
        return tracks

    async def download(self, video_id: str, video: bool = False) -> str | None:
        url = self.base + video_id
        cookie = self.get_cookies()

        if video:
            target_file = f"downloads/{video_id}_video.mp4"
            if Path(target_file).exists() and Path(target_file).stat().st_size > 1024:
                return target_file

            ydl_opts = {
                "outtmpl": f"downloads/{video_id}_video.%(ext)s",
                "quiet": True,
                "noplaylist": True,
                "geo_bypass": True,
                "no_warnings": True,
                "overwrites": False,
                "logger": DummyLogger(),
                "nocheckcertificate": True,
                "cookiefile": cookie,
                "remote_components": ["ejs:github"],
                "format": "(bestvideo[height<=?720][width<=?1280]+bestaudio)/best[height<=?720]/best",
                "merge_output_format": "mp4",
            }

            def _download_video():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        ydl.download([url])
                    except Exception as ex:
                        logger.warning(f"Video download failed: {ex}")
                        return None
                if Path(target_file).exists() and Path(target_file).stat().st_size > 1024:
                    return target_file
                for f in Path("downloads").glob(f"{video_id}_video.*"):
                    if f.is_file() and f.stat().st_size > 1024:
                        return str(f).replace("\\", "/")
                return None

            return await asyncio.to_thread(_download_video)

        else:
            target_webm = f"downloads/{video_id}_audio.webm"
            target_mp4 = f"downloads/{video_id}_audio.mp4"
            target_m4a = f"downloads/{video_id}_audio.m4a"

            for t in [target_webm, target_mp4, target_m4a]:
                if Path(t).exists() and Path(t).stat().st_size > 1024:
                    return t

            ydl_opts = {
                "outtmpl": f"downloads/{video_id}_audio.%(ext)s",
                "quiet": True,
                "noplaylist": True,
                "geo_bypass": True,
                "no_warnings": True,
                "overwrites": False,
                "logger": DummyLogger(),
                "nocheckcertificate": True,
                "cookiefile": cookie,
                "remote_components": ["ejs:github"],
                "format": "bestaudio[ext=webm][acodec=opus]/bestaudio/best",
            }

            def _download_audio():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        ydl.download([url])
                    except Exception as ex:
                        logger.warning(f"Audio yt-dlp download failed: {ex}")
                        return None
                for t in [target_webm, target_mp4, target_m4a]:
                    if Path(t).exists() and Path(t).stat().st_size > 1024:
                        return t
                for f in Path("downloads").glob(f"{video_id}_audio.*"):
                    if f.is_file() and f.stat().st_size > 1024:
                        return str(f).replace("\\", "/")
                return None

            res = await asyncio.to_thread(_download_audio)
            if res:
                return res

            # Backup fallback via Lyra API
            if getattr(config, "LYRA_API_URL", None) and getattr(config, "LYRA_API_KEY", None):
                try:
                    logger.info("Attempting Lyra API fallback for audio...")
                    timeout = aiohttp.ClientTimeout(total=20)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        stream_api = f"{config.LYRA_API_URL}/api/v1/stream"
                        params = {"id": video_id, "quality": "best", "api_key": config.LYRA_API_KEY}
                        async with session.get(stream_api, params=params) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                stream_url = data.get("stream_url") or data.get("proxy_stream_url")
                                if stream_url:
                                    async with session.get(stream_url) as dl_resp:
                                        if dl_resp.status == 200:
                                            with open(target_mp4, "wb") as fw:
                                                async for chunk in dl_resp.content.iter_chunked(128 * 1024):
                                                    if chunk:
                                                        fw.write(chunk)
                                            if Path(target_mp4).exists() and Path(target_mp4).stat().st_size > 1024:
                                                logger.info(f"Downloaded via Lyra API fallback: {target_mp4}")
                                                return target_mp4
                except Exception as ex:
                    logger.warning(f"Lyra API fallback failed: {ex}")

            return None


