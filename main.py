import discord
from discord.ext import commands
from discord import app_commands
import os
import difflib

# --- CONFIGURATION ---
FAQ_PATH = './valetudobot/faq'  
EMBED_COLOR = 0x3498db           

# --- TOKEN LOADER ---
def load_token():
    token_file = 'disctoken.txt'
    if os.path.exists(token_file):
        with open(token_file, 'r', encoding='utf-8-sig') as f:
            lines = f.read().splitlines()
            for line in lines:
                if line.strip(): return line.strip()
    exit("❌ disctoken.txt missing!")

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
        print(f"🌐 Slash commands synced for {self.user}")

bot = ValetudoBot()

# --- DATA HELPERS ---

def get_faq_list():
    if not os.path.exists(FAQ_PATH): return []
    return [f.replace('.txt', '') for f in os.listdir(FAQ_PATH) if f.endswith('.txt')]

def parse_valetudo_file(file_path):
    title, content, is_text = "FAQ", "", False
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('title:'): title = line.replace('title:', '').strip()
            elif line.strip().lower() == 'text:':
                is_text = True
                continue
            if is_text: content += line
    return title, content.strip().replace('<code>', '`').replace('</code>', '`')

# --- UI COMPONENTS ---

class HelpButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="📄 List Topics", style=discord.ButtonStyle.primary)
    async def topics_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = get_faq_list()
        embed = discord.Embed(
            title="📖 FAQ Topics", 
            description="Use `/faq <topic>`\n\n" + ", ".join([f"`{t}`" for t in topics]),
            color=EMBED_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🔍 Search Keywords", style=discord.ButtonStyle.secondary)
    async def keywords_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Quick keyword scan
        all_kws = set()
        for f_name in os.listdir(FAQ_PATH):
            if f_name.endswith('.txt'):
                with open(os.path.join(FAQ_PATH, f_name), 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('keywords:'):
                            all_kws.update([k.strip() for k in line.replace('keywords:', '').split(',')])
                            break
        
        embed = discord.Embed(
            title="🔍 Keywords", 
            description="Search using these words:\n\n" + ", ".join([f"`{k}`" for k in sorted(list(all_kws))]),
            color=EMBED_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=self)

# --- HYBRID COMMANDS ---

@bot.hybrid_command(name="helpme", description="Show the Valetudo help menu")
async def helpme(ctx: commands.Context):
    view = HelpButtons()
    embed = discord.Embed(
        title="Valetudo Support",
        description="Select an option below to browse the FAQ database.",
        color=EMBED_COLOR
    )
    await ctx.send(embed=embed, view=view)

@bot.hybrid_command(name="faq", description="Search the Valetudo FAQ database")
@app_commands.describe(topic="The topic or keyword you are looking for")
async def faq(ctx: commands.Context, topic: str = None):
    if not topic:
        return await helpme(ctx)

    topic = topic.lower().strip()
    found_file = None
    all_files = [f for f in os.listdir(FAQ_PATH) if f.endswith('.txt')]
    
    # 1. Filename Match
    potential_path = os.path.join(FAQ_PATH, f"{topic}.txt")
    if os.path.exists(potential_path):
        found_file = potential_path
    
    # 2. Internal Keyword Match
    if not found_file:
        for f_name in all_files:
            path = os.path.join(FAQ_PATH, f_name)
            with open(path, 'r', encoding='utf-8') as f:
                head = [next(f) for _ in range(15) if f] 
                for line in head:
                    if line.startswith('keywords:') and topic in line.lower():
                        found_file = path
                        break
            if found_file: break

    if found_file:
        title, text = parse_valetudo_file(found_file)
        embed = discord.Embed(title=f"🛠️ {title}", description=text[:4000], color=EMBED_COLOR)
        await ctx.send(embed=embed)
    else:
        possible = get_faq_list()
        matches = difflib.get_close_matches(topic, possible, n=1, cutoff=0.6)
        suggestion = f" Did you mean `/faq {matches[0]}`?" if matches else ""
        await ctx.send(f"❌ Topic not found.{suggestion}", ephemeral=True)

# Autocomplete for /faq
@faq.autocomplete('topic')
async def faq_autocomplete(interaction: discord.Interaction, current: str):
    topics = get_faq_list()
    return [app_commands.Choice(name=t, value=t) for t in topics if current.lower() in t.lower()][:25]

# Sync command for owner
@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("✅ Synced!")

bot.run(TOKEN)