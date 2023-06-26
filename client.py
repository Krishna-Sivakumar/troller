import discord
from discord.ext import tasks
from dice import StoredCommand, InvalidCommandException, handle_dice, HELP_TEXT

intents = discord.Intents.default()
intents.message_content = True

class TrollerClient(discord.Client):

    overwrite_command, overwrite_message = None, None
    SCHandle = StoredCommand()

    @tasks.loop(seconds=30)
    async def clear_overwrite(self):
        self.overwrite_message = None
        self.overwrite_command = None


    async def setup_hook(self):
        self.clear_overwrite.start()


    async def on_ready(self):
        print(f"We have logged in as {self.user}")


    async def on_message(self, message):
        if message.author == self.user:
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
                commands = self.SCHandle.get()
                if command_name in commands:
                    self.overwrite_message = await message.channel.send("Please react to this message if you want to overwrite the existing command")
                    self.overwrite_command = query
                else:
                    self.SCHandle.register(message.author.mention, command_name.lower(), dice_string)
                    await message.channel.send(f"Stored command **{command_name}** for later", reference=message)
            except ValueError as e:
                await message.channel.send("Invalid command; Look at help for more information", reference=message)
            except InvalidCommandException:
                await message.channel.send("Cannot register invalid command; Look at help for more information", reference=message)

        elif query[0] == "!command" or query[0] == "!use":
            try:
                command_name = " ".join(query[1:]).lower()
                commands = self.SCHandle.get()
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
                commands = self.SCHandle.get()
                if command_name in commands:
                    del commands[command_name]
                    self.SCHandle.put(commands)
                    await message.channel.send(f"Troller forgot **{command_name}** :)", reference=message)
                else:
                    await message.channel.send("Troller can't forget a command Troller doesn't know :(", reference=message)
            except InvalidCommandException:
                await message.channel.send("Invalid command; Look at help for more information", reference=message)

        elif query[0] == "!commands":
            try:
                commands = self.SCHandle.get()
                response_text = "Command list:\n"
                for command_name in commands:
                    _, dice_string = commands[command_name]
                    response_text += f"**{command_name}**: {dice_string}\n"
                await message.channel.send(response_text, reference=message)
            except InvalidCommandException:
                await message.channel.send("Invalid command; Look at help for more information", reference=message)


    async def on_raw_reaction_add(self, payload):
        if self.overwrite_message is None:
            return
        if payload.message_id == self.overwrite_message.id:
            command_name, dice_string = " ".join(self.overwrite_command[1:]).split("/")
            command_name = command_name.strip()
            dice_string = dice_string.strip()
            self.SCHandle.register(None, command_name.lower(), dice_string)
            await self.overwrite_message.channel.send(f"Overwrote command **{command_name}**")


troller_client = TrollerClient(intents=intents)
