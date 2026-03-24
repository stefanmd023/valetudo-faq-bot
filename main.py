import discord
from discord.ext import commands
from discord import app_commands
import os
import difflib
import typing

# --- CONFIGURATION ---
FAQ_PATH = './valetudobot/faq'  # Path to your .txt files
EMBED_COLOR = 0x3498db           # Valetudo Blue

# --- TOKEN LOADER ---
def load_token():
    """Reads the token from disctoken.txt with UTF-8-SIG to avoid hidden characters."""
    token_file = 'disctoken.txt'
    if os.path.exists(token_file):
        with open(token_file, 'r', encoding='utf-8-sig') as f:
            lines = f.read().splitlines()
            for line in lines:
                if line.strip(): 
                    return line.strip()
    print(f"❌ Error: {token_file} is empty or missing!")
    exit()

TOKEN = load_token()

# --- BOT CLASS SETUP ---
class ValetudoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Syncs slash commands globally (can take up to 1 hour to propagate)
        await self.tree.sync()
        print(f"🌐 Slash commands synced for {self.user}")

bot = ValetudoBot()

# --- DATA HELPERS ---

def get_faq_list():
    """Returns a list of available filenames (without .txt) for autocomplete."""
    if not os.path.exists(FAQ_PATH): 
        return []
    return [f.replace('.txt', '') for f in os.listdir(FAQ_PATH) if f.endswith('.txt')]

def parse_valetudo_file(file_path):
    """Extracts Title and Text body from Valetudo .txt format."""
    title, content, is_text = "FAQ", "", False
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('title:'): 
                title = line.replace('title:', '').strip()
            elif line.strip().lower() == 'text:':
                is_text = True
                continue
            if is_text: 
                content += line

    # Convert HTML code tags to Discord backticks
    content = content.replace('<code>', '`').replace('</code>', '`')
    return title, content.strip()

# --- HYBRID COMMAND (Works as /faq and !faq) ---

@bot.hybrid_command(name="faq", description="Search the Valetudo FAQ database")
@app_commands.describe(topic="The topic or keyword you are looking for")
async def faq(ctx: commands.Context, topic: str = None):
    if not topic:
        topics = get_faq_list()
        embed = discord.Embed(
            title="📖 FAQ Topics", 
            description="Type `/faq <topic>`\n\n" + ", ".join([f"`{t}`" for t in topics]),
            color=EMBED_COLOR
        )
        return await ctx.send(embed=embed)

    topic = topic.lower().strip()
    found_file = None
    all_files = [f for f in os.listdir(FAQ_PATH) if f.endswith('.txt')]
    
    # 1. Check for Exact Filename Match
    potential_path = os.path.join(FAQ_PATH, f"{topic}.txt")
    if os.path.exists(potential_path):
        found_file = potential_path
    
    # 2. Check Keywords Inside Files
    if not found_file:
        for f_name in all_files:
            path = os.path.join(FAQ_PATH, f_name)
            with open(path, 'r', encoding='utf-8') as f:
                # Read only top 15 lines to save memory/speed
                head = [next(f) for _ in range(15) if f] 
                for line in head:
                    if line.startswith('keywords:') and topic in line.lower():
                        found_file = path
                        break
            if found_file: break

    # 3. Output Result or Suggestion
    if found_file:
        title, text = parse_valetudo_file(found_file)
        embed = discord.Embed(title=f"🛠️ {title}", description=text[:4000], color=EMBED_COLOR)
        await ctx.send(embed=embed)
    else:
        # Fuzzy match for typos
        possible = get_faq_list()
        matches = difflib.get_close_matches(topic, possible, n=1, cutoff=0.6)
        suggestion = f" Did you mean `/faq {matches[0]}`?" if matches else ""
        await ctx.send(f"❌ Topic `{topic}` not found.{suggestion}", ephemeral=True)

# --- AUTOCOMPLETE LOGIC ---

@faq.autocomplete('topic')
async def faq_autocomplete(interaction: discord.Interaction, current: str):
    topics = get_faq_list()
    # Filter topics based on what the user is currently typing
    return [
        app_commands.Choice(name=t, value=t)
        for t in topics if current.lower() in t.lower()
    ][:25] # Discord limit is 25 items

# --- OWNER COMMANDS ---

@bot.command()
@commands.is_owner()
async def sync(ctx):
    """Owner only: Force sync commands to the current server immediately."""
    await bot.tree.sync()
    await ctx.send("✅ Slash commands synced to this server!")

# --- EXECUTION ---
if __name__ == "__main__":
    bot.run(TOKEN)