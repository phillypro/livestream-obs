# app/services/discord_service.py
import discord
import asyncio
import threading
from app.config.globals import settings_manager # Import settings_manager

class DiscordBot:
    def __init__(self, token, socketio):
        self.token = token
        self.client = None
        self.socketio = socketio
        self.stop_event = threading.Event()
        self.loop = None
        self.last_message = None  # Track the last message for highlight functionality

        # Customize these IDs as needed or move them to config
        self.specific_user_id = 408163545830785024       # Example user ID
        self.specific_channel_id = 1148844776624496740   # Example channel ID

    async def shutdown(self):
        await self.client.close()
        if self.client.loop.is_running():
            self.client.loop.stop()
        await self.client.loop.close()

    def setup_discord_client(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.messages = True
        intents.reactions = True
        intents.voice_states = True  # For voice state updates
        intents.message_content = True

        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            print(f'[Discord Bot] Logged in as {client.user}')

        @client.event
        async def on_raw_reaction_add(payload):
            await self.handle_reaction(payload)

        @client.event
        async def on_message(message):
            await self.handle_new_message(message)

        @client.event
        async def on_voice_state_update(member, before, after):
            await self.handle_voice_state_update(member, before, after)

        return client

    async def handle_reaction(self, payload):
        # Check if the reaction is from a specific user in a specific channel
        if payload.user_id == self.specific_user_id and payload.channel_id == self.specific_channel_id:
            channel = self.client.get_channel(payload.channel_id)
            if channel:
                message = await channel.fetch_message(payload.message_id)
                if message:
                    await self.send_highlight_data(message)

    async def handle_new_message(self, message):
        # Only track messages in the specific channel
        if not message.author.bot and message.channel.id == self.specific_channel_id:
            self.last_message = message  # Store the last message
            await self.send_save_data(message)

    async def handle_voice_state_update(self, member, before, after):
        # Check if the user's voice state changed
        if before.channel == after.channel:
            # Hand raised: requested_to_speak_at changes from None to not None
            if before.requested_to_speak_at is None and after.requested_to_speak_at is not None:
                data = {
                    "action": "hand_raised",
                    "name": member.name,
                    "profileImageUrl": str(member.avatar.url) if member.avatar else ""
                }
                print(f'{member.name} raised their hand in {after.channel.name}.')
                self.socketio.emit('voice_state_update', data)

            # Hand lowered: requested_to_speak_at changes from not None to None
            elif before.requested_to_speak_at is not None and after.requested_to_speak_at is None:
                data = {
                    "action": "hand_lowered",
                    "name": member.name,
                    "profileImageUrl": str(member.avatar.url) if member.avatar else ""
                }
                print(f'{member.name} lowered their hand in {after.channel.name}.')
                self.socketio.emit('voice_state_update', data)

    def get_last_message_data(self):
        if self.last_message:
            author_nick = self.last_message.author.display_name
            author_profile_image = str(self.last_message.author.avatar.url) if self.last_message.author.avatar else ""

            return {
                "message": self.last_message.content,
                "from": author_nick,
                "timestamp": str(self.last_message.created_at),
                "profileImageUrl": author_profile_image,
                "show": True
            }
        return None

    async def send_highlight_data(self, message):
        author_nick = message.author.display_name
        author_profile_image = str(message.author.avatar.url) if message.author.avatar else ""

        data = {
            "message": message.content,
            "from": author_nick,
            "timestamp": str(message.created_at),
            "profileImageUrl": author_profile_image,
            "show": True
        }
        print("[Discord Bot] Sending highlight data:", data)
        self.socketio.emit('highlight_data', data)

    async def send_save_data(self, message):
        author_nick = message.author.display_name
        author_profile_image = str(message.author.avatar.url) if message.author.avatar else ""

        data = {
            "message": message.content,
            "from": author_nick,
            "timestamp": str(message.created_at),
            "profileImageUrl": author_profile_image,
            "show": True
        }
        print("[Discord Bot] Sending save data:", data)
        self.socketio.emit('save_comment', data)

    async def start_client(self):
        self.client = self.setup_discord_client()

        # Additional events can be redefined here if needed

        try:
            await self.client.start(self.token)
        except Exception as e:
            print(f"[Discord Bot] Error: {e}")
        finally:
            if not self.stop_event.is_set():
                await self.client.close()

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.start_client())

    def stop(self):
        self.stop_event.set()
        if self.client and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.client.close(), self.loop)
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)


def prepare_message(message, activity_type):
    # Stub implementation. 
    # Later, integrate with the actual Discord bot code to send a message.
    print(f"[Discord] Preparing message: {message} (type: {activity_type})")
