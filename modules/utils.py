import re
from datetime import datetime


# Normalize vehicle registration number
def normalise_registration_number(registration_number: str) -> str:
    # Remove spaces, hyphens, slashes, and commas, and convert to lowercase
    return re.sub(r"[\s\-/,]", "", registration_number.strip().casefold())


# Get current timestamp
def get_timestamp():
    return datetime.now().timestamp()


def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
