# (c) @nihatfarz.

import re
import logging

from redis import Redis
from decouple import config
from telethon import TelegramClient, events, Button, types, functions, errors

logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s"
)
log = logging.getLogger("ChannelActions")
log.info("\n\nBaşlanır...\n")


try:
    bot_token = config("BOT_TOKEN")
    REDIS_URI = config("REDIS_URI")
    REDIS_PASSWORD = config("REDIS_PASSWORD")
    AUTH = [int(i) for i in config("OWNERS").split(" ")]
except Exception as e:
    log.exception(e)
    exit(1)

try:
    bot = TelegramClient(None, 6, "eb06d4abfb49dc3eeb1aeb98ae0f581e").start(
        bot_token=bot_token
    )
except Exception as e:
    log.exception(e)
    exit(1)

REDIS_URI = REDIS_URI.split(":")
db = Redis(
    host=REDIS_URI[0],
    port=REDIS_URI[1],
    password=REDIS_PASSWORD,
    decode_responses=True,
)


def str_to_list(text):  
    return text.split(" ")


def list_to_str(list):  
    str = "".join(f"{x} " for x in list)
    return str.strip()


def is_added(var, id):  
    if not str(id).isdigit():
        return False
    users = get_all(var)
    return str(id) in users


def add_to_db(var, id):  
    id = str(id)
    if not id.isdigit():
        return False
    try:
        users = get_all(var)
        users.append(id)
        db.set(var, list_to_str(users))
        return True
    except Exception as e:
        return False


def get_all(var):  # Returns List
    users = db.get(var)
    if users is None or users == "":
        return [""]
    else:
        return str_to_list(users)


async def get_me():
    me = await bot.get_me()
    myname = me.username
    return "@" + myname


bot_username = bot.loop.run_until_complete(get_me())
start_msg = """Salam {user}!
**Mən kanal əməliyyatları botuyam, əsasən yeni [Admin təsdiq dəvəti linkləri](https://t.me/telegram/153) ilə işləməyə hazırlanmışam.**
**__Funksiyalar__**:
- __Yeni Qoşulma sorğularını avtomatik təsdiqləyin.__
- __Yeni Qoşulma İstəklərindən Avtomatik imtina edin.__
`Məndən necə istifadə edəcəyinizi bilmək üçün aşağıdakı düyməyə klikləyin!
`"""
start_buttons = [
    [Button.inline("Məndən necə istifadə etmək olar ❓", data="helper")],
    [Button.url("Kanalımız📣", "https://t.me/FarzTeam")],
]


@bot.on(events.NewMessage(incoming=True, pattern=f"^/start({bot_username})?$"))
async def starters(event):
    if not is_added("BOTUSERS", event.sender_id):
        add_to_db("BOTUSERS", event.sender_id)
    from_ = await bot.get_entity(event.sender_id)
    await event.reply(
        start_msg.format(user=from_.first_name),
        buttons=start_buttons,
        link_preview=False,
    )


@bot.on(events.CallbackQuery(data="start"))
async def start_in(event):
    from_ = await bot.get_entity(event.sender_id)
    await event.edit(
        start_msg.format(user=from_.first_name),
        buttons=start_buttons,
        link_preview=False,
    )


@bot.on(events.CallbackQuery(data="helper"))
async def helper(event):
    await event.edit(
        '**İstifadə təlimatları.**\n\n *İstifadəçilər əlavə etmək- icazəsi ilə məni admin kimi kanalınıza əlavə edin və məni qurmaq üçün həmin çatdan mesaj göndərin!',
        buttons=Button.inline("Əsas Menyu ⚙️", data="start"),
    )


@bot.on(events.NewMessage(incoming=True, func=lambda e: e.is_private and e.fwd_from))
async def settings_selctor(event):
    id = event.fwd_from.from_id
    if not isinstance(id, types.PeerChannel):
        await event.reply("Deyəsən bu kanaldan deyil!")
        return
    try:
        chat = await bot.get_entity(id)
        if chat.admin_rights is None:
            await event.reply("Deyəsən bu kanalda admin deyiləm!")
            return
    except ValueError:
        await event.reply("Deyəsən məni kanalınıza əlavə etməmisiniz!")
        return

    # parametrləri dəyişməyə çalışan adamın admin olub olmadığını yoxlayın

    try:
        who_u = (
            await bot(
                functions.channels.GetParticipantRequest(
                    channel=chat.id,
                    participant=event.sender_id,
                )
            )
        ).participant
    except errors.rpcerrorlist.UserNotParticipantError:
        await event.reply(
            "Siz bu əməliyyatı yerinə yetirmək üçün kanalda admin deyilsiniz."
        )
        return
    if not (
        isinstance(
            who_u, (types.ChannelParticipantCreator, types.ChannelParticipantAdmin)
        )
    ):
        await event.reply(
            "Siz bu kanalın admini deyilsiniz və onun parametrlərini dəyişə bilməzsiniz!"
        )
        return

    added_chats = db.get("CHAT_SETTINGS") or "{}"
    added_chats = eval(added_chats)
    setting = added_chats.get(str(chat.id)) or "Auto-Approve"
    await event.reply(
        "**{title} üçün parametrlər**\n\nYeni qoşulma sorğularında nə edəcəyinizi seçin.\n\n**Cari parametr** - __{set}__".format(
            title=chat.title, set=setting
        ),
        buttons=[
            [Button.inline("Avtomatik Təsdiq", data="set_ap_{}".format(chat.id))],
            [
                Button.inline(
                    "Avtomatik Rədd et",
                    data="set_disap_{}".format(chat.id),
                )
            ],
        ],
    )


@bot.on(events.CallbackQuery(data=re.compile("set_(.*)")))
async def settings(event):
    args = event.pattern_match.group(1).decode("utf-8")
    setting, chat = args.split("_")
    added_chats = db.get("CHAT_SETTINGS") or "{}"
    added_chats = eval(added_chats)
    if setting == "ap":
        op = "Avtomatik Təsdiq"
        added_chats.update({chat: op})
    elif setting == "disap":
        op = "Avtomatik Rədd et"
        added_chats.update({chat: op})
    db.set("CHAT_SETTINGS", str(added_chats))
    await event.edit(
        "Parametrlər yeniləndi! `{}` kanalında yeni üzvlər {} olacaq!".format(
            chat, op
        )
    )


@bot.on(events.Raw(types.UpdateBotChatInviteRequester))
async def approver(event):
    chat = event.peer.channel_id
    chat_settings = db.get("CHAT_SETTINGS") or "{}"
    chat_settings = eval(chat_settings)
    who = await bot.get_entity(event.user_id)
    chat_ = await bot.get_entity(chat)
    if chat_settings.get(str(chat)) == "Avtomatik Təsdiq":
        appr = True
        dn = "Qəbul Olundu✅"
    elif chat_settings.get(str(chat)) == "Avtomatik Rədd et":
        appr = False
        dn = "Qəbul Olunmadı❌"
    await bot.send_message(
        event.user_id,
        "Salam {}, {}} qrupuna qoşulmaq üçün sorğunuz {}\n\nƏtraflı məlumat üçün  /start yazın.".format(
            who.first_name, chat_.title, dn
        ),
    )
    try:
        await bot(
            functions.messages.HideChatJoinRequestRequest(
                approved=appr, peer=chat, user_id=event.user_id
            )
        )
    except errors.rpcerrorlist.UserAlreadyParticipantError:
        pass


@bot.on(events.NewMessage(incoming=True, from_users=AUTH, pattern="^/stats$"))
async def auth_(event):
    t = db.get("CHAT_SETTINGS") or "{}"
    t = eval(t)
    await event.reply(
        "**Bot stats**\n\nİstifadəçilər: {}\nQruplar əlavə edildi: {}".format(
            len(get_all("BOTUSERS")), len(t.keys())
        )
    )


@bot.on(events.NewMessage(incoming=True, from_users=AUTH, pattern="^/broadcast ?(.*)"))
async def broad(e):
    msg = e.pattern_match.group(1)
    if not msg:
        return await e.reply("Zəhmət olmasa istifadə edin  `/broadcast mesaj`")
    xx = await e.reply("Davam edir...")
    users = get_all("BOTUSERS")
    done = error = 0
    for i in users:
        try:
            await bot.send_message(int(i), msg)
            done += 1
        except:
            error += 1
    await xx.edit("Yayım tamamlandı.\nUğurlu Oldu: {}\nUğursuz oldu: {}".format(done, error))


log.info("Bot Başladıldı - %s", bot_username)
log.info("\n@FarzTeam\n\nDev - @NihatFarz.")

bot.run_until_disconnected()
