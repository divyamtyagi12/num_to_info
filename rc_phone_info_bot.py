"""
rc_phone_info_bot.py - Webhook Version for Render
A Telegram bot that looks up vehicle RC info via:
    https://vvvin-ng.vercel.app/lookup?rc=<RC_NUMBER>
"""

import os
import logging
import re
import requests
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# CONFIG
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g., https://your-app.onrender.com
PORT = int(os.getenv("PORT", 10000))

RC_API_BASE = os.getenv("RC_API_BASE", "https://vvvin-ng.vercel.app/lookup?rc=")
PHONE_API_PROVIDER = os.getenv("PHONE_API_PROVIDER", "")
PHONE_API_KEY = os.getenv("PHONE_API_KEY", "")

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Simple validators
RC_REGEX = re.compile(r"^[A-Z]{2}\d{1,2}[A-Z]{1,2}\d{1,4}$", re.IGNORECASE)
PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 *RC & Phone Info Bot*\n\n"
        "• Send a vehicle registration (RC) like `MH12DE1433` to get vehicle & owner details.\n"
        "• Or send a phone number with country code like `+14155552671` (optional: requires phone API key).\n\n"
        "Examples:\n"
        "`MH12DE1433`\n"
        "`+14155552671`\n\n"
        "Made for educational/demo purposes. Use responsibly."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def format_rc_response(data: dict) -> str:
    """Build a readable message from the RC API JSON response."""
    if not data:
        return "❌ No data returned."

    lines = []
    # Ownership
    owner = data.get("owner_name") or data.get("Owner Name") or data.get("Owner") or data.get("owner")
    father = data.get("father_name") or data.get("Father Name")
    reg_no = data.get("registration_number") or data.get("Registration No") or data.get("Registration number") or data.get("reg_no")
    rto = data.get("registered_rto") or data.get("RTO")
    vehicle_model = data.get("model_name") or data.get("Model Name") or data.get("modal_name") or data.get("Modal Name")
    maker = data.get("maker_model") or data.get("Maker Model")
    vehicle_class = data.get("vehicle_class") or data.get("Vehicle Class")
    fuel = data.get("fuel_type") or data.get("Fuel Type")
    chassis = data.get("chassis_number") or data.get("Chassis Number") or data.get("Chassis No")
    engine = data.get("engine_number") or data.get("Engine Number")
    insurance_no = data.get("insurance_no") or data.get("Insurance No")
    insurance_company = data.get("insurance_company") or data.get("Insurance Company")
    insurance_expiry = data.get("insurance_expiry") or data.get("Insurance Expiry") or data.get("Insurance Upto")
    puc_no = data.get("puc_no") or data.get("PUC No")
    puc_upto = data.get("puc_upto") or data.get("PUC Upto")
    tax_upto = data.get("tax_upto") or data.get("Tax Upto")
    registration_date = data.get("registration_date") or data.get("Registration Date")
    vehicle_age = data.get("vehicle_age") or data.get("Vehicle Age")
    financer = data.get("financer_name") or data.get("Financer Name")
    seating = data.get("seating_capacity") or data.get("Seating Capacity")
    cubic_capacity = data.get("cubic_capacity") or data.get("Cubic Capacity")
    blacklist = data.get("blacklist_status") or data.get("Blacklist Status")

    lines.append("🚗 *Ownership Details*")
    if owner: lines.append(f"• *Owner:* {owner}")
    if father: lines.append(f"• *Father/Spouse:* {father}")
    if reg_no: lines.append(f"• *Registration No:* {reg_no}")
    if rto: lines.append(f"• *RTO:* {rto}")

    lines.append("\n🧰 *Vehicle Details*")
    if vehicle_model: lines.append(f"• *Model:* {vehicle_model}")
    if maker: lines.append(f"• *Maker Model:* {maker}")
    if vehicle_class: lines.append(f"• *Class:* {vehicle_class}")
    if fuel: lines.append(f"• *Fuel:* {fuel}")
    if cubic_capacity: lines.append(f"• *Cubic Capacity:* {cubic_capacity}")
    if seating: lines.append(f"• *Seating:* {seating}")
    if chassis: lines.append(f"• *Chassis No:* {chassis}")
    if engine: lines.append(f"• *Engine No:* {engine}")

    lines.append("\n📄 *Insurance & PUC*")
    if insurance_no: lines.append(f"• *Insurance No:* {insurance_no}")
    if insurance_company: lines.append(f"• *Insurance Company:* {insurance_company}")
    if insurance_expiry: lines.append(f"• *Insurance Expiry:* {insurance_expiry}")
    if puc_no: lines.append(f"• *PUC No:* {puc_no}")
    if puc_upto: lines.append(f"• *PUC Upto:* {puc_upto}")
    if tax_upto: lines.append(f"• *Tax Upto:* {tax_upto}")

    lines.append("\n🗓️ *Other*")
    if registration_date: lines.append(f"• *Registration Date:* {registration_date}")
    if vehicle_age: lines.append(f"• *Vehicle Age:* {vehicle_age}")
    if financer: lines.append(f"• *Financer:* {financer}")
    if blacklist: lines.append(f"• *Blacklist:* {blacklist}")

    expired_days = data.get("expired_days") or data.get("Expired Days")
    if expired_days:
        lines.append(f"\n⚠️ *Expired Days:* {expired_days}")

    return "\n".join(lines) if lines else "No meaningful data found in response."


async def lookup_rc(rc_number: str) -> dict:
    """Call the RC API and return JSON (or {} on failure)."""
    try:
        url = RC_API_BASE + requests.utils.quote(rc_number.strip())
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        j = resp.json()
        if isinstance(j, dict) and ("data" in j and j["data"]):
            return j["data"]
        return j
    except Exception as e:
        logger.exception("RC lookup failed")
        return {"error": str(e)}


async def lookup_phone(phone_number: str) -> dict:
    """Optional: example phone lookup (placeholder)."""
    if not PHONE_API_KEY:
        return {"error": "Phone lookup not configured."}
    try:
        if PHONE_API_PROVIDER.lower() == "numverify":
            url = f"http://apilayer.net/api/validate?access_key={PHONE_API_KEY}&number={phone_number}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        return {"error": "Provider not implemented in bot."}
    except Exception as e:
        logger.exception("Phone lookup failed")
        return {"error": str(e)}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    logger.info("Message from %s: %s", user.username or user.id, text)

    # Check if it's RC
    if RC_REGEX.match(text.replace(" ", "").upper()):
        rc = text.replace(" ", "").upper()
        await update.message.reply_text(f"🔎 Looking up RC: *{rc}* ...", parse_mode=ParseMode.MARKDOWN)
        data = await lookup_rc(rc)
        if not data:
            await update.message.reply_text("❌ No result returned from RC API.")
            return
        if data.get("error"):
            await update.message.reply_text(f"❌ RC lookup error: {data['error']}")
            return
        reply = format_rc_response(data)
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        return

    # Check if it's Phone
    if PHONE_REGEX.match(text):
        phone = text if text.startswith("+") else f"+{text}"
        await update.message.reply_text(f"🔎 Looking up Phone: *{phone}* ...", parse_mode=ParseMode.MARKDOWN)
        pdata = await lookup_phone(phone)
        if pdata.get("error"):
            await update.message.reply_text(f"❌ Phone lookup error: {pdata['error']}")
            return
        lines = []
        valid = pdata.get("valid", None)
        if valid is not None:
            lines.append(f"• *Valid:* {valid}")
        country = pdata.get("country_name") or pdata.get("country")
        if country: lines.append(f"• *Country:* {country}")
        carrier = pdata.get("carrier")
        if carrier: lines.append(f"• *Carrier:* {carrier}")
        line_type = pdata.get("line_type")
        if line_type: lines.append(f"• *Line Type:* {line_type}")
        await update.message.reply_text("\n".join(lines) or "No data found.", parse_mode=ParseMode.MARKDOWN)
        return

    await update.message.reply_text(
        "❓ I couldn't recognise that input.\n\n"
        "• Send RC like `MH12DE1433` (no spaces) or a phone like `+14155552671`.\n"
        "• Make sure RC uses letters+digits, e.g. `KA01AB1234`.",
        parse_mode=ParseMode.MARKDOWN,
    )


def main():
    if not BOT_TOKEN:
        print("ERROR: Set TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    if not WEBHOOK_URL:
        print("ERROR: Set WEBHOOK_URL environment variable (e.g., https://your-app.onrender.com)")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Set up webhook
    logger.info(f"Starting webhook on port {PORT}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )


if __name__ == "__main__":
    main()