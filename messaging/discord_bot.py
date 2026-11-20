import asyncio

import discord
from discord.ext import commands

from broker.alpaca_client import AlpacaClient
from config import ALPACA_API_KEY, ALPACA_BASE_URL, ALPACA_SECRET_KEY
from config import DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID
from trading_state import is_trading_enabled, set_trading_enabled


class TradingBotDiscord(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.channel = None
        self.is_ready = False
        self.event_loop = None
        self._register_commands()

    def _register_commands(self):
        async def require_control_permission(interaction: discord.Interaction) -> bool:
            if (
                isinstance(interaction.user, discord.Member)
                and interaction.user.guild_permissions.manage_guild
            ):
                return True
            await interaction.response.send_message(
                "You do not have permission to control trading.", ephemeral=True
            )
            return False

        @self.tree.command(name="start", description="Enable new trades")
        async def start_trading(interaction: discord.Interaction):
            if not await require_control_permission(interaction):
                return
            set_trading_enabled(True)
            await interaction.response.send_message("Trading enabled.", ephemeral=True)

        @self.tree.command(name="stop", description="Stop new trades while continuing sell checks")
        async def stop_trading(interaction: discord.Interaction):
            if not await require_control_permission(interaction):
                return
            set_trading_enabled(False)
            await interaction.response.send_message("Trading disabled; position monitoring remains active.", ephemeral=True)

        @self.tree.command(name="clear", description="Clear recent messages from this channel")
        async def clear_channel(interaction: discord.Interaction, amount: int = 10):
            if not (
                isinstance(interaction.user, discord.Member)
                and interaction.user.guild_permissions.manage_messages
            ):
                await interaction.response.send_message("You do not have permission to manage messages.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                deleted = await interaction.channel.purge(limit=max(1, min(amount, 100)))
                await interaction.followup.send(f"Cleared {len(deleted)} messages.", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("The bot cannot delete messages in this channel.", ephemeral=True)

        @self.tree.command(name="status", description="Show trading and market status")
        async def status(interaction: discord.Interaction):
            embed = discord.Embed(title="Trading Bot Status", color=0x2ECC71)
            embed.add_field(name="Trading", value="Active" if is_trading_enabled() else "Monitoring only")
            try:
                market_open = AlpacaClient(
                    ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL
                ).api.get_clock().is_open
                embed.add_field(name="Market", value="Open" if market_open else "Closed")
            except Exception:
                embed.add_field(name="Market", value="Unavailable")
            await interaction.response.send_message(embed=embed)

    async def on_ready(self):
        self.event_loop = asyncio.get_running_loop()
        self.channel = self.get_channel(DISCORD_CHANNEL_ID)
        if not self.channel:
            print(f"Discord channel {DISCORD_CHANNEL_ID} was not found")
            return
        await self.tree.sync()
        self.is_ready = True
        await self.channel.send(embed=self._create_embed("Trading bot connected"))

    async def start_bot(self):
        if DISCORD_BOT_TOKEN:
            await self.start(DISCORD_BOT_TOKEN)

    async def send_message(self, message: str) -> bool:
        if not self.is_ready or not self.channel:
            return False
        try:
            await asyncio.wait_for(self.channel.send(embed=self._create_embed(message)), timeout=10)
            return True
        except (asyncio.TimeoutError, discord.DiscordException) as exc:
            print(f"Discord message failed: {exc}")
            return False

    @staticmethod
    def _create_embed(message: str) -> discord.Embed:
        lowered = message.lower()
        if lowered.startswith("bought"):
            title, color = "Buy Order Executed", 0x2ECC71
        elif lowered.startswith("sold"):
            title, color = "Sell Order Executed", 0x3498DB
        elif "disabled" in lowered or "closed" in lowered:
            title, color = "Trading Update", 0xE67E22
        else:
            title, color = "Trading Bot", 0x5865F2
        return discord.Embed(title=title, description=message, color=color, timestamp=discord.utils.utcnow())


discord_bot = TradingBotDiscord()
