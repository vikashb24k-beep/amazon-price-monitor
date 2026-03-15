import random

PROXIES = [
    "http://proxy1:port",
    "http://proxy2:port"
]

def get_proxy():
    return random.choice(PROXIES)