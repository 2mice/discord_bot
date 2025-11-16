import discord
from discord.ext import commands
from discord.ui import View, Button

# Replace with your actual values
TICKET_CATEGORY_ID = 1439655079127814274  # <-- SET THIS
STAFF_ROLE_ID = 1438950739664830534        # <-- SET THIS
TRANSCRIPT_LOG_CHANNEL_ID = 1439656270000033944  # <-- SET THIS

# Track active tickets per user
active_tickets = {}

class TicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket_button")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user

        # Check if user already has a ticket
        if user.id in active_tickets:
            await interaction.response.send_message(
                "You already have an open ticket!", ephemeral=True
            )
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message(
                "Ticket category not found. Contact staff.", ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}-{user.discriminator}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket for {user} (ID: {user.id})"
        )

        # Save active ticket
        active_tickets[user.id] = channel.id

        await channel.send(f"Hello {user.mention}, please describe your issue.")
        await interaction.response.send_message(
            f"Your ticket has been created: {channel.mention}", ephemeral=True
        )


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

    @commands.command(name="ticketpanel")
    @commands.has_permissions(administrator=True)
    async def ticketpanel(self, ctx):
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
