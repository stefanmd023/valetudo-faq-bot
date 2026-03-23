import discord
from discord.ext import commands
import os
import difflib

# --- CONFIGURATION ---
TOKEN = 'YOUR_DISCORD_BOT_TOKEN'
FAQ_PATH = './valetudobot/faq'  # Path to your .txt files
EMBED_COLOR = 0x3498db           # Blue

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# --- HELPER FUNCTIONS ---

def get_faq_data():
    """Maps keywords and filenames to their actual file paths."""
    faq_map = {}
    all_topics = []
    all_keywords = set()
    
    if not os.path.exists(FAQ_PATH):
        return {}, [], []

    for filename in os.listdir(FAQ_PATH):
        if filename.endswith('.txt'):
            topic_key = filename.replace('.txt', '').lower()
            file_path = os.path.join(FAQ_PATH, filename)
            all_topics.append(topic_key)
            
            # Index the filename itself
            faq_map[topic_key] = file_path
            
            # Index the keywords inside the file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('keywords:'):
                            kws = [k.strip().lower() for k in line.replace('keywords:', '').split(',')]
                            for kw in kws:
                                if kw: # ensure not empty
                                    faq_map[kw] = file_path
                                    all_keywords.add(kw)
                            break 
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                
    return faq_map, sorted(all_topics), sorted(list(all_keywords))

def parse_valetudo_file(file_path):
    """Parses metadata and content from Valetudo .txt files."""
    title = "Valetudo Help"
    content = ""
    is_text_section = False

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('title:'):
                title = line.replace('title:', '').strip()
            elif line.strip().lower() == 'text:':
                is_text_section = True
                continue
            if is_text_section:
                content += line

    # Convert HTML code tags to Discord backticks
    content = content.replace('<code>', '`').replace('</code>', '`')
    return title, content.strip()

# --- UI COMPONENTS ---

class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="📄 List Topics", style=discord.ButtonStyle.primary)
    async def topics_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        _, topics, _ = get_faq_data()
        embed = discord.Embed(
            title="📖 Available FAQ Topics",
            description="Type `!faq <topic>` to view.\n\n" + ", ".join([f"`{t}`" for t in topics]),
            color=EMBED_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🔍 Search Keywords", style=discord.ButtonStyle.secondary)
    async def keywords_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        _, _, keywords = get_faq_data()
        embed = discord.Embed(
            title="🔍 Search Keywords",
            description="Use these as keywords in `!faq <keyword>`:\n\n" + ", ".join([f"`{k}`" for k in keywords]),
            color=EMBED_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=self)

# --- BOT COMMANDS ---

@bot.event
async def on_ready():
    print(f'✅ Bot Online: {bot.user.name}')
    print(f'📂 FAQ Path: {os.path.abspath(FAQ_PATH)}')

@bot.command()
async def helpme(ctx):
    """Shows the interactive help menu with buttons."""
    view = HelpMenu()
    embed = discord.Embed(
        title="Valetudo Robot Support",
        description="I can help with rooting, autostart, and more. Click a button below to explore.",
        color=EMBED_COLOR
    )
    await ctx.send(embed=embed, view=view)

@bot.command()
async def faq(ctx, *, topic: str = None):
    """The main FAQ command. Supports filenames, keywords, and fuzzy matching."""
    faq_map, all_topics, all_keywords = get_faq_data()

    if not topic:
        return await helpme(ctx)

    topic = topic.lower().strip()
    
    # 1. Check for Exact Match (Filename or Keyword)
    if topic in faq_map:
        title, text = parse_valetudo_file(faq_map[topic])
        embed = discord.Embed(title=f"🛠️ {title}", description=text[:4000], color=EMBED_COLOR)
        embed.set_footer(text=f"Topic: {topic}")
        await ctx.send(embed=embed)
        
    # 2. Fuzzy Suggestion for Typos
    else:
        all_possible_keys = list(faq_map.keys())
        matches = difflib.get_close_matches(topic, all_possible_keys, n=1, cutoff=0.6)
        
        if matches:
            await ctx.send(f"❓ Not found. Did you mean `!faq {matches[0]}`?")
        else:
            await ctx.send(f"❌ I couldn't find anything for `{topic}`. Try `!helpme` to see all keywords.")

# --- RUN BOT ---
if __name__ == "__main__":
    bot.run(TOKEN)