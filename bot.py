import discord
import secrets
import dateparser
from dateparser.search import search_dates
from binascii import hexlify

import re
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base

engine = create_engine('sqlite:///:memory:', echo=True)
Base = declarative_base()
class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True)
    request_message_id = Column(String)
    reminder_message_id = Column(String)
    def __repr__(self):
        return f"<Reminder(id={self.id}, request_message_id={self.request_message_id}, reminder_message_id={self.reminder_message_id})>"

Base.metadata.create_all(engine)


scheduler = AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url="sqlite:///:memory:")}
)


intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)



async def send_error_message(title, description, message):
    try:
        await message.add_reaction("❌")
    except discord.errors.Forbidden as e:
        pass

    name = message.guild.name if message.guild is not None else "a direct message"

    embed = discord.Embed(
        title=title,
        description=description.format(name, gen_link(message)),
        color=0xFF2020,
    )
    embed.add_field(
        name="Request",
        value="[{}]({})".format(message.content, gen_link(message)),
        inline=False,
    )
    await message.author.send(embed=embed)



def gen_link(message):
    return (
        "https://discord.com/channels/"
        + str(message.guild.id) if message.guild else "@me"
        + "/"
        + str(message.channel.id)
        + "/"
        + str(message.id)
    )




async def send_reminder(channel_id, message_id, reminder_text):
    print('send reminder')
    channel = client.get_channel(channel_id)
    if getattr(channel, 'guild', None) and channel.guild.id == 852786013934714890:
        await channel.send('someone attempted to send a reminder here')
    else:
        await channel.send(reminder_text)


async def set_reminder(date, message, reminder_text=""):
    print('set reminder')
    try:
        await message.add_reaction("✅")
    except discord.errors.Forbidden as e:
        # This is fine.
        pass

    name = message.guild.name if message.guild is not None else "a direct message"

    pretty_date = date.strftime("%A, %B %d, %Y at %H:%M %Z")
    if reminder_text:
        description = (
            'I will remind you on ** {} ** about your message in [{}]({}) "{}"'.format(
                pretty_date, name, gen_link(message), reminder_text
            )
        )
    else:
        description = "I will remind you on ** {} ** in [{}]({})".format(
            pretty_date, name, gen_link(message)
        )

    embed = discord.Embed(
        title="Reminder Set!",
        description=description,
        color=0x60FF60,
    )
    embed.add_field(
        name="Time",
        value=pretty_date,
        inline=False,
    )
    if reminder_text:
        embed.add_field(
            name="Reminder",
            value=reminder_text,
            inline=False,
        )
    embed.add_field(
        name="Request",
        value="[{}]({})".format(message.content, gen_link(message)),
        inline=False,
    )

    print(message)
    try:
        channel_id = client.get_channel(int(message.content.split(' ')[-1])).id
        reminder_text = ' '.join(reminder_text.split(' ')[:-1])
    except:
        channel_id = message.channel.id

    scheduler.add_job(
        send_reminder,
        "date",
        run_date=date,
        args=[channel_id, message.id, reminder_text],
    )
    await message.author.send(embed=embed)


async def handle_remind_me(args, message):
    print('handle reminder')
    content = " ".join(args[1:])
    # Is there a better way to parse dates, or is this ideal?
    date = None
    date_text = content

    while date_text and date is None:
        date = dateparser.parse(
            date_text,
            settings={
                "TIMEZONE": "UTC",
                "TO_TIMEZONE": "UTC",
                "RETURN_AS_TIMEZONE_AWARE": True,
                "PREFER_DATES_FROM": "future",
            },
        )
        if date is not None:
            break
        date_text = " ".join(date_text.split()[:-1]).strip()

    if date:
        reminder_text = date_text.join(content.split(date_text)[1:]).strip()
        await set_reminder(date, message, reminder_text)
    else:
        await send_error_message(
            "Invalid Format", "Your command had an invalid format or date.", message
        )

async def handle_debug(args, message):
    content = " ".join(args)

    a,b = bytearray(content, 'utf8'), bytearray(secrets.flag2, 'utf8')
    a = b''.join([bytes(chr((b[i] ^ a[i])), 'utf8') for i in range(len(a))])
    await message.channel.send(hexlify(a))

@client.event
async def on_message(message):
    name = "dm channel" if isinstance(message.channel, discord.channel.DMChannel) else message.channel.name
    args = message.content.split()

    if name == 'dm channel':
        if args and args[0] == "remindme":
            await handle_remind_me(args, message)
    elif name == 'flag-deletion-test':
        if re.match(r".*ccc\{.*\}.*", message.content, re.IGNORECASE):
            await message.delete()
            flag_warnings = [
                "👀",
                "Please be careful about posting flags in a public channel.",
                "NO FLAG SHARING.",
                "...",
                "🤔",
                "🚫 That ain't it.",
                "Submit the flag at https://ctf.circlecitycon.com",
                "That's the flag format!"
            ]
            await message.channel.send(message.author.mention + " " + random.choice(flag_warnings))
    elif len(args) >= 2 and args[0] == "sudo":
        if args[1] == "debug":
            if client.get_guild(852786013934714890).get_member(message.author.id).guild_permissions.administrator:
                await handle_debug(args[2:], message)

    

scheduler.start()

flag_deletion_guild_id = 852786013934714890
flag_deletion_channel_id = 852786136492671036

async def send_flag(guild_id, channel_id):
    print('sending flag')
    guild = client.get_guild(guild_id)
    channel = guild.get_channel(channel_id)

    await channel.send(secrets.flag1)

@client.event
async def on_ready():
    """
    on ready
    """
    print("We have logged in as {0.user}".format(client))

    scheduler.add_job(
        send_flag,
        "interval",
        minutes=15,
        args=[flag_deletion_guild_id, flag_deletion_channel_id],
    )

client.run(secrets.secret)
