def usage_tokens(message) -> int:
    usage = getattr(message, "usage_metadata", None)
    if not usage:
        return 0
    return usage.get("total_tokens", 0) or 0
