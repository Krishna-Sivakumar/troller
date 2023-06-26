import discord
import re
from random import randint
from tatsu import parse
import json
from discord.ext import tasks


class TaskClient(discord.Client):
    async def setup_hook(self):
        clear_overwrite.start()


intents = discord.Intents.default()
intents.message_content = True
client = TaskClient(intents=intents)


class InvalidCommandException(Exception):
    pass


HELP_TEXT = '''
Troller is Troller, I respond to commands:
`!troll (dice text)`: Troller rolls dice
`!register (or) !put (command name) / (dice text)`: Troller stores dice command for later
`!command (or) !use (command name)`: Troller runs stored command
`!commands`: Troller blurts all the commands Troller remembers

Troller recognizes dices like this:
`!troll 1d8+5`: Troller rolls dice with modifiers
`!troll adv (1d20+7)`: Troller rolls dice with advantage
`!troll disadv (1d20+3)`: Troller rolls dice with disadvantage
`!troll 1d6+10,1d8+5`: Troller rolls multiple sets of dice
`!register sneak attack montana / 1d4+3d6`: Troller stores "sneak attack montana" for later
`!command sneak attack montana`: Troller runs the command "sneak attack montana"
'''

GRAMMAR = '''
    @@grammar::CALC


    start = expression $ ;

    expression
        =
        | expression ',' expression
        | expression '+' dexpr
        | expression '-' dexpr
        | dexpr
        ;

    dexpr
        =
        | 'adv' dexpr
        | 'disadv' dexpr
        | dexpr '+' term
        | dexpr '-' term
        | term
        ;

    term
        =
        | 'adv' expression
        | 'disadv' expression
        | '(' expression ')'
        | dice
        | number
        ;

    number = /\d+/ ;
    dice = /\d+d\d+/ ;
'''


class StoredCommand:
    def __init__(self):
        pass

    def register(self, mention, command_name, dice_string):
        commands = self.get()
        commands[command_name] = (mention, dice_string)
        self.put(commands)

    def put(self, commands):
        with open("stored_commands.json", "w") as file:
            file.write(json.dumps(commands))

    def get(self):
        commands = {}
        try:
            commands = json.loads(open("stored_commands.json").read())
        except FileNotFoundError:
            with open("stored_commands.json", "w") as file:
                file.write(json.dumps({}))
        
        return commands


class DiceGroup:
    def __init__(self, dice):
        self.dices = [dice]

    def __add__(self, d):
        self.dices += d.dices
        return self

    def __sub__(self, d):
        for i in range(len(d.dices)):
            d.dices[i].results = [-r for r in d.dices[i].results]
            d.dices[i].constant = -d.dices[i].constant
        self.dices += d.dices
        return self
            

class Dice:
    def __init__(self, string, reroll=""):
        self.constant = 0
        self.reroll = reroll
        self.inter = None
        if "d" not in string:
            self.constant = int(string)
            self.count = 0
            self.dice = 0
        else:
            count, dice = map(int, string.split("d"))
            self.count = count
            self.dice = dice
        self.roll()

    def roll(self):
        self.results = []
        if self.reroll == "adv":
            roll_one = [randint(1, self.dice) for _ in range(self.count)]
            roll_two = [randint(1, self.dice) for _ in range(self.count)]
            self.inter = [roll_one, roll_two]
            if sum(roll_one) > sum(roll_two):
                self.results = roll_one
            else:
                self.results = roll_two
        elif self.reroll == "disadv":
            roll_one = [randint(1, self.dice) for _ in range(self.count)]
            roll_two = [randint(1, self.dice) for _ in range(self.count)]
            self.inter = [roll_one, roll_two]
            if sum(roll_one) < sum(roll_two):
                self.results = roll_one
            else:
                self.results = roll_two
        else:
            self.results = [randint(1, self.dice) for _ in range(self.count)]

    @property
    def sum(self):
        return sum([*self.results, self.constant])

    def __add__(self, d):
        return DiceGroup(self) + DiceGroup(d)

    def __sub__(self, d):
        d.results = [-r for r in d.results]
        return DiceGroup(self) - DiceGroup(d)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        def highlight(roll):
            if roll == self.dice:
                return f"**{roll}**"
            elif roll == 1:
                return f"**{roll}**"
            else:
                return str(roll)
        if self.constant != 0:
            return f"({self.constant})"
        result = "(" + ",".join(map(highlight, self.results)) + ")"
        if not self.reroll == "":
            inter_one = ",".join(map(highlight, self.inter[0]))
            inter_two = ",".join(map(highlight, self.inter[1]))
            inter_one = f"({inter_one})" if len(self.inter[0]) > 1 else inter_one
            inter_two = f"({inter_two})" if len(self.inter[1]) > 1 else inter_two
            return f"{self.reroll} {self.count}d{self.dice}({inter_one},{inter_two})->{result}"
        return f"{self.count}d{self.dice}{result}"


def compute(expr, reroll=""):
    if len(expr) == 3 and expr[1] == ",":
        lterm = compute(expr[0], reroll)
        rterm = compute(expr[2], reroll)
        return [lterm, *rterm] if type(rterm) == list else [lterm, rterm]
    elif len(expr) == 3 and expr[1] == "+":
        lterm = compute(expr[0], reroll)
        rterm = compute(expr[2], reroll)
        return lterm + rterm
    elif len(expr) == 3 and expr[1] == "-":
        lterm = compute(expr[0], reroll)
        rterm = compute(expr[2], reroll)
        return lterm - rterm
    elif expr[0] == "(" and expr[-1] == ")":
        return compute(expr[1:-1][0], reroll)
    elif expr[0] == "adv":
        return compute(expr[1], "adv")
    elif expr[0] == "disadv":
        return compute(expr[1], "disadv")
    else:
        return DiceGroup(Dice(expr, reroll))


def handle_dice(command):
    try:
        expr = parse(GRAMMAR, command)
        dice_groups = compute(expr)
        roll_response = ""
        if type(dice_groups) == DiceGroup:
            group = dice_groups
            # render result of each dice roll with str(), change if necessary in the future
            roll_response += " + ".join(map(str, group.dices))
            roll_response += " = "
            roll_response += f"__{sum([d.sum for d in group.dices])}__"
            roll_response += "\n"
        else:
            for idx, group in enumerate(dice_groups):
                roll_response += f"**Roll {idx+1}**:\n"
                roll_response += " + ".join(map(str, group.dices)) + " = " + f"__{sum([d.sum for d in group.dices])}__"
                roll_response += "\n"
        return roll_response
        
    except Exception as e:
        print(e)
        raise InvalidCommandException()


overwrite_command, overwrite_message = None, None
SCHandle = StoredCommand()


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@tasks.loop(seconds=30)
async def clear_overwrite():
    global overwrite_message, overwrite_command
    overwrite_message, overwrite_command = None, None
            

@client.event
async def on_message(message):
    global overwrite_command, overwrite_message

    if message.author == client.user:
        return

    query = message.content.lower().split(" ")
    if query[0] == "!troll" or query[0] == "!t":
        try:
            roll_response = handle_dice(" ".join(query[1:]))
            await message.channel.send(roll_response, reference=message)
        except InvalidCommandException:
            await message.channel.send("Invalid command; Look at help for more information", reference=message)

    elif query[0] == "!help":
        await message.channel.send(HELP_TEXT)

    elif query[0] == "!register" or query[0] == "!put":
        try:
            command_name, dice_string = " ".join(query[1:]).split("/")
            command_name = command_name.strip()
            dice_string = dice_string.strip()

            if len(command_name) <= 1:
                await message.channel.send("Troller can't rememebr something that short >:(", reference=message)

            handle_dice(dice_string)
            commands = SCHandle.get()
            if command_name in commands:
                # add reaction based confirmation to overwrite here later
                overwrite_message = await message.channel.send("Please react to this message if you want to overwrite the existing command")
                overwrite_command = query[1:]
            else:
                SCHandle.register(message.author.mention, command_name.lower(), dice_string)
                await message.channel.send(f"Stored command **{command_name}** for later", reference=message)
        except ValueError as e:
            print(e)
            await message.channel.send("Invalid command; Look at help for more information", reference=message)
        except InvalidCommandException:
            await message.channel.send("Cannot register invalid command; Look at help for more information", reference=message)

    elif query[0] == "!command" or query[0] == "!use":
        try:
            command_name = " ".join(query[1:]).lower()
            commands = SCHandle.get()
            if command_name in commands:
                _, dice_string = commands[command_name]
                roll_response = f"Rolling **{command_name}**:\n"
                roll_response += handle_dice(dice_string)
                await message.channel.send(roll_response, reference=message)
            else:
                await message.channel.send("Troller can't find command or Troller forgot :(", reference=message)
        except InvalidCommandException:
            await message.channel.send("Invalid command; Look at help for more information", reference=message)

    elif query[0] == "!del":
        try:
            command_name = " ".join(query[1:]).lower()
            commands = SCHandle.get()
            if command_name in commands:
                del commands[command_name]
                SCHandle.put(commands)
                await message.channel.send(f"Troller forgot **{command_name}** :)", reference=message)
            else:
                await message.channel.send("Troller can't forget a command Troller doesn't know :(", reference=message)
        except InvalidCommandException:
            await message.channel.send("Invalid command; Look at help for more information", reference=message)

    elif query[0] == "!commands":
        try:
            commands = SCHandle.get()
            response_text = "Command list:\n"
            for command_name in commands:
                _, dice_string = commands[command_name]
                response_text += f"**{command_name}**: {dice_string}\n"
            await message.channel.send(response_text, reference=message)
        except InvalidCommandException:
            await message.channel.send("Invalid command; Look at help for more information", reference=message)


@client.event
async def on_raw_reaction_add(payload):
    global overwrite_command, overwrite_message
    if overwrite_message is None:
        return
    if payload.message_id == overwrite_message.id:
        command_name, dice_string = overwrite_command[0], " ".join(overwrite_command[2:])
        command_name = command_name.strip()
        dice_string = dice_string.strip()
        SCHandle.register(None, command_name.lower(), dice_string)
        await overwrite_message.channel.send(f"Overwrote command **{command_name}**")


if __name__ == '__main__':
    client.run(open("token.txt").read())

