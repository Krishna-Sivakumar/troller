from client import troller_client
from os import environ

if __name__ == "__main__":
    token = environ["DISCORD_TOKEN"]
    troller_client.run(token)

