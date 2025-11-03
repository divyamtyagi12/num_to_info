import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import requests
import re

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = "8387493035:AAGU5jshpvyxL5E9M0ajiFKDxw5oF_34gyI"
RC_API_URL = "https://vvvin-ng.vercel.app/lookup?rc="

class InfoBot:
    def __init__(self):
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up command and message handlers"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(CommandHandler("phone", self.phone_help))
        self.app.add_handler(CommandHandler("rc", self.rc_help))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_input))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message with options"""
        keyboard = [
            [
                InlineKeyboardButton("📞 Phone Lookup", callback_data="help_phone"),
                InlineKeyboardButton("🚗 RC Lookup", callback_data="help_rc")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = """
🔥 *Welcome to Info Lookup Bot!* ❤️

I can help you with:

📞 *Phone Number Lookup*
Get detailed information about any phone number

🚗 *Vehicle RC Lookup*
Get complete vehicle registration details

👇 Choose an option below or send:
• Phone number (e.g., +919876543210)
• RC number (e.g., MH12DE1433)

Use /help for detailed instructions.
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "help_phone":
            await self.phone_help(update, context, is_callback=True)
        elif query.data == "help_rc":
            await self.rc_help(update, context, is_callback=True)
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send general help message"""
        help_text = """
ℹ️ *How to use this bot:*

*📞 Phone Number Lookup:*
Send any phone number with country code
Example: +919876543210, +1-555-123-4567

*🚗 Vehicle RC Lookup:*
Send vehicle registration number
Example: MH12DE1433, DL01AB1234

*Commands:*
/start - Main menu
/help - This help message
/phone - Phone lookup help
/rc - RC lookup help

⚠️ *Disclaimer:*
This bot provides information for educational purposes only. Users are responsible for their actions.
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def phone_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
        """Phone lookup help"""
        text = """
📞 *Phone Number Lookup Help*

*Supported formats:*
• +919876543210
• +1 (555) 123-4567
• +44 20 7946 0958

*Information provided:*
✓ Country & Region
✓ Carrier/Operator
✓ Line Type (Mobile/Fixed/VoIP)
✓ Timezone
✓ Validity Status
✓ Formatted Numbers

Just send a phone number to get started!
        """
        if is_callback:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
    
    async def rc_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
        """RC lookup help"""
        text = """
🚗 *Vehicle RC Lookup Help*

*Example formats:*
• MH12DE1433
• DL01AB1234
• KA01MN5678

*Information provided:*
🚗 Ownership Details
🧰 Vehicle Specifications
📄 Insurance Information
🗓 Important Dates
🚫 Blacklist Status
📁 NOC Details

Just send a vehicle registration number!

⚠️ *Note:* Information is for educational purposes only.
        """
        if is_callback:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, parse_mode='Markdown')
    
    def is_phone_number(self, text):
        """Check if text is a phone number"""
        # Check if it starts with + or contains only digits and common phone chars
        return bool(re.match(r'^[\+\d][\d\s\-\(\)]+$', text)) and len(re.sub(r'[^\d]', '', text)) >= 7
    
    def is_rc_number(self, text):
        """Check if text is an RC number"""
        # Indian RC format: 2 letters, 2 digits, 2 letters/digits, 4 digits
        return bool(re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]{1,2}\d{4}$', text.upper()))
    
    async def handle_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user input and determine type"""
        user_input = update.message.text.strip()
        
        # Check if it's an RC number first (more specific pattern)
        if self.is_rc_number(user_input):
            await self.handle_rc_lookup(update, user_input)
        elif self.is_phone_number(user_input):
            await self.handle_phone_lookup(update, user_input)
        else:
            await update.message.reply_text(
                "❌ Invalid input!\n\n"
                "Please send:\n"
                "📞 Phone number (e.g., +919876543210)\n"
                "🚗 RC number (e.g., MH12DE1433)\n\n"
                "Use /help for more information."
            )
    
    async def handle_phone_lookup(self, update: Update, phone_number: str):
        """Handle phone number lookup"""
        processing_msg = await update.message.reply_text("🔍 Analyzing phone number...")
        
        try:
            parsed = phonenumbers.parse(phone_number, None)
            is_valid = phonenumbers.is_valid_number(parsed)
            is_possible = phonenumbers.is_possible_number(parsed)
            
            country = geocoder.description_for_number(parsed, "en")
            carrier_name = carrier.name_for_number(parsed, "en")
            timezones = timezone.time_zones_for_number(parsed)
            number_type = phonenumbers.number_type(parsed)
            
            type_map = {
                0: "Fixed Line", 1: "Mobile", 2: "Fixed Line or Mobile",
                3: "Toll Free", 4: "Premium Rate", 5: "Shared Cost",
                6: "VoIP", 7: "Personal Number", 8: "Pager",
                9: "UAN", 10: "Voicemail", 99: "Unknown"
            }
            line_type = type_map.get(number_type, "Unknown")
            
            response = f"""
📞 *Phone Number Information*

*Formatted Numbers:*
• International: `{phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)}`
• National: `{phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)}`
• E.164: `{phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)}`

*Details:*
🌍 Country: {country if country else 'Unknown'}
📱 Country Code: +{parsed.country_code}
📡 Carrier: {carrier_name if carrier_name else 'Unknown'}
📞 Line Type: {line_type}
🕐 Timezone: {', '.join(timezones) if timezones else 'Unknown'}

*Validation:*
✓ Valid: {'Yes ✅' if is_valid else 'No ❌'}
✓ Possible: {'Yes ✅' if is_possible else 'No ❌'}

🚀 Made by Info Lookup Bot
            """
            
            await processing_msg.edit_text(response, parse_mode='Markdown')
            
        except Exception as e:
            await processing_msg.edit_text(
                f"❌ *Error analyzing phone number*\n\n"
                f"Please make sure to include country code (e.g., +91, +1, +44)",
                parse_mode='Markdown'
            )
    
    async def handle_rc_lookup(self, update: Update, rc_number: str):
        """Handle RC number lookup"""
        processing_msg = await update.message.reply_text("🔍 Fetching vehicle information...")
        
        try:
            response = requests.get(f"{RC_API_URL}{rc_number.upper()}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we have valid data (check for key fields)
                if data.get('registration_number') or data.get('Ownership Details'):
                    result = data
                    
                    # Extract nested data
                    ownership = result.get('Ownership Details', {})
                    vehicle = result.get('Vehicle Details', {})
                    insurance = result.get('Insurance Information', {})
                    dates = result.get('Important Dates & Validity', {})
                    other = result.get('Other Information', {})
                    
                    message = f"""
🚗 *Vehicle Registration Details*

*🔢 Registration:* `{rc_number.upper()}`

*🚗 Ownership Details:*
😀 Owner: {ownership.get('Owner Name', 'N/A')}
👨‍👨‍👦‍👦 Father: {ownership.get("Father's Name", 'N/A')}
🔢 Serial: {ownership.get('Owner Serial No', 'N/A')}
🏢 RTO: {ownership.get('Registered RTO', 'N/A')}

*🧰 Vehicle Details:*
🚘 Model: {vehicle.get('Maker Model', 'N/A')}
🏭 Maker: {vehicle.get('Model Name', 'N/A')}
💎 Class: {vehicle.get('Vehicle Class', 'N/A')}
🧤 Fuel: {vehicle.get('Fuel Type', 'N/A')}
☃️ Norms: {vehicle.get('Fuel Norms', 'N/A')}
🔩 Chassis: {vehicle.get('Chassis Number', 'N/A')}
🧠 Engine: {vehicle.get('Engine Number', 'N/A')}

*📄 Insurance:*
🧝 Expiry: {insurance.get('Insurance Expiry', 'N/A')}
🔖 Policy: {insurance.get('Insurance No', 'N/A')}
🏢 Company: {insurance.get('Insurance Company', 'N/A')}

*🗓 Important Dates:*
👑 Reg Date: {dates.get('Registration Date', 'N/A')}
⏳ Age: {dates.get('Vehicle Age', 'N/A')}
😀 Tax Upto: {dates.get('Tax Upto', 'N/A')}
🧾 Fitness: {dates.get('Fitness Upto', 'N/A')}
🗓️ PUC: {dates.get('PUC Upto', 'N/A')}

*🛍 Other Info:*
😀 Financer: {other.get('Financer Name', 'N/A')}
⚙️ CC: {other.get('Cubic Capacity', 'N/A')}
👥 Seats: {other.get('Seating Capacity', 'N/A')}
🚫 Blacklist: {other.get('Blacklist Status', 'N/A')}

🚀 Made by Info Lookup Bot

⚠️ *Disclaimer:* Information for educational purposes only.
                    """
                    
                    await processing_msg.edit_text(message, parse_mode='Markdown')
                else:
                    await processing_msg.edit_text(
                        f"❌ No information found for RC: `{rc_number.upper()}`\n\n"
                        f"Please verify the registration number and try again.",
                        parse_mode='Markdown'
                    )
            else:
                await processing_msg.edit_text(
                    "❌ API Error. Please try again later.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"RC Lookup error: {e}")
            await processing_msg.edit_text(
                "❌ *Error fetching vehicle information*\n\n"
                "Please check the RC number and try again.",
                parse_mode='Markdown'
            )
    
    def run(self):
        """Start the bot"""
        logger.info("Bot started successfully...")
        print("✅ Bot is running! Press Ctrl+C to stop.")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    print("🚀 Starting Info Lookup Bot...")
    print("📞 Phone lookup enabled")
    print("🚗 RC lookup enabled")
    print("\n📦 Make sure you have installed:")
    print("   pip install python-telegram-bot phonenumbers requests")
    print("\n" + "="*50)
    
    bot = InfoBot()
    bot.run()