import json  # ✅ DITAMBAHKAN (KURANG DI ASLI)
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, CallbackContext
)
from datetime import datetime

# ==============================================
# ✅ SUDAH DIGANTI SESUAI DATA KAMU!
# ==============================================
OWNER_ID = 6930821002
LOG_GROUP_ID = 5552268912
ADMIN_USERNAME = "@Kyaa671"
BOT_TOKEN = "8731920897:AAHaV5EUIjmfcrg6MVw2crHs7tX8XcP3KOA"

# File Penyimpanan
produk_file = "produk.json"
saldo_file = "saldo.json"
deposit_file = "pending_deposit.json"
riwayat_file = "riwayat.json"
statistik_file = "statistik.json"

# Link Gambar & Pembayaran (SUDAH DIATUR)
BANNER_URL = "https://ibb.co.com/6cnXkscb"
PAYMENT_TEXT = """💳 Transfer *Rp{nominal:,}* ke:
`DANA 0857-0852-5975 A.N MAIMUNAH`

Setelah transfer, kirim bukti foto transfer ke bot ini."""

# ==============================================
# FUNGSI DASAR
# ==============================================
def load_json(file):
    if not os.path.exists(file):
        return {} if file.endswith(".json") else []
    with open(file, "r") as f:
        content = f.read().strip()
        if not content:
            return {} if file.endswith(".json") else []
        return json.loads(content)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def update_statistik(uid, nominal):
    statistik = load_json(statistik_file)
    uid = str(uid)
    if uid not in statistik:
        statistik[uid] = {"jumlah": 0, "nominal": 0}
    statistik[uid]["jumlah"] += 1
    statistik[uid]["nominal"] += nominal
    save_json(statistik_file, statistik)

def add_riwayat(uid, tipe, keterangan, jumlah):
    riwayat = load_json(riwayat_file)
    if str(uid) not in riwayat:
        riwayat[str(uid)] = []
    riwayat[str(uid)].append({
        "tipe": tipe,
        "keterangan": keterangan,
        "jumlah": jumlah,
        "waktu": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })
    save_json(riwayat_file, riwayat)
    if tipe == "BELI":
        update_statistik(uid, jumlah)

async def send_logs(context, text):
    try:
        await context.bot.send_message(LOG_GROUP_ID, text, parse_mode="Markdown")
    except Exception as e:
        print(f"Gagal kirim logs: {e}")

# ==============================================
# MENU UTAMA
# ==============================================
async def send_main_menu(context, chat_id, user):
    saldo = load_json(saldo_file)
    statistik = load_json(statistik_file)
    s = saldo.get(str(user.id), 0)
    jumlah = statistik.get(str(user.id), {}).get("jumlah", 0)
    total = statistik.get(str(user.id), {}).get("nominal", 0)

    text = (
        f"👋 Selamat datang di *Store Garfield*!\n\n"
        f"🧑 Nama: {user.full_name}\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Total Saldo Kamu: Rp{s:,}\n"
        f"📦 Total Transaksi: {jumlah}\n"
        f"💸 Total Nominal Transaksi: Rp{total:,}"
    )

    keyboard = [
        [InlineKeyboardButton("📋 List Produk", callback_data="list_produk"),
         InlineKeyboardButton("🛒 Stock", callback_data="cek_stok")],
        [InlineKeyboardButton("💰 Deposit Saldo", callback_data="deposit")],
        [InlineKeyboardButton("📖 Informasi Bot", callback_data="info_bot")],
        [InlineKeyboardButton("📝 Order Langsung", callback_data="direct_order")]
    ]
    if user.id == OWNER_ID:
        keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel")])

    # Kirim Banner
    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=BANNER_URL,
            caption="🎉 Selamat datang di Store Garfield!",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Gagal kirim banner: {e}")

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def send_main_menu_safe(update, context):
    if update.message:
        await send_main_menu(context, update.effective_chat.id, update.effective_user)
    elif update.callback_query:
        try:
            await update.callback_query.message.delete()
        except:
            pass
        await send_main_menu(context, update.callback_query.from_user.id, update.callback_query.from_user)

# ==============================================
# PERBAIKAN FITUR ORDER LANGSUNG (TIDAK ERROR)
# ==============================================
async def handle_direct_order(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    text = (
        f"👋 Halo {user.full_name}!\n\n"
        "Silakan tulis detail pesanan langsung ke admin.\n"
        "Format contoh:\n"
        "`Nama Produk - Jumlah - Keterangan lain`\n\n"
        "Pesan kamu akan langsung dikirim ke admin."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Kembali", callback_data="back_to_produk")]
    ])

    await query.message.delete()
    await context.bot.send_message(
        chat_id=user.id,
        text=text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    context.user_data["direct_order"] = True

async def forward_direct_order(update: Update, context: CallbackContext):
    user = update.message.from_user
    if context.user_data.get("direct_order"):
        msg = update.message.text
        await context.bot.send_message(
            chat_id=ADMIN_USERNAME,
            text=f"📨 Pesanan baru dari {user.full_name} (ID: {user.id}):\n{msg}"
        )
        await update.message.reply_text("✅ Pesanan kamu sudah dikirim ke admin.")
        context.user_data.pop("direct_order", None)
        await send_main_menu_safe(update, context)
        return False  # Stop lanjut ke handler lain
    return True  # Lanjut ke handler lain

# ==============================================
# FITUR LAINNYA
# ==============================================
async def handle_list_produk(update: Update, context: CallbackContext):
    query = update.callback_query
    produk = load_json(produk_file)
    msg = "*LIST PRODUK*\n"
    keyboard = []
    for pid, item in produk.items():
        harga = item.get("harga", 0)
        msg += f"{pid} {item['nama']} - Rp{harga:,}\n"
        stok = len(item.get("akun_list", [])) if item.get("akun_list") else item.get("stok", 0)
        if stok > 0:
            keyboard.append([KeyboardButton(pid)])
        else:
            keyboard.append([KeyboardButton(f"{pid} SOLDOUT ❌")])
    keyboard.append([KeyboardButton("🔙 Kembali")])
    await query.message.delete()
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=msg + "\nPilih nomor produk:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="Markdown"
    )

async def handle_cek_stok(update: Update, context: CallbackContext):
    query = update.callback_query
    produk = load_json(produk_file)
    now = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
    msg = f"*Informasi Stok*\n- {now}\n\n"
    keyboard = []
    for pid, item in produk.items():
        stok = len(item.get("akun_list", [])) if item.get("akun_list") else item.get("stok", 0)
        msg += f"{pid}. {item['nama']} ➔ {stok}x\n"
        if stok > 0:
            keyboard.append([KeyboardButton(pid)])
        else:
            keyboard.append([KeyboardButton(f"{pid} SOLDOUT ❌")])
    keyboard.append([KeyboardButton("🔙 Kembali")])
    await query.message.delete()
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=msg,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="Markdown"
    )

async def handle_produk_detail(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    produk = load_json(produk_file)
    item = produk.get(data)
    if not item:
        await query.answer("Produk tidak ada", show_alert=True)
        return
    stok = len(item.get("akun_list", [])) if item.get("akun_list") else item.get("stok", 0)
    if stok <= 0:
        await query.answer("Stok habis", show_alert=True)
        return
    harga = item.get("harga", 0)
    tipe = item.get("akun_list", [{}])[0].get("tipe", "-") if item.get("akun_list") else "-"
    context.user_data["konfirmasi"] = {"produk_id": data, "jumlah": 1}
    text = (
        "KONFIRMASI PESANAN 🛒\n"
        "╭─────────────────────────────────────────────╮\n"
        f"┊・Produk: {item['nama']}\n"
        f"┊・Variasi: {tipe}\n"
        f"┊・Harga satuan: Rp. {harga:,}\n"
        f"┊・Stok tersedia: {stok}\n"
        "┊─────────────────────────────────────────────\n"
        f"┊・Jumlah Pesanan: x1\n"
        f"┊・Total Pembayaran: Rp. {harga:,}\n"
        "╰─────────────────────────────────────────────╯"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➖", callback_data="qty_minus"),
         InlineKeyboardButton("Jumlah: 1", callback_data="ignore"),
         InlineKeyboardButton("➕", callback_data="qty_plus")],
        [InlineKeyboardButton("Konfirmasi Order ✅", callback_data="confirm_order")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="back_to_produk")]
    ])
    await query.message.delete()
    await context.bot.send_message(chat_id=query.from_user.id, text=text, reply_markup=keyboard)

async def handle_deposit(update: Update, context: CallbackContext):
    query = update.callback_query
    nominals = [10000, 15000, 20000, 25000]
    keyboard = [[InlineKeyboardButton(f"Rp{n:,}", callback_data=f"deposit_{n}") for n in nominals]]
    keyboard.append([InlineKeyboardButton("🔧 Custom Nominal", callback_data="deposit_custom")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="back_to_produk")])
    await query.edit_message_text("💰 Pilih nominal deposit kamu:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_deposit_nominal(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    if data == "deposit_custom":
        context.user_data["awaiting_custom"] = True
        await query.message.delete()
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="Ketik jumlah deposit (angka saja):",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Batalkan Deposit")]], resize_keyboard=True, one_time_keyboard=True)
        )
    else:
        nominal = int(data.split("_")[1])
        context.user_data["nominal_asli"] = nominal
        context.user_data["total_transfer"] = nominal + 23
        await query.message.delete()
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=PAYMENT_TEXT.format(nominal=nominal+23),
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Batalkan Deposit")]], resize_keyboard=True, one_time_keyboard=True)
        )

async def handle_cancel_deposit(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = str(query.from_user.id)
    pending = load_json(deposit_file)
    pending = [p for p in pending if str(p["user_id"]) != uid]
    save_json(deposit_file, pending)
    await query.edit_message_text("✅ Deposit dibatalkan.")
    await send_main_menu(context, query.from_user.id, query.from_user)

async def handle_admin_panel(update: Update, context: CallbackContext):
    query = update.callback_query
    saldo = load_json(saldo_file)
    pending = load_json(deposit_file)
    text = "*📊 Data User:*\n"
    for u, s in saldo.items():
        text += f"• ID {u}: Rp{s:,}\n"
    text += "\n*⏳ Pending Deposit:*\n"
    text += "\n".join([f"- @{p['username']} ({p['user_id']}) Rp{p['nominal']:,}" for p in pending]) if pending else "Tidak ada."
    await query.edit_message_text(text, parse_mode="Markdown")

async def handle_admin_confirm(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = int(query.data.split(":")[1])
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ YA", callback_data=f"final:{user_id}")],[InlineKeyboardButton("🔙 Batal", callback_data="back")]])
    await query.edit_message_caption("Konfirmasi saldo ke user ini?", reply_markup=keyboard)

async def handle_admin_final(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = int(query.data.split(":")[1])
    pending = load_json(deposit_file)
    saldo = load_json(saldo_file)
    item = next((p for p in pending if p["user_id"] == user_id), None)
    if item:
        nominal = item["nominal"]
        saldo[str(user_id)] = saldo.get(str(user_id), 0) + nominal
        save_json(saldo_file, saldo)
        pending = [p for p in pending if p["user_id"] != user_id]
        save_json(deposit_file, pending)
        add_riwayat(user_id, "DEPOSIT", "Konfirmasi Admin", nominal)
        await query.edit_message_caption(f"✅ Saldo Rp{nominal:,} ditambahkan ke user:\n👤 @{item['username']}\n🆔 {user_id}")
        await context.bot.send_message(user_id, f"✅ Saldo Rp{nominal:,} berhasil masuk!", reply_markup=ReplyKeyboardRemove())
        await send_main_menu(context, user_id, await context.bot.get_chat(user_id))
    else:
        await query.edit_message_caption("❌ Data tidak ditemukan.")

async def handle_admin_reject(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = int(query.data.split(":")[1])
    await query.edit_message_caption("❌ Deposit ditolak.")
    await context.bot.send_message(user_id, "❌ Deposit kamu ditolak admin.", reply_markup=ReplyKeyboardRemove())

async def handle_qty_plus(update: Update, context: CallbackContext):
    query = update.callback_query
    info = context.user_data.get("konfirmasi")
    if not info: await query.answer("Data tidak ada"); return
    produk = load_json(produk_file)
    item = produk.get(info["produk_id"])
    if not item: await query.answer("Produk tidak ada"); return
    jumlah = info["jumlah"]
    stok = len(item.get("akun_list", [])) if item.get("akun_list") else item.get("stok", 0)
    if jumlah < stok: jumlah +=1
    context.user_data["konfirmasi"]["jumlah"] = jumlah
    total = jumlah * item["harga"]
    tipe = item["akun_list"][0]["tipe"] if item.get("akun_list") else "-"
    text = (
        "KONFIRMASI PESANAN 🛒\n"
        "╭─────────────────────────────────────────────╮\n"
        f"┊・Produk: {item['nama']}\n┊・Variasi: {tipe}\n┊・Harga: Rp{item['harga']:,}\n┊・Stok: {stok}\n"
        "┊─────────────────────────────────────────────\n"
        f"┊・Jumlah: x{jumlah}\n┊・Total: Rp{total:,}\n"
        "╰─────────────────────────────────────────────╯"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("➖",callback_data="qty_minus"),InlineKeyboardButton(f"Jumlah:{jumlah}",callback_data="ignore"),InlineKeyboardButton("➕",callback_data="qty_plus")],[InlineKeyboardButton("Konfirmasi ✅",callback_data="confirm_order")],[InlineKeyboardButton("🔙 Kembali",callback_data="back_to_produk")]])
    await query.edit_message_text(text,reply_markup=kb)

async def handle_qty_minus(update: Update, context: CallbackContext):
    query = update.callback_query
    info = context.user_data.get("konfirmasi")
    if not info: await query.answer("Data tidak ada"); return
    produk = load_json(produk_file)
    item = produk.get(info["produk_id"])
    if not item: await query.answer("Produk tidak ada"); return
    jumlah = info["jumlah"]
    if jumlah>1: jumlah -=1
    context.user_data["konfirmasi"]["jumlah"] = jumlah
    total = jumlah * item["harga"]
    tipe = item["akun_list"][0]["tipe"] if item.get("akun_list") else "-"
    text=(
        "KONFIRMASI PESANAN 🛒\n╭─────────────────────────────────────────────╮\n"
        f"┊・Produk: {item['nama']}\n┊・Variasi: {tipe}\n┊・Harga: Rp{item['harga']:,}\n┊・Stok: {len(item.get('akun_list',[])) or item.get('stok',0)}\n"
        "┊─────────────────────────────────────────────\n"
        f"┊・Jumlah: x{jumlah}\n┊・Total: Rp{total:,}\n╰─────────────────────────────────────────────╯"
    )
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("➖",callback_data="qty_minus"),InlineKeyboardButton(f"Jumlah:{jumlah}",callback_data="ignore"),InlineKeyboardButton("➕",callback_data="qty_plus")],[InlineKeyboardButton("Konfirmasi ✅",callback_data="confirm_order")],[InlineKeyboardButton("🔙 Kembali",callback_data="back_to_produk")]])
    await query.edit_message_text(text,reply_markup=kb)

async def handle_confirm_order(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = str(query.from_user.id)
    produk = load_json(produk_file)
    saldo = load_json(saldo_file)
    info = context.user_data.get("konfirmasi")
    if not info: await query.answer("❌ Data hilang",show_alert=True); return
    item = produk.get(info["produk_id"])
    if not item: await query.edit_message_text("❌ Produk tidak ada"); return
    jumlah = info["jumlah"]
    total = jumlah * item["harga"]
    stok = len(item.get("akun_list", [])) if item.get("akun_list") else item.get("stok", 0)
    if saldo.get(uid,0) < total:
        kb=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Deposit",callback_data="deposit")],[InlineKeyboardButton("🔙 Kembali",callback_data="back_to_produk")]])
        await query.edit_message_text("❌ *Saldo tidak cukup!*",parse_mode="Markdown",reply_markup=kb); return
    if stok < jumlah: await query.edit_message_text("❌ Stok habis!"); return
    saldo[uid] -= total
    if item.get("akun_list"):
        akun_terpakai = [item["akun_list"].pop(0) for _ in range(jumlah)]
    else:
        item["stok"] -= jumlah
        akun_terpakai = [{"username":"Umum","password":"-"}]*jumlah
    save_json(saldo_file, saldo)
    save_json(produk_file, produk)
    add_riwayat(uid, "BELI", f"{item['nama']} x{jumlah}", total)
    os.makedirs("akun_dikirim", exist_ok=True)
    fp = f"akun_dikirim/{uid}_{info['produk_id']}.txt"
    with open(fp,"w") as f:
        for i,a in enumerate(akun_terpakai,1):
            f.write(f"Akun #{i}\nUser: {a.get('username','-')}\nPass: {a.get('password','-')}\nTipe: {a.get('tipe','-')}\n----------------\n")
    with open(fp,"rb") as f:
        await context.bot.send_document(query.from_user.id, InputFile(f), caption=f"✅ Berhasil beli *{item['nama']}* x{jumlah}\nSisa saldo: Rp{saldo[uid]:,}",parse_mode="Markdown")
    await send_logs(context,f"📦 TRANSAKSI\nUser: {query.from_user.full_name} ({uid})\nProduk: {item['nama']} x{jumlah}\nTotal: Rp{total:,}\nSisa: Rp{saldo[uid]:,}")
    context.user_data.pop("konfirmasi",None)
    await send_main_menu(context, query.from_user.id, query.from_user)

async def handle_back(update: Update, context: CallbackContext):
    await update.callback_query.edit_message_caption("✅ Dibatalkan.")

async def handle_back_to_produk(update: Update, context: CallbackContext):
    await update.callback_query.message.delete()
    await send_main_menu_safe(update, context)

async def handle_info_bot(update: Update, context: CallbackContext):
    q=update.callback_query
    text="""📖 *INFORMASI BOT*
╽─────────────────────────────╮
├ 🧠 *Nama Bot*: `Store GARFIELD`
├ 👨‍💻 *Author*: [@Brsik23](https://t.me/storegarf)
├ 🛒 *Fungsi*: Penjualan akun digital otomatis
├ ⚙️ *Fitur*: Deposit, Pengiriman Akun, Statistik
├ 🧰 *Teknologi*: Python, Telegram Bot API
╰─────────────────────────────╯

🌐 *Sosial Media Developer:*
💬 Hubungi [@Brsik23](https://t.me/storegarf)"""
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali",callback_data="back_to_produk")]])
    await q.edit_message_text(text,parse_mode="Markdown",disable_web_page_preview=True,reply_markup=kb)

async def handle_ignore(update: Update, context: CallbackContext):
    await update.callback_query.answer()

# ==============================================
# HANDLER TEKS & FOTO
# ==============================================
async def handle_text(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    uid = str(update.effective_user.id)
    if text == "❌ Batalkan Deposit":
        pending = load_json(deposit_file)
        pending = [p for p in pending if str(p["user_id"]) != uid]
        save_json(deposit_file, pending)
        await update.message.reply_text("✅ Deposit dibatalkan.", reply_markup=ReplyKeyboardRemove())
        await send_main_menu_safe(update, context)
        return
    if context.user_data.get("awaiting_custom"):
        try:
            nominal = int(text)
            context.user_data["awaiting_custom"] = False
            context.user_data["nominal_asli"] = nominal
            context.user_data["total_transfer"] = nominal + 23
            await update.message.reply_text(PAYMENT_TEXT.format(nominal=nominal+23), parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Batalkan Deposit")]], resize_keyboard=True))
        except:
            await update.message.reply_text("❌ Harus angka saja!")
        return
    produk = load_json(produk_file)
    if text in produk:
        item = produk[text]
        stok = len(item.get("akun_list", [])) if item.get("akun_list") else item.get("stok", 0)
        if stok <= 0:
            await update.message.reply_text("❌ Stok habis!")
            await send_main_menu_safe(update, context)
            return
        context.user_data["konfirmasi"] = {"produk_id": text, "jumlah":1}
        txt = (
            f"KONFIRMASI 🛒\n╭─────────────────────────────╮\n┊・{item['nama']}\n┊・Harga: Rp{item['harga']:,}\n┊・Stok: {stok}\n"
            "┊─────────────────────────────\n┊・Jumlah: x1\n┊・Total: Rp{item['harga']:,}\n╰─────────────────────────────╯"
        )
        kb=InlineKeyboardMarkup([[InlineKeyboardButton("➖",callback_data="qty_minus"),InlineKeyboardButton("1",callback_data="ignore"),InlineKeyboardButton("➕",callback_data="qty_plus")],[InlineKeyboardButton("✅ Beli",callback_data="confirm_order")],[InlineKeyboardButton("🔙 Kembali",callback_data="back_to_produk")]])
        await update.message.reply_text(txt,reply_markup=kb)
        return
    if text == "🔙 Kembali":
        await send_main_menu_safe(update, context)
        return

async def handle_photo(update: Update, context: CallbackContext):
    user = update.effective_user
    ph = update.message.photo[-1]
    file = await context.bot.get_file(ph.file_id)
    os.makedirs("bukti", exist_ok=True)
    path = f"bukti/{user.id}.jpg"
    await file.download_to_drive(path)
    nominal = context.user_data.get("nominal_asli",0)
    total = context.user_data.get("total_transfer", nominal)
    pending = load_json(deposit_file)
    pending.append({"user_id":user.id,"username":user.username,"bukti_path":path,"nominal":nominal,"total_transfer":total})
    save_json(deposit_file, pending)
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Konfirmasi",callback_data=f"confirm:{user.id}")],[InlineKeyboardButton("❌ Tolak",callback_data=f"reject:{user.id}")]])
    with open(path,"rb") as f:
        await context.bot.send_photo(OWNER_ID, InputFile(f), caption=f"📥 Deposit @{user.username}\nTransfer: Rp{total:,}\nMasuk: Rp{nominal:,}",reply_markup=kb)
    await update.message.reply_text("✅ Bukti dikirim! Tunggu konfirmasi admin.")

# ==============================================
# PENGATURAN TOMBOL & MENU
# ==============================================
callback_map = {
    "list_produk": handle_list_produk,
    "cek_stok": handle_cek_stok,
    "info_bot": handle_info_bot,
    "deposit": handle_deposit,
    "deposit_custom": handle_deposit_nominal,
    "cancel_deposit": handle_cancel_deposit,
    "admin_panel": handle_admin_panel,
    "qty_plus": handle_qty_plus,
    "qty_minus": handle_qty_minus,
    "confirm_order": handle_confirm_order,
    "back": handle_back,
    "back_to_produk": handle_back_to_produk,
    "ignore": handle_ignore,
    "direct_order": handle_direct_order
}

async def button_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    await q.answer()
    data = q.data
    produk = load_json(produk_file)
    if data in produk:
        await handle_produk_detail(update, context)
    elif data.startswith("deposit_"):
        await handle_deposit_nominal(update, context)
    elif data.startswith("confirm:"):
        await handle_admin_confirm(update, context)
    elif data.startswith("final:"):
        await handle_admin_final(update, context)
    elif data.startswith("reject:"):
        await handle_admin_reject(update, context)
    elif data in callback_map:
        await callback_map[data](update, context)
    else:
        await q.edit_message_text("❌ Tidak dikenal.")

async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    await send_logs(context, f"👤 USER MULAI\nNama: {user.full_name}\nID: {user.id}\nWaktu: {datetime.now()}")
    await send_main_menu(context, update.effective_chat.id, user)

# ==============================================
# JALANKAN BOT
# ==============================================
def main():
    # Buat file kosong kalau belum ada
    for f in [produk_file, saldo_file, deposit_file, riwayat_file, statistik_file]:
        if not os.path.exists(f):
            save_json(f, {} if f != deposit_file else [])
    os.makedirs("akun_dikirim", exist_ok=True)
    os.makedirs("bukti", exist_ok=True)

    app = Application.builder().token(BOT_TOKEN).build()

    # Daftar Urutan Handler (PENTING)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_direct_order))  # Pesan ke admin DULU
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))          # Pesan biasa
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🤖 Bot Store Garfield Berjalan!")
    app.run_polling()

if __name__ == "__main__":
    main()
