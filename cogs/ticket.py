import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import io
import asyncio
import config

# Server-specific IDs
MAIN_GUILD_ID = 1438946135871062199
STAFF_ROLE_ID = 1438950739664830534  # Staff role
TICKET_CATEGORY_NAME = "Tickets"
TICKET_PANEL_NAME = "ticket-panel"
TRANSCRIPT_CHANNEL_NAME = "ticket-transcripts"

# Track active tickets per user
active_tickets = {}

# ----------------- Views -----------------

class TicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Report Ticket", style=discord.ButtonStyle.red, custom_id="open_report_ticket")
    async def open_report(self, interaction: discord.Interaction, button: Button):
        await self.create_ticket(interaction, "report")

    @discord.ui.button(label="Open Order Ticket", style=discord.ButtonStyle.green, custom_id="open_order_ticket")
    async def open_order(self, interaction: discord.Interaction, button: Button):
        await self.create_ticket(interaction, "order")

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        await interaction.response.send_modal(TicketIssueModal(ticket_type))


class TicketIssueModal(Modal, title="Describe Your Issue"):
    def __init__(self, ticket_type):
        super().__init__()
        self.ticket_type = ticket_type

        self.issue = TextInput(
            label="What is the issue?",
            placeholder="Describe your problem in detail...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )
        self.add_item(self.issue)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        # Find or create ticket category
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        # Prevent multiple tickets
        if user.id in active_tickets:
            await interaction.response.send_message("You already have an open ticket!", ephemeral=True)
            return

        # Overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True)
        }

        # Create ticket channel
        channel = await guild.create_text_channel(
            name=f"{self.ticket_type}-ticket-{user.name}-{user.discriminator}",
            category=category,
            overwrites=overwrites,
            topic=f"{self.ticket_type.capitalize()} ticket for {user} (ID: {user.id})"
        )

        active_tickets[user.id] = channel.id

        await channel.send(f"**New {self.ticket_type.capitalize()} Ticket**\n**User:** {user.mention}\n**Issue:** {self.issue.value}")
        await interaction.response.send_message(f"Your {self.ticket_type} ticket has been created: {channel.mention}", ephemeral=True)


class ClaimTicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.blurple, custom_id="claim_ticket_button")
    async def claim(self, interaction: discord.Interaction, button: Button):
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)
            return

        channel = interaction.channel
        if "Claimed by" in (channel.topic or ""):
            await interaction.response.send_message("This ticket is already claimed!", ephemeral=True)
            return

        overwrites = channel.overwrites
        for target, perms in list(overwrites.items()):
            if isinstance(target, discord.Member):
                perms.send_messages = False
                overwrites[target] = perms

        overwrites[interaction.user] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        await channel.edit(overwrites=overwrites)

        new_topic = f"{channel.topic} | Claimed by {interaction.user.name}"
        await channel.edit(topic=new_topic)

        await channel.send(f"🔒 Ticket has been claimed by {interaction.user.mention} and locked.")
        await interaction.response.send_message("You claimed this ticket.", ephemeral=True)


class CloseTicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        channel = interaction.channel
        guild = interaction.guild

        if not channel.category or channel.category.name != TICKET_CATEGORY_NAME:
            await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
            return

        await interaction.response.send_message("Closing ticket in 5 seconds...", ephemeral=True)

        # Find or create transcript channel
        log_channel = discord.utils.get(guild.text_channels, name=TRANSCRIPT_CHANNEL_NAME)
        if not log_channel:
            log_channel = await guild.create_text_channel(TRANSCRIPT_CHANNEL_NAME)

        # Create transcript
        transcript_text = f"Transcript for ticket: {channel.name}\n\n"
        messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
        for msg in messages:
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            transcript_text += f"[{timestamp}] {msg.author}: {msg.content}\n"

        await log_channel.send(file=discord.File(io.BytesIO(transcript_text.encode()), filename=f"{channel.name}.txt"))

        for uid, tid in list(active_tickets.items()):
            if tid == channel.id:
                del active_tickets[uid]
                break

        await channel.delete()


# ----------------- Cog -----------------

class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketButton())
        self.bot.add_view(ClaimTicketButton())
        self.bot.add_view(CloseTicketButton())
        await self.ensure_panel_channel()

    async def ensure_panel_channel(self):
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(MAIN_GUILD_ID)
        if not guild:
            print("Guild not found")
            return

        panel_channel = discord.utils.get(guild.text_channels, name=TICKET_PANEL_NAME)
        if not panel_channel:
            panel_channel = await guild.create_text_channel(TICKET_PANEL_NAME)

        embed = discord.Embed(
            title="Support Tickets",
            description="Click the button below to open a ticket.",
            color=discord.Color.blue()
        )
        await panel_channel.send(embed=embed, view=TicketButton())
        print(f"Ticket panel sent to channel: {panel_channel.name} ({panel_channel.id})")

    @commands.command(name="ticketpanel")
    @commands.has_permissions(administrator=True)
    async def ticketpanel(self, ctx):
        embed = discord.Embed(
            title="Support Tickets",
            description="Click the button below to open a ticket.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=TicketButton())


async def setup(bot):
    await bot.add_cog(TicketCog(bot))
