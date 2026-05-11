"""音乐工具管理器.

负责音乐工具的Initialization、Configuration和MCP工具Register
"""

from typing import Any, Dict

from src.utils.logging_config import get_logger

from .music_player import get_music_player_instance

logger = get_logger(__name__)


class MusicToolsManager:
    """
    音乐工具管理器.
    """

    def __init__(self):
        """
        Initialization音乐工具管理器.
        """
        self._initialized = False
        self._music_player = None
        logger.info("[MusicManager] 音乐工具管理器Initialization")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Initialization并Register所有音乐工具.
        """
        try:
            logger.info("[MusicManager] 开始Register音乐工具")

            # Get音乐播放器单例实例
            self._music_player = get_music_player_instance()

            # RegisterSearch并播放工具
            self._register_search_and_play_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register暂停工具
            self._register_pause_tool(add_tool, PropertyList)

            # RegisterResume工具
            self._register_resume_tool(add_tool, PropertyList)

            # RegisterStop工具
            self._register_stop_tool(add_tool, PropertyList)

            # Register跳转工具
            self._register_seek_tool(add_tool, PropertyList, Property, PropertyType)

            # RegisterGet歌词工具
            self._register_get_lyrics_tool(add_tool, PropertyList)

            # RegisterGet本地歌单工具
            self._register_get_local_playlist_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            self._initialized = True
            logger.info("[MusicManager] 音乐工具RegisterComplete")

        except Exception as e:
            logger.error(f"[MusicManager] 音乐工具RegisterFailure: {e}", exc_info=True)
            raise

    def _register_search_and_play_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        RegisterSearch并播放工具.
        """

        async def search_and_play_wrapper(args: Dict[str, Any]) -> str:
            song_name = args.get("song_name", "")
            result = await self._music_player.search_and_play(song_name)
            return result.get("message", "Search播放Complete")

        search_props = PropertyList([Property("song_name", PropertyType.STRING)])

        add_tool(
            (
                "music_player.search_and_play",
                "Search并播放指定的歌曲。根据歌名在线Search歌曲并自动开始播放。"
                "如果已有音乐在播放，会自动Stop当前音乐并播放新歌曲。"
                "用于播放用户请求的特定歌曲，例如'播放周杰伦的稻香'、'听一下孤勇者'。",
                search_props,
                search_and_play_wrapper,
            )
        )
        logger.debug("[MusicManager] RegisterSearch播放工具Success")

    def _register_pause_tool(self, add_tool, PropertyList):
        """
        Register暂停工具.
        """

        async def pause_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.pause()
            return result.get("message", "已暂停")

        add_tool(
            (
                "music_player.pause",
                "暂停当前正在播放的音乐。调用此工具会立即Stop音乐播放，保持当前位置。"
                "用户可以稍后调用 resume Resume播放。"
                "注意：不要在 TTS 说话时主动调用此工具，TTS 会自动临时暂停音乐。"
                "只有当用户明确说'暂停'、'暂停音乐'、'先停一下'等时才调用。",
                PropertyList(),
                pause_wrapper,
            )
        )
        logger.debug("[MusicManager] Register暂停工具Success")

    def _register_resume_tool(self, add_tool, PropertyList):
        """
        RegisterResume工具.
        """

        async def resume_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.resume()
            return result.get("message", "已Resume播放")

        add_tool(
            (
                "music_player.resume",
                "Resume播放之前暂停的音乐。从暂停的位置继续播放。"
                "只有当音乐处于'已暂停'状态（用户主动暂停）时才调用此工具。"
                "如果音乐只是被 TTS 临时打断，TTS 结束后会自动Resume，无需调用此工具。",
                PropertyList(),
                resume_wrapper,
            )
        )
        logger.debug("[MusicManager] RegisterResume工具Success")

    def _register_stop_tool(self, add_tool, PropertyList):
        """
        RegisterStop工具.
        """

        async def stop_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.stop()
            return result.get("message", "Stop播放Complete")

        add_tool(
            (
                "music_player.stop",
                "完全Stop音乐播放。Stop当前歌曲并重置播放位置到开头。"
                "与 pause（暂停）的区别：stop 是完全结束播放，pause 是临时暂停。"
                "用于用户说'Stop音乐'、'Close音乐'、'别放了'等明确要求结束播放的场景。",
                PropertyList(),
                stop_wrapper,
            )
        )
        logger.debug("[MusicManager] RegisterStop工具Success")

    def _register_seek_tool(self, add_tool, PropertyList, Property, PropertyType):
        """
        Register跳转工具.
        """

        async def seek_wrapper(args: Dict[str, Any]) -> str:
            position = args.get("position", 0)
            result = await self._music_player.seek(float(position))
            return result.get("message", "跳转Complete")

        seek_props = PropertyList(
            [Property("position", PropertyType.INTEGER, min_value=0)]
        )

        add_tool(
            (
                "music_player.seek",
                "跳转到歌曲的指定位置。position 参数单位为秒（从开头计算）。"
                "用于用户要求'快进到2分钟'、'跳到副歌部分'、'回到开头'、'跳转30%'、'跳到30秒'等场景。"
                "注意：如果用户说'快进30秒'，需要先Get当前位置，再加上30秒。",
                seek_props,
                seek_wrapper,
            )
        )
        logger.debug("[MusicManager] Register跳转工具Success")

    def _register_get_lyrics_tool(self, add_tool, PropertyList):
        """
        RegisterGet歌词工具.
        """

        async def get_lyrics_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.get_lyrics()
            if result.get("status") == "success":
                lyrics = result.get("lyrics", [])
                return "歌词内容:\n" + "\n".join(lyrics)
            else:
                return result.get("message", "Get歌词Failure")

        add_tool(
            (
                "music_player.get_lyrics",
                "Get当前播放歌曲的歌词。返回完整歌词及时间戳。"
                "用于用户询问'这首歌的歌词是什么'、'帮我看看歌词'、'歌词里唱的什么'等场景。",
                PropertyList(),
                get_lyrics_wrapper,
            )
        )
        logger.debug("[MusicManager] RegisterGet歌词工具Success")

    def _register_get_local_playlist_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        RegisterGet本地歌单工具.
        """

        async def get_local_playlist_wrapper(args: Dict[str, Any]) -> str:
            force_refresh = args.get("force_refresh", False)
            result = await self._music_player.get_local_playlist(force_refresh)

            if result.get("status") == "success":
                playlist = result.get("playlist", [])
                total_count = result.get("total_count", 0)

                if playlist:
                    playlist_text = f"本地音乐歌单 (共{total_count}首):\n"
                    playlist_text += "\n".join(playlist)
                    return playlist_text
                else:
                    return "本地缓存中没有音乐文件"
            else:
                return result.get("message", "Get本地歌单Failure")

        refresh_props = PropertyList(
            [Property("force_refresh", PropertyType.BOOLEAN, default_value=False)]
        )

        add_tool(
            (
                "music_player.get_local_playlist",
                "Get本地音乐歌单。显示所有已下载并缓存的歌曲。"
                "返回格式：'歌名 - 歌手'，例如'菊花台 - 周杰伦'。"
                "用于用户询问'我有哪些歌'、'本地歌曲列表'、'缓存了什么音乐'等场景。"
                "注意：播放列表中的歌曲时，只需使用歌名调用 search_and_play，"
                "例如列表显示'菊花台 - 周杰伦'，调用 search_and_play(song_name='菊花台') 即可。",
                refresh_props,
                get_local_playlist_wrapper,
            )
        )
        logger.debug("[MusicManager] RegisterGet本地歌单工具Success")

    def _format_time(self, seconds: float) -> str:
        """
        将秒数格式化为 mm:ss 格式.
        """
        minutes = int(seconds) // 60
        seconds = int(seconds) % 60
        return f"{minutes:02d}:{seconds:02d}"

    def is_initialized(self) -> bool:
        """
        检查管理器是否已Initialization.
        """
        return self._initialized


# 全局管理器实例
_music_tools_manager = None


def get_music_tools_manager() -> MusicToolsManager:
    """
    Get音乐工具管理器单例.
    """
    global _music_tools_manager
    if _music_tools_manager is None:
        _music_tools_manager = MusicToolsManager()
        logger.debug("[MusicManager] 创建音乐工具管理器实例")
    return _music_tools_manager
