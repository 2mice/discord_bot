import discord
from discord.ext import commands
from discord.ui import View, Button
import config

TICKET_CATEGORY_ID = config.TICKET_CATEGORY_ID
STAFF_ROLE_ID = config.STAFF_ROLE_ID
TRANSCRIPT_LOG_CHANNEL_ID = config.TRANSCRIPT_LOG_CHANNEL_ID
TICKET_PANEL_CHANNEL_ID = config.TICKET_PANEL_CHANNEL_ID

# Track active tickets per user
active_tickets = {}

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
        # Show modal instead of creating immediately
        await interaction.response.send_modal(TicketIssueModal(ticket_type))
(self, interaction: discord.Interaction, ticket_type: str):
        guild = interaction.guild
        user = interaction.user

        # Check if user already has a ticket
        if user.id in active_tickets:
            await interaction.response.send_message("You already have an open ticket!", ephemeral=True)
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("Ticket category not found. Contact staff.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"{ticket_type}-ticket-{user.name}-{user.discriminator}",
            category=category,
            overwrites=overwrites,
            topic=f"{ticket_type.capitalize()} ticket for {user} (ID: {user.id})"
        )

        active_tickets[user.id] = channel.id

        await channel.send(f"Hello {user.mention}, this is your **{ticket_type} ticket**. Please describe your issue.")
        await interaction.response.send_message(f"Your {ticket_type} ticket has been created: {channel.mention}", ephemeral=True)


class TicketIssueModal(discord.ui.Modal, title="Describe Your Issue"):
    def __init__(self, ticket_type):
        super().__init__()
        self.ticket_type = ticket_type

        self.issue = discord.ui.TextInput(
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

        # Block if already has a ticket
        if user.id in active_tickets:
            await interaction.response.send_message("You already have an open ticket!", ephemeral=True)
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("Ticket category not found.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"{self.ticket_type}-ticket-{user.name}-{user.discriminator}",
            category=category,
            overwrites=overwrites,
            topic=f"{self.ticket_type.capitalize()} ticket for {user} (ID: {user.id})"
        )

        active_tickets[user.id] = channel.id

        await channel.send(f"**New {self.ticket_type.capitalize()} Ticket**
**User:** {user.mention}
**Issue:** {self.issue.value}")
        await interaction.response.send_message(f"Your {self.ticket_type} ticket has been created: {channel.mention}", ephemeral=True)


class ClaimTicketButton(View):(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.blurple, custom_id="claim_ticket_button")
    async def claim(self, interaction: discord.Interaction, button: Button):
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)
            return

        channel = interaction.channel

        # Prevent claiming twice
        if "Claimed by" in (channel.topic or ""):
            await interaction.response.send_message("This ticket is already claimed!", ephemeral=True)
            return

        # Lock ticket so only claimer & staff can talk
        overwrites = channel.overwrites
        for target, perms in list(overwrites.items()):
            if isinstance(target, discord.Member):
                perms.send_messages = False
                overwrites[target] = perms

        # Allow claimer to speak
        overwrites[interaction.user] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        await channel.edit(overwrites=overwrites)

        # Update topic with claimer name
        new_topic = f"{channel.topic} | Claimed by {interaction.user.name}"
        await channel.edit(topic=new_topic)

        await channel.send(f"🔒 Ticket has been claimed by {interaction.user.mention} and locked.")
        await interaction.response.send_message("You claimed this ticket.", ephemeral=True)

        await interaction.channel.send(f"{interaction.user.mention} has claimed this ticket.")
        await interaction.response.send_message("You claimed this ticket.", ephemeral=True)


class CloseTicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        channel = interaction.channel
        guild = interaction.guild
        user = interaction.user

        # Validate ticket category
        if channel.category_id != TICKET_CATEGORY_ID:
            await interaction.response.send_message(
                "This is not a ticket channel.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Closing ticket in 5 seconds...", ephemeral=True
        )

        # Create transcript
        transcript_text = "Transcript for ticket: " + channel.name + "

"
        messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]

        for msg in messages:
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            transcript_text += f"[{timestamp}] {msg.author}: {msg.content}
"

        # Send transcript to log channel
        log_channel = guild.get_channel(TRANSCRIPT_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                content=f"Transcript from {channel.name}",
                file=discord.File(fp=discord.BytesIO(transcript_text.encode()), filename=f"{channel.name}.txt")
            )

        # Remove user from active tickets
        for uid, tid in list(active_tickets.items()):
            if tid == channel.id:
                del active_tickets[uid]
                break

        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=5))
        await channel.delete()


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Register persistent views so buttons survive restarts
        self.bot.add_view(TicketButton())
        self.bot.add_view(ClaimTicketButton())

        # Automatically send Open Ticket button to the specified channel
        channel = self.bot.get_channel(1439589764222423160)
        if channel:
            embed = discord.Embed(
                title="Support Tickets",
                description="Click the button below to open a ticket.",
                color=discord.Color.blue()
            )
            try:
                await channel.send(embed=embed, view=TicketButton())
            except:
                pass

    @commands.command(name="ticketpanel")
    @commands.has_permissions(administrator=True)
    async def ticketpanel(self, ctx):
        """Creates the ticket panel with button manually"""
        embed = discord.Embed(
            title="Support Tickets",
            description="Click the button below to open a ticket.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=TicketButton())(self, ctx):
        """Creates the ticket panel with button"""
        embed = discord.Embed(
            title="Support Tickets",
            description="Click the button below to open a ticket.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=TicketButton())

    @commands.Cog.listener()
    async def on_ready(self):
        # Register persistent views so buttons survive restarts
        self.bot.add_view(TicketButton())
        self.bot.add_view(CloseTicketButton())

async def setup(bot):
    await bot.add_cog(TicketCog(bot))
