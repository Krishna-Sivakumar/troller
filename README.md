# Troller
A bot to roll your dice for DnD and more!

### Docker

There's a docker container that you can find on the releases tab.

Usage commands:
```
docker build -t troller troller-bot
docker run -e DISCORD_TOKEN=(cat discord_token.txt) troller-bot
```

### Setup Instructions

```shell
virutalenv .env
source .env/bin/activate # shell dependent, this works for bash
python3 -m pip install -r requirements.txt
```

set the `DISCORD_TOKEN` environment variable to authenticate your account.
I currently use a static token to log the bot in.

### Run the Bot

```shell
python main.py
```


#### Commands go as follows:
```
`!troll (dice text)`: Troller rolls dice
`!register (or) !put (command name) / (dice text)`: Troller stores dice command for later
`!command (or) !use (command name)`: Troller runs stored command
`!commands`: Troller lists out all the commands stored

Example dice formats:
`!troll 1d8+5`: 1d8 dice is rolled with a +5 modifier
`!troll adv (1d20+7)`: 1d20 dice is rolled with advantage along with a +7 modifier
`!troll disadv (1d20+3)`: 1d20 dice is rolled with disadvantage along with a +3 modifier
`!troll 1d6+10,1d8+5`: Multiple dice rolls are made in parallel
`!register sneak attack montana / 1d4+3d6`: Command "sneak attack montana" is stored for later
`!command sneak attack montana`: Troller runs the command "sneak attack montana"
```

