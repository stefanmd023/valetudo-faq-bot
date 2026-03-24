import discord
from discord.ext import commands
from discord import app_commands
import os
import difflib

# --- CONFIGURATION ---
BASE_PATH = './valetudobot'
FAQ_PATH = os.path.join(BASE_PATH, 'faq')
ROOT_PATH = os.path.join(BASE_PATH, 'root')
EMBED_COLOR_FAQ = 0x3498db  # Blue
EMBED_COLOR_ROOT = 0xe74c3c # Red

# --- TOKEN LOADER ---
def load_token():
    """Reads the token from disctoken.txt with safety for hidden characters."""
    token_file = 'disctoken.txt'
    if os.path.exists(token_file):
        with open(token_file, 'r', encoding='utf-8-sig') as f:
            lines = f.read().splitlines()
            for line in lines:
                if line.strip(): 
                    return line.strip()
    exit("❌ Error: disctoken.txt missing or empty in /data/valetudo-faq-bot/")

TOKEN = load_token()

# --- BOT CLASS SETUP ---
class ValetudoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Syncs slash commands globally
        await self.tree.sync()
        print(f"🌐 Logged in as {self.user} | Commands Synced")

bot = ValetudoBot()

# --- DATA HELPERS ---

def get_file_list(folder_path):
    """Returns a list of .txt filenames (without extension) for autocomplete."""
    if not os.path.exists(folder_path):
        return []
    return [f.replace('.txt', '') for f in os.listdir(folder_path) if f.endswith('.txt')]

def parse_valetudo_file(file_path):
    """Parses Valetudo-style .txt files (Title: ... Text: ...)"""
    title, content, is_text = "Information", "", False
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('title:'):
                    title = line.replace('title:', '').strip()
                elif line.strip().lower() == 'text:':
                    is_text = True
                    continue
                if is_text:
                    content += line
        # Simple HTML to Markdown conversion
        content = content.replace('<code>', '`').replace('</code>', '`').strip()
        return title, content
    except Exception as e:
        return "Error", f"Could not read file: {e}"

# --- HYBRID COMMANDS ---

@bot.hybrid_command(name="helpme", description="Show the Valetudo help menu")
async def helpme(ctx: commands.Context):
    embed = discord.Embed(
        title="Valetudo Support",
        description=(
            "**Commands:**\n"
            "`/faq <topic>` - General setup and troubleshooting\n"
            "`/root <robot>` - Specific rooting instructions\n\n"
            "*Type `/` to see the autocomplete list!*"
        ),
        color=EMBED_COLOR_FAQ
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(name="faq", description="Search general Valetudo FAQ")
@app_commands.describe(topic="The general topic to search for")
async def faq(ctx: commands.Context, topic: str):
    path = os.path.join(FAQ_PATH, f"{topic.lower()}.txt")
    
    if os.path.exists(path):
        title, text = parse_valetudo_file(path)
        embed = discord.Embed(title=f"📖 {title}", description=text[:4000], color=EMBED_COLOR_FAQ)
        await ctx.send(embed=embed)
    else:
        # Suggest a close match if they made a typo
        options = get_file_list(FAQ_PATH)
        matches = difflib.get_close_matches(topic.lower(), options, n=1, cutoff=0.5)
        suggestion = f" Did you mean `/faq {matches[0]}`?" if matches else ""
        await ctx.send(f"❌ FAQ topic `{topic}` not found.{suggestion}", ephemeral=True)

@bot.hybrid_command(name="root", description="Search robot-specific rooting instructions")
@app_commands.describe(robot="The robot model to get rooting info for")
async def root(ctx: commands.Context, robot: str):
    path = os.path.join(ROOT_PATH, f"{robot.lower()}.txt")
    
    if os.path.exists(path):
        title, text = parse_valetudo_file(path)
        embed = discord.Embed(title=f"🔐 Rooting: {title}", description=text[:4000], color=EMBED_COLOR_ROOT)
        await ctx.send(embed=embed)
    else:
        options = get_file_list(ROOT_PATH)
        matches = difflib.get_close_matches(robot.lower(), options, n=1, cutoff=0.5)
        suggestion = f" Did you mean `/root {matches[0]}`?" if matches else ""
        await ctx.send(f"❌ Rooting guide for `{robot}` not found.{suggestion}", ephemeral=True)

# --- AUTOCOMPLETE HANDLERS ---

@faq.autocomplete('topic')
async def faq_autocomplete(interaction: discord.Interaction, current: str):
    topics = get_file_list(FAQ_PATH)
    return [
        app_commands.Choice(name=t, value=t) 
        for t in topics if current.lower() in t.lower()
    ][:25]

@root.autocomplete('robot')
async def root_autocomplete(interaction: discord.Interaction, current: str):
    robots = get_file_list(ROOT_PATH)
    return [
        app_commands.Choice(name=r, value=r) 
        for r in robots if current.lower() in r.lower()
    ][:25]

# --- OWNER ONLY UTILITIES ---

@bot.command()
@commands.is_owner()
async def sync(ctx):
    """Force sync commands to the current server immediately."""
    await bot.tree.sync()
    await ctx.send("✅ Slash commands synced to this server!")

# --- START THE BOT ---
if __name__ == "__main__":
    bot.run(TOKEN)