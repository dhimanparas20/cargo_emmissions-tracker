from datetime import datetime


def get_timestamp():
    return datetime.now().timestamp()


def format_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
