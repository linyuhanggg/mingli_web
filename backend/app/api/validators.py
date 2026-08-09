from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def validate_iana_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as error:
        raise ValueError("unknown IANA timezone name") from error
    return value
