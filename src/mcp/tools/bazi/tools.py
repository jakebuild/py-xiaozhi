"""
八字命理MCP工具函数 提供给MCP服务器调用的异步工具函数。
"""

import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .bazi_calculator import get_bazi_calculator
from .engine import get_bazi_engine

logger = get_logger(__name__)


async def get_bazi_detail(args: Dict[str, Any]) -> str:
    """
    根据时间（公历或农历）、性别来Get八字信息。
    """
    try:
        solar_datetime = args.get("solar_datetime")
        lunar_datetime = args.get("lunar_datetime")
        gender = args.get("gender", 1)
        eight_char_provider_sect = args.get("eight_char_provider_sect", 2)

        if not solar_datetime and not lunar_datetime:
            return json.dumps(
                {
                    "success": False,
                    "message": "solar_datetime和lunar_datetime必须传且只传其中一个",
                },
                ensure_ascii=False,
            )

        calculator = get_bazi_calculator()
        result = calculator.build_bazi(
            solar_datetime=solar_datetime,
            lunar_datetime=lunar_datetime,
            gender=gender,
            eight_char_provider_sect=eight_char_provider_sect,
        )

        return json.dumps(
            {"success": True, "data": result.to_dict()}, ensure_ascii=False, indent=2
        )

    except Exception as e:
        logger.error(f"Get八字详情Failure: {e}")
        return json.dumps(
            {"success": False, "message": f"Get八字详情Failure: {str(e)}"},
            ensure_ascii=False,
        )


async def get_solar_times(args: Dict[str, Any]) -> str:
    """
    根据八字Get公历时间列表。
    """
    try:
        bazi = args.get("bazi")
        if not bazi:
            return json.dumps(
                {"success": False, "message": "八字参数不能为空"}, ensure_ascii=False
            )

        calculator = get_bazi_calculator()
        result = calculator.get_solar_times(bazi)

        return json.dumps(
            {"success": True, "data": {"可能时间": result, "总数": len(result)}},
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Get公历时间Failure: {e}")
        return json.dumps(
            {"success": False, "message": f"Get公历时间Failure: {str(e)}"},
            ensure_ascii=False,
        )


async def get_chinese_calendar(args: Dict[str, Any]) -> str:
    """
    Get指定公历时间（默认今天）的黄历信息。
    """
    try:
        solar_datetime = args.get("solar_datetime")

        engine = get_bazi_engine()

        # 如果提供了时间，Parse它；否则使用当前时间
        if solar_datetime:
            solar_time = engine.parse_solar_time(solar_datetime)
            result = engine.get_chinese_calendar(solar_time)
        else:
            result = engine.get_chinese_calendar()  # 使用当前时间

        return json.dumps(
            {"success": True, "data": result.to_dict()}, ensure_ascii=False, indent=2
        )

    except Exception as e:
        logger.error(f"Get黄历信息Failure: {e}")
        return json.dumps(
            {"success": False, "message": f"Get黄历信息Failure: {str(e)}"},
            ensure_ascii=False,
        )


async def build_bazi_from_lunar_datetime(args: Dict[str, Any]) -> str:
    """
    根据农历时间、性别来Get八字信息（已弃用，使用get_bazi_detail替代）。
    """
    try:
        lunar_datetime = args.get("lunar_datetime")
        gender = args.get("gender", 1)
        eight_char_provider_sect = args.get("eight_char_provider_sect", 2)

        if not lunar_datetime:
            return json.dumps(
                {"success": False, "message": "lunar_datetime参数不能为空"},
                ensure_ascii=False,
            )

        calculator = get_bazi_calculator()
        result = calculator.build_bazi(
            lunar_datetime=lunar_datetime,
            gender=gender,
            eight_char_provider_sect=eight_char_provider_sect,
        )

        return json.dumps(
            {
                "success": True,
                "message": "此方法已弃用，请使用get_bazi_detail",
                "data": result.to_dict(),
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"根据农历时间Get八字Failure: {e}")
        return json.dumps(
            {"success": False, "message": f"根据农历时间Get八字Failure: {str(e)}"},
            ensure_ascii=False,
        )


async def build_bazi_from_solar_datetime(args: Dict[str, Any]) -> str:
    """
    根据阳历时间、性别来Get八字信息（已弃用，使用get_bazi_detail替代）。
    """
    try:
        solar_datetime = args.get("solar_datetime")
        gender = args.get("gender", 1)
        eight_char_provider_sect = args.get("eight_char_provider_sect", 2)

        if not solar_datetime:
            return json.dumps(
                {"success": False, "message": "solar_datetime参数不能为空"},
                ensure_ascii=False,
            )

        calculator = get_bazi_calculator()
        result = calculator.build_bazi(
            solar_datetime=solar_datetime,
            gender=gender,
            eight_char_provider_sect=eight_char_provider_sect,
        )

        return json.dumps(
            {
                "success": True,
                "message": "此方法已弃用，请使用get_bazi_detail",
                "data": result.to_dict(),
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"根据阳历时间Get八字Failure: {e}")
        return json.dumps(
            {"success": False, "message": f"根据阳历时间Get八字Failure: {str(e)}"},
            ensure_ascii=False,
        )
