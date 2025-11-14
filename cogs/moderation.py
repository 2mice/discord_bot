import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        """Clears messages, notifies the channel, and logs the action."""
        if amount < 1:
            await ctx.send("You must delete at least 1 message!")
            return

        # Delete messages
        deleted = await ctx.channel.purge(limit=amount)

        # Notify the channel briefly
        notif = await ctx.send(f"🗑️ {len(deleted)} messages cleared by {ctx.author.mention}.")
        await notif.delete(delay=5)

        # Check if log channel exists, create if not
        log_channel_name = "bot-logs"
        log_channel = discord.utils.get(ctx.guild.text_channels, name=log_channel_name)

        if log_channel is None:
            # Create the logging channel
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False)
            }
            log_channel = await ctx.guild.create_text_channel(log_channel_name, overwrites=overwrites)

        # Send log embed
        embed = discord.Embed(
            title="Messages Cleared",
            description=f"**Moderator:** {ctx.author.mention}\n**Channel:** {ctx.channel.mention}\n**Amount:** {len(deleted)}",
            color=discord.Color.red()
        )
        await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
