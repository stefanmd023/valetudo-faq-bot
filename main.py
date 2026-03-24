import discord
from discord.ext import commands
from discord import app_commands
import os
import difflib
import logging
from logging.handlers import RotatingFileHandler

# --- CONFIGURATION ---
BASE_PATH = './valetudobot'
FAQ_PATH = os.path.join(BASE_PATH, 'faq')
ROOT_PATH = os.path.join(BASE_PATH, 'root')
LOG_FILE = '/data/valetudo-faq-bot/bot_activity.log'
CHANGELOG_FILE = '/data/valetudo-faq-bot/changelog.txt'

# --- LOGGING SETUP (Self-Cleaning) ---
# Keeps 5 backup files of 5MB each. Never fills up your Proxmox LXC disk.
log_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[log_handler, logging.StreamHandler()]
)
logger = logging.getLogger('ValetudoBot')

# --- TOKEN LOADER ---
def load_token():
    token_file = 'disctoken.txt'
    if os.path.exists(token_file):
        with open(token_file, 'r', encoding='utf-8-sig') as f:
            lines = f.read().splitlines()
            for line in lines:
                if line.strip(): return line.strip()
    logger.error("disctoken.txt is missing in /data/valetudo-faq-bot/")
    exit(1)

TOKEN = load_token()

# --- BOT SETUP ---
class ValetudoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Initial sync on startup
        await self.tree.sync()
        logger.info(f"Bot started as {self.user}. Commands Synced.")

bot = ValetudoBot()

# --- DATA HELPERS ---

def get_file_list(folder_path):
    """Returns a list of .txt filenames for autocomplete."""
    if not os.path.exists(folder_path): return []
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
        return title, content.replace('<code>', '`').replace('</code>', '`').strip()
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return "Error", "Could not read the file."

def get_recent_changelog():
    """Reads the first 5 lines of changelog.txt"""
    if os.path.exists(CHANGELOG_FILE):
        try:
            with open(CHANGELOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                return "".join(lines[:5])
        except Exception as e:
            logger.error(f"Changelog read error: {e}")
            return "Could not load updates."
    return "No recent updates recorded."

# --- HYBRID COMMANDS ---

@bot.hybrid_command(name="helpme", description="Show the Valetudo help menu and updates")
async def helpme(ctx: commands.Context):
    logger.info(f"USER:{ctx.author} | CMD:/helpme")
    updates = get_recent_changelog()
    
    embed = discord.Embed(title="🤖 Valetudo Support Bot", color=0x3498db)
    embed.add_field(name="Commands", value="`/faq <topic>`\n`/root <robot>`\n`/helpme`", inline=True)
    embed.add_field(name="Recent Updates", value=f"```text\n{updates}\n```", inline=False)
    embed.set_footer(text="Pro-tip: Autocomplete works in / commands!")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="faq", description="Search general Valetudo FAQ")
async def faq(ctx: commands.Context, topic: str):
    path = os.path.join(FAQ_PATH, f"{topic.lower()}.txt")
    if os.path.exists(path):
        title, text = parse_valetudo_file(path)
        logger.info(f"USER:{ctx.author} | CMD:/faq | TOPIC:{topic} | SUCCESS")
        await ctx.send(embed=discord.Embed(title=f"📖 {title}", description=text[:4000], color=0x3498db))
    else:
        logger.warning(f"USER:{ctx.author} | CMD:/faq | TOPIC:{topic} | NOT_FOUND")
        options = get_file_list(FAQ_PATH)
        matches = difflib.get_close_matches(topic.lower(), options, n=1, cutoff=0.5)
        suggestion = f" Did you mean `/faq {matches[0]}`?" if matches else ""
        await ctx.send(f"❌ FAQ topic `{topic}` not found.{suggestion}", ephemeral=True)

@bot.hybrid_command(name="root", description="Search robot rooting instructions")
async def root(ctx: commands.Context, robot: str):
    path = os.path.join(ROOT_PATH, f"{robot.lower()}.txt")
    if os.path.exists(path):
        title, text = parse_valetudo_file(path)
        logger.info(f"USER:{ctx.author} | CMD:/root | ROBOT:{robot} | SUCCESS")
        await ctx.send(embed=discord.Embed(title=f"🔐 Rooting: {title}", description=text[:4000], color=0xe74c3c))
    else:
        logger.warning(f"USER:{ctx.author} | CMD:/root | ROBOT:{robot} | NOT_FOUND")
        options = get_file_list(ROOT_PATH)
        matches = difflib.get_close_matches(robot.lower(), options, n=1, cutoff=0.5)
        suggestion = f" Did you mean `/root {matches[0]}`?" if matches else ""
        await ctx.send(f"❌ Rooting guide for `{robot}` not found.{suggestion}", ephemeral=True)

# --- AUTOCOMPLETE ---

@faq.autocomplete('topic')
async def faq_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=t, value=t) for t in get_file_list(FAQ_PATH) if current.lower() in t.lower()][:25]

@root.autocomplete('robot')
async def root_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=r, value=r) for r in get_file_list(ROOT_PATH) if current.lower() in r.lower()][:25]

# --- ADMIN COMMANDS ---

@bot.hybrid_command(name="faqsync", description="Owner only: Sync all slash commands")
@commands.is_owner()
@commands.cooldown(1, 30, commands.BucketType.user)
async def faqsync(ctx: commands.Context):
    try:
        await bot.tree.sync()
        logger.info(f"ADMIN:{ctx.author} | ACTION:SYNC | SUCCESS")
        await ctx.send("✅ Slash commands (including /faq and /root) have been synced!", ephemeral=True)
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        await ctx.send(f"❌ Sync failed: {e}", ephemeral=True)

# Cooldown error handler
@faqsync.error
async def faqsync_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Sync is on cooldown. Try again in {error.retry_after:.1f}s.", delete_after=5)

bot.run(TOKEN)