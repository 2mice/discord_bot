import discord
from discord.ext import commands

class TicketCog(commands.Cog):
    def __init__(self, bot: commands.Bot, ticket_category_id: int, staff_role_id: int):
        self.bot = bot
        self.ticket_category_id = ticket_category_id
        self.staff_role_id = staff_role_id

    @commands.slash_command(name="ticket", description="Open a new support ticket")
    async def ticket(self, ctx: discord.Interaction):
        """Slash command to open a ticket."""
        guild = ctx.guild
        member = ctx.user

        category = guild.get_channel(self.ticket_category_id)
        if not category:
            await ctx.respond("Ticket category not found. Contact an admin.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
            guild.get_role(self.staff_role_id): discord.PermissionOverwrite(view_channel=True),
        }

        # Name channel uniquely, e.g., ticket-username-id
        channel_name = f"ticket-{member.name}-{member.discriminator}"
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            topic=f"Ticket for {member} (ID: {member.id})"
        )

        await ticket_channel.send(f"Hello {member.mention}, please explain your issue and a staff member will help you soon.")
        await ctx.respond(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

    @commands.slash_command(name="close", description="Close this ticket")
    @commands.has_role  # you can put a check here, or custom check
    async def close(self, ctx: discord.Interaction):
        """Close the ticket (must be used in a ticket channel)."""
        channel = ctx.channel
        # Optionally check that this is really a ticket channel:
        if not isinstance(channel, discord.TextChannel):
            await ctx.respond("This command must be used in a ticket.")
            return

        # Send a closing message
        await channel.send("This ticket will be closed in 5 seconds…")
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=5))
        try:
            await channel.delete()
        except Exception as e:
            await ctx.respond("Could not delete channel. Maybe missing permissions.")

def setup(bot: commands.Bot):
    # Replace these with your actual category ID and staff role ID
    TICKET_CATEGORY_ID = 1439655079127814274
    STAFF_ROLE_ID = 1438950739664830534

    bot.add_cog(TicketCog(bot, TICKET_CATEGORY_ID, STAFF_ROLE_ID))
