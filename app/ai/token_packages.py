TOKEN_PACKAGES = {
    "starter": {"tokens": 50000, "price_id": "price_1UIABwGaHOweIXJbBjmmfutp", "amount": 5},
    "standard": {"tokens": 150000, "price_id": "price_1UIACTGaHOweIXJbZuQ9JMqQ", "amount": 9},
    "pro": {"tokens": 500000, "price_id": "price_1UIACtGaHOweIXJbATXrzpHD", "amount": 20},
}


def get_package(key: str) -> dict | None:
    return TOKEN_PACKAGES.get(key)