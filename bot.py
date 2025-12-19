import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, 
    BufferedInputFile, 
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery 
)
from PIL import Image, ImageDraw, ImageFont, ImageOps
import qrcode
import io
from datetime import datetime, timedelta
import requests
import random 
import re 
import json
import os 

# ============================
# CONFIGURATION
# ============================
# --- YOUR UPDATED TOKEN ---
BOT_TOKEN = "8508303764:AAEJGIWOU4P31FH4WDV3Hi_tYL6mLypg9GE" 
# NOTE: !!! REPLACE THIS WITH YOUR ACTUAL TELEGRAM USER ID !!!
ADMIN_ID = 401413271 
# NOTE: Ensure 'my_epsa_logo.png' exists in the same directory as this script.
EPSA_LOGO_PATH = "my_epsa_logo.png" 

# --- Brand Colors (Professional Theme) ---
EPSA_BLUE = "#003366"   # Dark Navy Blue
EPSA_GOLD = "#D4AF37"   # Metallic Gold
WHITE = "#FFFFFF"
OFF_WHITE = "#F8F9FA"   # Slight grey for background
TEXT_DARK = "#2C3E50"   # Dark Slate Grey for text
TEXT_LIGHT = "#7F8C8D"  # Grey for labels
SUSPENDED_RED = "#CC0000" # Red for suspension stamp

# --- Dimensions ---
CARD_WIDTH, CARD_HEIGHT = 1000, 600
CORNER_RADIUS = 30 
PHOTO_CORNER_RADIUS = 20

# --- REGION MAPPING ---
REGION_MAP = {
    "Addis Ababa": "AA", "Afar": "AF", "Amhara": "AM", 
    "Benishangul-Gumuz": "BG", "Central Ethiopia": "CE", "Dire Dawa": "DD", 
    "Gambella": "GM", "Harari": "HR", "Oromia": "OR", 
    "Sidama": "SD", "Somali": "SM", "South Ethiopia": "SE", 
    "South West Ethiopia": "SWE", "Tigray": "TG"
}

# Regex pattern for the structured ID: EPSA-2Letters-2Digits-4Digits
STRUCTURED_ID_PATTERN = re.compile(r"^EPSA-([A-Z]{2})-(\d{2})-(\d{4})$", re.IGNORECASE)

# ============================

# Global Data Stores (In-memory storage for demonstration)
user_data = {}
verification_mode = {}
admin_reject_mode = {} 
admin_suspension_mode = {} 
admin_contact_mode = {} 

DATA_FILE = 'user_data.json'

def load_data():
    global user_data
    if os.path.exists(DATA_FILE):
        try:
            loaded_data = json.load(open(DATA_FILE, 'r'))
            user_data = {int(k): v for k, v in loaded_data.items()}
        except:
            user_data = {}

def save_data():
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(user_data, f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

# Load data at startup
load_data() 

# --------------------------
# Image Generation Helper Functions 
# --------------------------

def draw_rounded_rectangle(draw, xy, radius, fill=None, outline=None, width=0):
    # Function to draw a proper rounded rectangle
    x1, y1, x2, y2 = xy
    draw.rectangle([(x1 + radius, y1), (x2 - radius, y2)], fill=fill, outline=outline, width=width)
    draw.rectangle([(x1, y1 + radius), (x2, y2 - radius)], fill=fill, outline=outline, width=width)
    draw.pieslice([(x1, y1), (x1 + 2*radius, y1 + 2*radius)], 180, 270, fill=fill, outline=outline, width=width)
    draw.pieslice([(x2 - 2*radius, y1), (x2, y1 + 2*radius)], 270, 360, fill=fill, outline=outline, width=width)
    draw.pieslice([(x1, y2 - 2*radius), (x1 + 2*radius, y2)], 90, 180, fill=fill, outline=outline, width=width)
    draw.pieslice([(x2 - 2*radius, y2 - 2*radius), (x2, y2)], 0, 90, fill=fill, outline=outline, width=width)

def generate_id(user_id, data, bot: Bot, is_suspended=False):
    # --- GET STRUCTURED MEMBER ID COMPONENTS ---
    region_code = data.get('region_code', 'XX')
    
    if data.get('membership_status') == "Current Student":
        year_code = str(data.get('year', '00')).zfill(2)
    else: # Recent Graduate
        grad_year_str = str(data.get('graduation_year', '00'))
        year_code = grad_year_str[-2:].zfill(2)
        
    random_part = data.get('random_id_suffix', '0000') 
    member_id_display = f"EPSA-{region_code}-{year_code}-{random_part}"
    
    # Create image
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), color=OFF_WHITE)
    draw = ImageDraw.Draw(img)

    # Load Fonts 
    def get_font(size, bold=False):
        try:
            # Assumes standard system fonts for portability
            font_name = "arialbd.ttf" if bold else "arial.ttf"
            return ImageFont.truetype(font_name, size)
        except:
            return ImageFont.load_default()

    font_header = get_font(46, bold=True) 
    font_subheader = get_font(28, bold=True)
    font_name = get_font(40, bold=True)
    font_label = get_font(22, bold=False)
    font_value = get_font(26, bold=True)
    font_id_main = get_font(34, bold=True)
    font_date_sub = get_font(20, bold=False) # For date labels

    # --- 1. BACKGROUND WATERMARK ---
    try:
        bg_logo = Image.open(EPSA_LOGO_PATH).convert("RGBA")
        bg_logo = bg_logo.resize((600, 600))
        data_alpha = bg_logo.getdata()
        new_data = []
        for item in data_alpha:
            new_data.append((item[0], item[1], item[2], int(item[3] * 0.05))) 
        bg_logo.putdata(new_data)
        bg_x = (CARD_WIDTH - 600) // 2
        bg_y = (CARD_HEIGHT - 600) // 2
        img.paste(bg_logo, (bg_x, bg_y), bg_logo)
    except: pass

    # --- 2. HEADER ---
    draw.rectangle([(0, 0), (CARD_WIDTH, 140)], fill=EPSA_BLUE)
    draw.rectangle([(0, 140), (CARD_WIDTH, 150)], fill=EPSA_GOLD)
    
    try:
        logo = Image.open(EPSA_LOGO_PATH).convert("RGBA")
        logo.thumbnail((110, 110))
        img.paste(logo, (40, 15), logo)
    except:
        draw.text((40, 40), "EPSA", fill=WHITE, font=font_header)

    # Header Text
    draw.text((155, 35), "ETHIOPIAN PSYCHOLOGY", fill=WHITE, font=font_header)
    draw.text((155, 90), "STUDENTS' ASSOCIATION", fill=EPSA_GOLD, font=font_subheader)

    # --- 3. PHOTO PLACEHOLDER ---
    photo_w, photo_h = 220, 270
    photo_x, photo_y = 730, 180
    draw_rounded_rectangle(draw, (photo_x-5, photo_y-5, photo_x+photo_w+5, photo_y+photo_h+5), 
                           PHOTO_CORNER_RADIUS, fill=None, outline=EPSA_GOLD, width=5)
    draw.text((photo_x + 50, photo_y + 120), "PHOTO", fill=TEXT_LIGHT, font=font_label)

    # --- 4. DATA SECTION (UPDATED WITH COMBINED ACAD. LEVEL) ---
    start_x = 50
    start_y = 190
    line_spacing = 65
    
    draw.text((start_x, start_y), data.get('full_name', 'N/A').upper(), fill=TEXT_DARK, font=font_name)
    status = data.get('membership_status', 'Member')
    draw.text((start_x, start_y + 50), status, fill=EPSA_BLUE, font=font_subheader)

    grid_y = start_y + 110
    
    # --- COMBINE ACADEMIC LEVEL AND YEAR/GRADUATION YEAR ---
    acad_level = data.get('education_level', 'N/A')
    
    if data.get('membership_status') == "Current Student":
        # Format: Bachelor's Degree (4th Year)
        year = data.get('year', 'N/A')
        acad_detail = f" ({year}th Year)" if year.isdigit() else ""
        formatted_acad_level = f"{acad_level}{acad_detail}"
        
    else: # Graduated within 3 years
        # Format: Master's Degree (Grad. 2023)
        grad_year = data.get('graduation_year', 'N/A')
        acad_detail = f" (Grad. {grad_year})" if grad_year.isdigit() else ""
        formatted_acad_level = f"{acad_level}{acad_detail}"

    # Define the fields (Now only 3 lines of data in this section)
    fields = [
        ("UNIVERSITY", data.get('university', 'N/A')),
        ("REGION", data.get('region', 'N/A')),
        ("ACAD. LEVEL", formatted_acad_level), # Combined field
    ]
        
    # Draw the fields
    for label, value in fields:
        draw.text((start_x, grid_y), label, fill=TEXT_LIGHT, font=font_label)
        draw.text((start_x + 180, grid_y), str(value), fill=TEXT_DARK, font=font_value)
        grid_y += line_spacing

    # --- 5. FOOTER (ADJUSTED POSITION) ---
    # Moved up by 40px compared to the original design
    FOOTER_START_Y = grid_y - 10 
    
    # Draw the blue rectangle 
    draw.rectangle([(0, FOOTER_START_Y), (CARD_WIDTH, CARD_HEIGHT)], fill=EPSA_BLUE)
    
    # ID Number (Left)
    draw.text((40, FOOTER_START_Y + 25), "ID NUMBER:", fill=EPSA_GOLD, font=font_subheader) 
    ID_NUMBER_Y = FOOTER_START_Y + 55 # Base Y-coordinate for main text alignment
    draw.text((40, ID_NUMBER_Y), member_id_display, fill=WHITE, font=font_id_main)
    
    # Dates (Right - SPACING ADJUSTED TO 23px)
    issue_date = datetime.now().strftime("%d-%b-%Y").upper()
    expiry_date = (datetime.now() + timedelta(days=365)).strftime("%d-%b-%Y").upper()

    issue_x_pos = 600
    expiry_x_pos = 780 
    
    # Label is now 23px above the main text line (was 35px)
    TEXT_ALIGN_Y_LABEL = ID_NUMBER_Y - 23 
    TEXT_ALIGN_Y_VALUE = ID_NUMBER_Y      # Value is aligned with the ID number

    # Draw ISSUE Date
    draw.text((issue_x_pos, TEXT_ALIGN_Y_LABEL), "ISSUED:", fill=EPSA_GOLD, font=font_date_sub)
    draw.text((issue_x_pos, TEXT_ALIGN_Y_VALUE), issue_date, fill=WHITE, font=font_label)
    
    # Draw EXPIRES Date
    draw.text((expiry_x_pos, TEXT_ALIGN_Y_LABEL), "EXPIRES:", fill=EPSA_GOLD, font=font_date_sub)
    draw.text((expiry_x_pos, TEXT_ALIGN_Y_VALUE), expiry_date, fill=WHITE, font=font_label)


    # --- 6. QR CODE (MOVED FURTHER UP) ---
    qr_data = f"ID:{user_id}" 
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=EPSA_BLUE, back_color="white").convert("RGB")
    qr_img = qr_img.resize((100, 100))
    
    qr_x = 600
    # Adjusted from FOOTER_START_Y - 95 to FOOTER_START_Y - 110 (this placement remains from previous request)
    qr_y = FOOTER_START_Y - 110 
    img.paste(qr_img, (qr_x, qr_y)) 
    
    # --- 7. SUSPENDED STAMP ---
    if is_suspended:
        try:
            stamp_draw = ImageDraw.Draw(img)
            stamp_font = get_font(120, bold=True) 
            stamp_text = "SUSPENDED"
            
            text_w, text_h = stamp_draw.textbbox((0, 0), stamp_text, font=stamp_font)[2:] 
            
            stamp_layer = Image.new('RGBA', (text_w, text_h), (255, 255, 255, 0))
            stamp_layer_draw = ImageDraw.Draw(stamp_layer)
            stamp_layer_draw.text((0, 0), stamp_text, font=stamp_font, fill=(int('CC', 16), 0, 0, 180))
            
            rotated_stamp = stamp_layer.rotate(20, expand=1)
            
            stamp_x = (CARD_WIDTH - rotated_stamp.width) // 2
            stamp_y = (CARD_HEIGHT - rotated_stamp.height) // 2
            
            img.paste(rotated_stamp, (stamp_x - 50, stamp_y + 30), rotated_stamp)

        except Exception as e:
            print(f"Error applying suspended stamp: {e}")


    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio


async def get_user_photo_bytes(bot: Bot, file_id: str) -> io.BytesIO | None:
    """Downloads the user's photo from Telegram."""
    try:
        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
        
        response = requests.get(file_url)
        response.raise_for_status()

        photo_bio = io.BytesIO(response.content)
        return photo_bio
    except Exception as e:
        print(f"Error fetching user photo {file_id}: {e}")
        return None

async def draw_photo_on_id(base_img_bio: io.BytesIO, photo_bio: io.BytesIO):
    """Pastes the user's photo onto the generated ID card image."""
    base_img_bio.seek(0)
    id_img = Image.open(base_img_bio).convert("RGB")
    
    # Must match coordinates in generate_id
    x, y, w, h = 730, 180, 220, 270

    user_photo = Image.open(photo_bio).convert("RGB")
    user_photo = ImageOps.fit(user_photo, (w, h), centering=(0.5, 0.5))
    
    # Mask
    mask = Image.new('L', (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    draw_rounded_rectangle(mask_draw, (0, 0, w, h), PHOTO_CORNER_RADIUS, fill=255)
    
    user_photo = user_photo.convert("RGBA")
    user_photo.putalpha(mask) 

    id_img.paste(user_photo, (x, y), user_photo)

    final_bio = io.BytesIO()
    id_img = id_img.convert("RGB")
    id_img.save(final_bio, format="PNG")
    final_bio.seek(0)
    return final_bio


# --------------------------
# Inline Keyboard Helper Functions
# --------------------------
def get_admin_action_keyboard(user_id):
    """Creates inline keyboard for Approve/Reject actions."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}")
        ]
    ])
    return keyboard

def get_suspension_keyboard(user_id, is_currently_suspended):
    """Creates inline keyboard for Suspension/Reactivation actions."""
    if is_currently_suspended:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Reactivate Membership", callback_data=f"reactivate_{user_id}")]
        ])
    else:
        keyboard = InlineKeyboardButton(text="🔴 Suspend/Remove Membership", callback_data=f"suspend_{user_id}")
        # Group with an empty button to prevent single button full-width style if desired, or just use a single row
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[keyboard]])
    return keyboard

def get_done_keyboard(action, uid, reason=None):
    """Creates a keyboard showing the completed action."""
    text = f"{action} ID {uid}"
    if reason:
        text += f" (Reason: {reason[:30]}{'...' if len(reason) > 30 else ''})"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data="done_action")]
    ])
    return keyboard

def get_manage_id_keyboard():
    """Creates inline keyboard for user to manage their ID."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Delete My Digital ID", callback_data="delete_id_confirm")]
    ])
    return keyboard


# --------------------------
# Main Bot Logic
# --------------------------
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # --- Menu Keyboards ---
    main_menu = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Register"), KeyboardButton(text="🔍 Verify ID")], 
        [KeyboardButton(text="📞 Contact Admin"), KeyboardButton(text="⚙️ Manage ID/Delete")] 
    ], resize_keyboard=True)
    
    admin_menu = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Register"), KeyboardButton(text="🔍 Verify ID")], 
        [KeyboardButton(text="📋 View Pending Registrations"), KeyboardButton(text="👥 View All Members")], 
        [KeyboardButton(text="📄 Get File by ID"), KeyboardButton(text="🚫 Suspend/Remove Member")]
    ], resize_keyboard=True)
    
    status_kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Current Student")], 
        [KeyboardButton(text="Graduated within 3 years")]
    ], resize_keyboard=True, one_time_keyboard=True)

    education_level_kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Bachelor's Degree")], 
        [KeyboardButton(text="Master's Degree")]
    ], resize_keyboard=True, one_time_keyboard=True)

    region_buttons = [[KeyboardButton(text=name)] for name in sorted(REGION_MAP.keys())]
    region_kb = ReplyKeyboardMarkup(keyboard=region_buttons, resize_keyboard=True, one_time_keyboard=True)


    # --- /start ---
    @dp.message(CommandStart())
    async def start_handler(message: Message):
        user_id = message.from_user.id
        # Clear all user modes
        if user_id in verification_mode: del verification_mode[user_id]
        if user_id in admin_reject_mode: del admin_reject_mode[user_id]
        if user_id in admin_suspension_mode: del admin_suspension_mode[user_id] 
        if user_id in admin_contact_mode: del admin_contact_mode[user_id] 
            
        if user_id == ADMIN_ID:
            await message.answer("Welcome Admin 👋\nChoose an option:", reply_markup=admin_menu)
        else:
            introduction_text = (
                "👋 **Welcome to the Ethiopian Psychology Students' Association (EPSA) Membership Bot!**\n\n"
                "This bot is your gateway to becoming an official EPSA member and receiving your **Digital Membership ID Card**.\n\n"
                "Choose an option to begin:"
            )
            await message.answer(introduction_text, reply_markup=main_menu, parse_mode="Markdown")

    # --------------------------
    # ID Management Flow 
    # --------------------------
    @dp.message(F.text == "⚙️ Manage ID/Delete")
    async def start_id_management(message: Message):
        user_id = message.from_user.id
        if user_id not in user_data or user_data[user_id].get("approved") is not True or user_data[user_id].get("suspended") is True:
             await message.answer("⚠️ You must have an **active and approved** Digital ID to manage this feature.", reply_markup=main_menu)
             return

        await message.answer(
            "⚙️ <b>Manage Digital ID</b>\n\n"
            "What would you like to do with your active Digital ID?\n\n"
            "<b>Note:</b> Deleting your ID will remove your registration files and require re-registration if you wish to obtain a new ID.",
            reply_markup=get_manage_id_keyboard(),
            parse_mode="HTML"
        )
        
    @dp.callback_query(lambda c: c.data == 'delete_id_confirm')
    async def confirm_id_deletion(callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        
        confirmation_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ YES, Delete All My Data", callback_data="delete_id_final"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="done_action")
            ]
        ])

        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="⚠️ <b>Are you sure you want to delete your Digital ID and all associated registration data? This action is permanent.</b>",
            reply_markup=confirmation_keyboard,
            parse_mode="HTML"
        )
        await callback_query.answer()

    @dp.callback_query(lambda c: c.data == 'delete_id_final')
    async def final_id_deletion(callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        
        if user_id in user_data:
            # Delete user data entirely
            del user_data[user_id]
            
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text="✅ <b>Digital ID and all registration data have been permanently erased.</b>",
                reply_markup=None,
                parse_mode="HTML"
            )
            await callback_query.answer("Data deleted.")
            await bot.send_message(user_id, "You are no longer a registered member. Use the Register button to start over.", reply_markup=main_menu)

            # Save data
            save_data()
        else:
            await callback_query.answer("No data found to delete.", show_alert=True)


    # --------------------------
    # Admin Contact Flow
    # --------------------------
    @dp.message(F.text == "📞 Contact Admin")
    async def start_admin_contact(message: Message):
        user_id = message.from_user.id
        if user_id in verification_mode: del verification_mode[user_id]
        admin_contact_mode[user_id] = True
        
        await message.answer(
            "✍️ <b>Contact Admin</b>\n\n"
            "Please type your full message (support request, compliant, or question). We will forward it to the administrator.\n\n"
            "<b>Note:</b> Use /start to cancel.", 
            reply_markup=ReplyKeyboardMarkup(keyboard=[[]], resize_keyboard=True), 
            parse_mode="HTML"
        )

    @dp.message(lambda m: m.from_user.id in admin_contact_mode and m.text is not None)
    async def process_admin_contact(message: Message):
        user_id = message.from_user.id
        contact_message = message.text
        
        del admin_contact_mode[user_id] # Exit contact mode

        user_mention = f"User ID: <code>{user_id}</code>"
        if message.from_user.username:
            user_mention += f" (@{message.from_user.username})"
        if message.from_user.full_name:
            user_mention = f"Name: {message.from_user.full_name} ({user_mention})"
            
        membership_info = ""
        if user_id in user_data:
            data = user_data[user_id]
            status = "✅ Active" if data.get('approved') and not data.get('suspended') else "⚠️ Pending/Inactive"
            
            # Recalculate structured ID for display
            region_code = data.get('region_code', 'XX')
            if data.get('membership_status') == "Current Student":
                year_code = str(data.get('year', '00')).zfill(2)
            else:
                grad_year_str = str(data.get('graduation_year', '00'))
                year_code = grad_year_str[-2:].zfill(2)
            random_part = data.get('random_id_suffix', '0000') 
            member_id_display = f"EPSA-{region_code}-{year_code}-{random_part}"

            membership_info = (
                f"<b>Status:</b> {status}\n"
                f"<b>Membership ID:</b> <code>{member_id_display}</code>\n"
            )

        admin_notification = (
            f"📞 <b>NEW SUPPORT/COMPLAINT MESSAGE</b>\n\n"
            f"{user_mention}\n"
            f"{membership_info}"
            f"--- MESSAGE ---\n"
            f"{(contact_message[:1000] + '...') if len(contact_message) > 1000 else contact_message}\n"
            f"---------------\n\n"
            f"Reply to this message to contact the user directly."
        )

        try:
            await bot.send_message(ADMIN_ID, admin_notification, parse_mode="HTML")
            menu_to_send = admin_menu if user_id == ADMIN_ID else main_menu
            await message.answer(
                "✅ Your message has been successfully forwarded to the administrator. We will respond as soon as possible.", 
                reply_markup=menu_to_send
            )

        except Exception as e:
            await message.answer("❌ There was an error sending your message. Please try again later.", reply_markup=main_menu)
            
    # --------------------------
    # Admin Portal Handlers
    # --------------------------

    # --- Admin File Retrieval (Requesting ID) ---
    @dp.message(F.text == "📄 Get File by ID")
    async def ask_file_id(message: Message):
        if message.from_user.id != ADMIN_ID: return
        if message.from_user.id in admin_reject_mode: del admin_reject_mode[message.from_user.id]
        if message.from_user.id in admin_suspension_mode: del admin_suspension_mode[message.from_user.id]
        if message.from_user.id in admin_contact_mode: del admin_contact_mode[message.from_user.id]
            
        await message.answer("Please reply with the **Numerical User ID** (Telegram ID) to retrieve files:")

    # --- Admin File Retrieval (Processing ID) ---
    @dp.message(lambda m: m.from_user.id == ADMIN_ID and m.text.isdigit() and m.from_user.id not in admin_reject_mode and m.from_user.id not in admin_suspension_mode and m.from_user.id not in admin_contact_mode)
    async def verify_file(message: Message):
        admin_id = message.from_user.id
        
        # Check to exit registration flow if admin is trying to fetch files
        if admin_id in user_data and "photo_file_id" not in user_data[admin_id]:
                return 
        
        try:
            uid = int(message.text)
            data = user_data.get(uid)
            
            if not data:
                await message.answer(f"❌ User ID {uid} not found in database.")
                return

            photo_file_id = data.get("photo_file_id")
            uni_id_file_id = data.get("uni_id_file") 
            proof_file_id = data.get("proof")
            
            status = "✅ APPROVED" if data.get('approved') is True else "⚠️ PENDING APPROVAL"
            is_suspended = data.get('suspended') is True
            if is_suspended:
                 status = "🛑 **SUSPENDED**"
                 
            year_info = data.get('year', data.get('graduation_year', 'N/A'))
            
            summary = (
                f"🔎 <b>FILE RETRIEVAL SUMMARY</b> for User ID: {uid}\n\n"
                f"<b>Name:</b> {data.get('full_name', 'N/A')}\n"
                f"<b>Membership:</b> {data.get('membership_status', 'N/A')}\n"
                f"<b>Status:</b> {status}\n"
                f"<b>Level:</b> {data.get('education_level', 'N/A')} ({year_info})\n\n"
                f"Files are attached below."
            )
            await message.answer(summary, parse_mode="HTML") 

            # 1. Send Digital ID Card 
            if data.get('approved') is True or is_suspended:
                try:
                    # Pass suspension status to generator
                    base_bio = generate_id(uid, data, bot, is_suspended=is_suspended) 
                    
                    # Only attempt to get photo if the photo file ID is present
                    photo_bio = None
                    if user_data[uid].get('photo_file_id'):
                        photo_bio = await get_user_photo_bytes(bot, user_data[uid]['photo_file_id'])

                    final_bio = base_bio
                    if photo_bio:
                        final_bio = await draw_photo_on_id(base_bio, photo_bio)
                        
                    photo_file = BufferedInputFile(final_bio.read(), filename="User_ID.png")
                    
                    await bot.send_photo(
                        chat_id=admin_id, 
                        photo=photo_file,
                        caption=f"🆔 <b>Digital ID Card</b> for {data.get('full_name', 'User')}",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    await message.answer(f"⚠️ Error generating/sending Digital ID: {e}")

            # 2. Send Photo File 
            if photo_file_id:
                await bot.send_photo(chat_id=admin_id, photo=photo_file_id, caption="📸 <b>User Selfie Photo</b>", parse_mode="HTML")
            else:
                await message.answer("❌ Photo file ID missing.")

            # 3. Send University ID
            if uni_id_file_id:
                await bot.send_photo(chat_id=admin_id, photo=uni_id_file_id, caption="🎓 <b>University ID Card</b>", parse_mode="HTML")
            else:
                await message.answer("⚠️ University ID file missing.")

            # 4. Send Proof/Slip File
            if proof_file_id:
                try:
                    await bot.send_document(chat_id=admin_id, document=proof_file_id, caption="📄 <b>Registration Slip</b>", parse_mode="HTML")
                except:
                    try:
                        await bot.send_photo(chat_id=admin_id, photo=proof_file_id, caption="📄 <b>Registration Slip</b>", parse_mode="HTML")
                    except:
                        await message.answer(f"⚠️ Error sending proof file.")
            else:
                await message.answer("❌ Proof/Slip file ID missing.")

        except Exception as e:
            await message.answer(f"An unexpected error occurred: {e}")

    # --- View Pending Registrations ---
    @dp.message(F.text == "📋 View Pending Registrations")
    async def view_pending(message: Message):
        if message.from_user.id != ADMIN_ID: return
        pending = []
        for uid, data in user_data.items():
            # Ensure all steps completed and not yet approved/rejected
            if all(k in data for k in ["proof", "photo_file_id", "uni_id_file"]) and "approved" not in data:
                year_info = data.get('year', data.get('graduation_year', 'N/A'))
                entry = (
                    f"ID: {uid} (Numerical)\n"
                    f"Name: {data.get('full_name')}\n"
                    f"Type: {data.get('membership_status', 'N/A')}\n"
                    f"University: {data.get('university')}\n"
                    f"Year: {year_info}"
                )
                pending.append((uid, entry))
        if pending:
            await message.answer(f"📋 <b>Pending Registrations ({len(pending)})</b>\n\nClick 'Review and approve/reject' to view documents and decide.", parse_mode="HTML")
            for uid, entry in pending:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Review and approve/reject", callback_data=f"review_{uid}")]
                ])
                await message.answer(entry, reply_markup=keyboard)
        else:
            await message.answer("✅ No pending registrations.")

    # --- View All Approved Members ---
    @dp.message(F.text == "👥 View All Members")
    async def view_all_members(message: Message):
        if message.from_user.id != ADMIN_ID: return
        
        approved_members = []
        for uid, data in user_data.items():
            if data.get("approved") is True and data.get("suspended") is not True:
                region_code = data.get('region_code', 'XX')
                if data.get('membership_status') == "Current Student":
                    year_code = str(data.get('year', '00')).zfill(2)
                else:
                    grad_year_str = str(data.get('graduation_year', '00'))
                    year_code = grad_year_str[-2:].zfill(2)
                random_part = data.get('random_id_suffix', '0000') 
                member_id_display = f"EPSA-{region_code}-{year_code}-{random_part}"
                
                approved_members.append(
                    f"• <b>ID:</b> {member_id_display}\n"
                    f"  <b>Name:</b> {data.get('full_name')}\n"
                    f"  <b>Num. ID:</b> <code>{uid}</code>"
                )
        
        if approved_members:
            list_header = "👥 <b>ALL ACTIVE MEMBERS ({})</b>\n\n".format(len(approved_members))
            current_text = list_header
            for line in approved_members:
                if len(current_text) + len(line) + 20 > 4096: 
                    await message.answer(current_text, parse_mode="HTML")
                    current_text = list_header
                current_text += line + "\n\n"
            if len(current_text.strip()) > len(list_header.strip()):
                await message.answer(current_text, parse_mode="HTML")
        else:
            await message.answer("❌ No active approved members found.")
            
    # --- Start Suspension/Remove Process ---
    @dp.message(F.text == "🚫 Suspend/Remove Member")
    async def start_suspension(message: Message):
        if message.from_user.id != ADMIN_ID: return
        if message.from_user.id in admin_reject_mode: del admin_reject_mode[message.from_user.id]
        if message.from_user.id in admin_contact_mode: del admin_contact_mode[message.from_user.id]
        admin_suspension_mode[message.from_user.id] = True
        
        await message.answer(
            "🛑 <b>MEMBER SUSPENSION MODE</b>\n\n"
            "Please reply with the **Numerical User ID** (Telegram ID).",
            parse_mode="HTML"
        )
        
    @dp.message(lambda m: m.from_user.id == ADMIN_ID and m.text.isdigit() and m.from_user.id in admin_suspension_mode)
    async def process_suspension(message: Message):
        admin_id = message.from_user.id
        target_uid = int(message.text)
        del admin_suspension_mode[admin_id] 
        
        data = user_data.get(target_uid)
        
        if not data:
            await message.answer(f"❌ User ID {target_uid} not found.")
            return

        is_suspended = data.get('suspended', False)
        status_text = "SUSPENDED" if is_suspended else "ACTIVE"
        
        await message.answer(
            f"👤 <b>MEMBER MANAGEMENT</b>\nName: {data.get('full_name')}\nCurrent Status: <b>{status_text}</b>", 
            reply_markup=get_suspension_keyboard(target_uid, is_suspended),
            parse_mode="HTML"
        )

    # --------------------------
    # INLINE CALLBACK HANDLERS
    # --------------------------
    
    # --- Approve ---
    @dp.callback_query(lambda c: c.data and c.data.startswith('approve_'))
    async def approve_user_callback(callback_query: CallbackQuery):
        user_id = int(callback_query.data.split('_')[1])
        admin_id = callback_query.from_user.id
        if admin_id != ADMIN_ID: 
            await callback_query.answer("Permission denied.")
            return

        if user_id in user_data:
            user_data[user_id]["approved"] = True
            if "suspended" in user_data[user_id]: del user_data[user_id]["suspended"] 
            
            try:
                await bot.edit_message_reply_markup(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=get_done_keyboard("✅ Approved", user_id)
                )
            except Exception as e:
                print(f"Error editing message markup for approval: {e}")
                await callback_query.answer("Approved, but could not update button.")


            # Generate and Send ID
            expiry_date = (datetime.now() + timedelta(days=365)).strftime("%d-%b-%Y")
            try:
                base_bio = generate_id(user_id, user_data[user_id], bot, is_suspended=False)
                photo_bio = await get_user_photo_bytes(bot, user_data[user_id]['photo_file_id'])

                final_bio = base_bio
                if photo_bio: final_bio = await draw_photo_on_id(base_bio, photo_bio)
                    
                photo_file = BufferedInputFile(final_bio.read(), filename="EPSA_ID.png")
                    
                await bot.send_message(user_id, "🎉 Your registration has been approved! Your Digital ID is attached.")
                await bot.send_photo(chat_id=user_id, photo=photo_file, caption=f"Valid until {expiry_date}.")
            except Exception as e:
                await bot.send_message(user_id, f"🎉 Your registration has been approved! However, there was an error generating your ID card: {e}")
                await bot.send_message(admin_id, f"⚠️ Error sending Digital ID to user {user_id}: {e}")
                
            await callback_query.answer(f"User {user_id} Approved.")

            # Save data
            save_data()

        else:
            await callback_query.answer("User not found.")

    # --- Review ---
    @dp.callback_query(lambda c: c.data and c.data.startswith('review_'))
    async def review_callback(callback_query: CallbackQuery):
        user_id = int(callback_query.data.split('_')[1])
        admin_id = callback_query.from_user.id
        if admin_id != ADMIN_ID: 
            await callback_query.answer("Permission denied.")
            return

        if user_id not in user_data:
            await callback_query.answer("User not found.")
            return

        data = user_data[user_id]
        status = "⚠️ PENDING APPROVAL"
        year_info = data.get('year', data.get('graduation_year', 'N/A'))
        
        summary = (
            f"🔎 <b>REVIEWING APPLICATION</b> for User ID: {user_id}\n\n"
            f"<b>Name:</b> {data.get('full_name', 'N/A')}\n"
            f"<b>Membership:</b> {data.get('membership_status', 'N/A')}\n"
            f"<b>Status:</b> {status}\n"
            f"<b>Level:</b> {data.get('education_level', 'N/A')} ({year_info})\n\n"
            f"Files are attached below."
        )
        await bot.send_message(ADMIN_ID, summary, parse_mode="HTML")

        # Send files
        photo_file_id = data.get("photo_file_id")
        uni_id_file_id = data.get("uni_id_file") 
        proof_file_id = data.get("proof")
        
        if photo_file_id:
            await bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id, caption="📸 <b>User Selfie Photo</b>", parse_mode="HTML")
        
        if uni_id_file_id:
            await bot.send_photo(chat_id=ADMIN_ID, photo=uni_id_file_id, caption="🎓 <b>University ID Card</b>", parse_mode="HTML")
        
        if proof_file_id:
            try:
                await bot.send_document(chat_id=ADMIN_ID, document=proof_file_id, caption="📄 <b>Registration Slip</b>", parse_mode="HTML")
            except:
                try:
                    await bot.send_photo(chat_id=ADMIN_ID, photo=proof_file_id, caption="📄 <b>Registration Slip</b>", parse_mode="HTML")
                except:
                    await bot.send_message(ADMIN_ID, "⚠️ Error sending proof file.")
        
        # Send approve/reject buttons
        keyboard = get_admin_action_keyboard(user_id)
        await bot.send_message(ADMIN_ID, "Review the files above and decide:", reply_markup=keyboard)
        
        await callback_query.answer("Review initiated.")

    # --- Suspend ---
    @dp.callback_query(lambda c: c.data and c.data.startswith('suspend_'))
    async def suspend_user_callback(callback_query: CallbackQuery):
        user_id = int(callback_query.data.split('_')[1])
        if callback_query.from_user.id != ADMIN_ID: 
            await callback_query.answer("Permission denied.")
            return
        
        if user_id in user_data:
            user_data[user_id]["approved"] = False
            user_data[user_id]["suspended"] = True
            await bot.edit_message_reply_markup(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=get_done_keyboard("🛑 Suspended", user_id)
            )
            
            # Generate and Send Suspended ID
            expiry_date = (datetime.now() + timedelta(days=365)).strftime("%d-%b-%Y")
            try:
                base_bio = generate_id(user_id, user_data[user_id], bot, is_suspended=True)
                photo_bio = await get_user_photo_bytes(bot, user_data[user_id]['photo_file_id'])
                final_bio = base_bio
                if photo_bio: final_bio = await draw_photo_on_id(base_bio, photo_bio)
                photo_file = BufferedInputFile(final_bio.read(), filename="EPSA_ID.png")
                
                await bot.send_message(user_id, "🛑 **Membership suspended!** Your suspended Digital ID is attached.")
                await bot.send_photo(chat_id=user_id, photo=photo_file, caption=f"Valid until {expiry_date}.")
            except Exception as e:
                await bot.send_message(user_id, f"🛑 Membership suspended! Error sending ID card: {e}")

            await callback_query.answer(f"User {user_id} Suspended.")

            # Save data
            save_data()

    # --- Reactivate ---
    @dp.callback_query(lambda c: c.data and c.data.startswith('reactivate_'))
    async def final_reactivate_callback(callback_query: CallbackQuery):
        user_id = int(callback_query.data.split('_')[1])
        if callback_query.from_user.id != ADMIN_ID: 
            await callback_query.answer("Permission denied.")
            return
        
        if user_id in user_data:
            user_data[user_id]["approved"] = True
            if "suspended" in user_data[user_id]: del user_data[user_id]["suspended"] 
            
            await bot.edit_message_reply_markup(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=get_done_keyboard("🟢 Reactivated", user_id)
            )
            
            # Resend NEW ACTIVE ID
            expiry_date = (datetime.now() + timedelta(days=365)).strftime("%d-%b-%Y")
            try:
                base_bio = generate_id(user_id, user_data[user_id], bot, is_suspended=False)
                photo_bio = await get_user_photo_bytes(bot, user_data[user_id]['photo_file_id'])
                final_bio = base_bio
                if photo_bio: final_bio = await draw_photo_on_id(base_bio, photo_bio)
                photo_file = BufferedInputFile(final_bio.read(), filename="EPSA_ID.png")
                
                await bot.send_message(user_id, "🟢 **Membership reactivated!** Your new active Digital ID is attached. Please manually delete any old 'SUSPENDED' IDs you may have.")
                await bot.send_photo(chat_id=user_id, photo=photo_file, caption=f"Valid until {expiry_date}.")
            except Exception as e:
                await bot.send_message(user_id, f"🟢 Membership reactivated! Error sending ID card: {e}")

            await callback_query.answer(f"User {user_id} Reactivated.")

    # --- Reject ---
    @dp.callback_query(lambda c: c.data and c.data.startswith('reject_'))
    async def reject_user_callback(callback_query: CallbackQuery):
        user_id = int(callback_query.data.split('_')[1])
        if callback_query.from_user.id != ADMIN_ID: 
            await callback_query.answer("Permission denied.")
            return
        admin_reject_mode[callback_query.from_user.id] = {'uid': user_id, 'message_id': callback_query.message.message_id}
        await bot.send_message(ADMIN_ID, f"🚫 Please reply with the rejection reason for User {user_id}.")
        await callback_query.answer("Reply with rejection reason.")

    @dp.message(lambda m: m.from_user.id == ADMIN_ID and m.from_user.id in admin_reject_mode and m.text is not None)
    async def process_rejection_reason(message: Message):
        admin_id = message.from_user.id
        rejection_data = admin_reject_mode.pop(admin_id)
        uid = rejection_data['uid']
        reason = message.text

        if uid in user_data:
            user_data[uid]["approved"] = False
            user_data[uid]["suspended"] = False # Ensure not suspended
            await message.answer(f"✅ Rejection recorded.")
            
            await bot.edit_message_reply_markup(
                chat_id=admin_id,
                message_id=rejection_data['message_id'],
                reply_markup=get_done_keyboard("❌ Rejected", uid, reason)
            )

            await bot.send_message(uid, f"❌ <b>Registration Rejected</b>\nReason: {reason}\nPlease re-register.", parse_mode="HTML")

            # Save data
            save_data()

    # --------------------------
    # ID Verification Flow 
    # --------------------------
    @dp.message(F.text == "🔍 Verify ID")
    async def start_verification(message: Message):
        user_id = message.from_user.id
        if user_id == ADMIN_ID:
            if user_id in admin_reject_mode: del admin_reject_mode[user_id]
            if user_id in admin_suspension_mode: del admin_suspension_mode[user_id]
            if user_id in admin_contact_mode: del admin_contact_mode[user_id]
            
        verification_mode[user_id] = True
        menu_to_send = admin_menu if user_id == ADMIN_ID else main_menu
        
        await message.answer(
            "🔑 <b>ID Verification Mode</b>\n\n"
            "Please enter either the **Numerical User ID** or the **Structured Membership ID** (e.g., `EPSA-AA-04-1234`).",
            reply_markup=menu_to_send,
            parse_mode="HTML"
        )
    
    @dp.message(lambda m: m.from_user.id in verification_mode and verification_mode[m.from_user.id] is True)
    async def process_verification(message: Message):
        verifier_id = message.from_user.id
        input_id = message.text.strip().upper()
        del verification_mode[verifier_id]
        
        target_uid = None
        user_info = None
        menu_to_send = admin_menu if verifier_id == ADMIN_ID else main_menu

        is_structured_id = STRUCTURED_ID_PATTERN.match(input_id)
        
        if is_structured_id:
            for uid, data in user_data.items():
                if data.get('region_code') and data.get('random_id_suffix'):
                    # Recalculate year code for search match
                    if data.get('membership_status') == "Current Student":
                        year_code = str(data.get('year', '00')).zfill(2)
                    elif data.get('membership_status') == "Graduated within 3 years":
                        grad_year_str = str(data.get('graduation_year', '00'))
                        year_code = grad_year_str[-2:].zfill(2)
                    else:
                        continue 
                        
                    expected_id = f"EPSA-{data['region_code']}-{year_code}-{data['random_id_suffix']}".upper()
                    if expected_id == input_id:
                        target_uid = uid
                        user_info = data
                        break
        
        elif input_id.isdigit():
            target_uid = int(input_id)
            user_info = user_data.get(target_uid)

        if not user_info:
            await message.answer("🚫 <b>Verification Failed.</b> Unknown ID.", reply_markup=menu_to_send, parse_mode="HTML")
            return
        
        # Check Status
        if user_info.get("suspended") is True:
            await message.answer(f"🛑 <b>ID SUSPENDED.</b>\nUser: {user_info.get('full_name')}", reply_markup=menu_to_send, parse_mode="HTML")
            
        elif user_info.get("approved") is True:
            await message.answer(f"✅ <b>ID VERIFIED & ACTIVE</b>\nName: {user_info.get('full_name')}\nSending ID Card...", parse_mode="HTML")
            
            if user_info.get("photo_file_id"):
                try:
                    # Send ACTIVE ID (not suspended)
                    base_bio = generate_id(target_uid, user_info, bot, is_suspended=False)
                    photo_bio = await get_user_photo_bytes(bot, user_info['photo_file_id'])
                    final_bio = base_bio
                    if photo_bio: final_bio = await draw_photo_on_id(base_bio, photo_bio)
                    photo_file = BufferedInputFile(final_bio.read(), filename=f"ID.png")
                    await bot.send_photo(chat_id=verifier_id, photo=photo_file)
                except Exception as e:
                    await message.answer(f"⚠️ Error generating ID: {e}")
            await message.answer("Verification complete.", reply_markup=menu_to_send)

        else:
            await message.answer("⚠️ <b>ID Invalid.</b> Pending or Rejected.", reply_markup=menu_to_send, parse_mode="HTML")


    # --------------------------
    # Registration Flow (General Catch-all)
    # --------------------------
    @dp.message(lambda m: True)
    async def registration_flow(message: Message):
        user_id = message.from_user.id
        
        # Admin is busy with other tasks
        if user_id == ADMIN_ID and (user_id in admin_reject_mode or user_id in admin_suspension_mode or user_id in admin_contact_mode):
            return

        # Regular user is busy contacting admin
        if user_id != ADMIN_ID and user_id in admin_contact_mode:
             if message.text:
                 await process_admin_contact(message)
             else:
                 await message.answer("Please send your support message as text, or use /start to cancel.")
             return
        
        # Clear verification mode if user sends any message
        if user_id in verification_mode:
            del verification_mode[user_id]

        if message.text == "📝 Register":
            if user_id in user_data and user_data[user_id].get("approved") is True and user_data[user_id].get("suspended") is not True:
                # If they are already approved
                await message.answer(
                    "You are already registered and approved. Use **🔍 Verify ID** to retrieve your ID or **⚙️ Manage ID/Delete** if you wish to erase your data.", 
                    reply_markup=main_menu,
                    parse_mode="Markdown"
                )
                return
            
            # Initialize data and generate the random suffix immediately
            user_data[user_id] = {}
            user_data[user_id]["random_id_suffix"] = str(random.randint(1000, 9999)) 
            
            # 1. Ask for Membership Status (Detailed)
            await message.answer(
                "➡️ **Step 1 of 9: Membership Status**\n\n"
                "Please select your current affiliation with your university. This determines the structure of your EPSA ID.", 
                reply_markup=status_kb,
                parse_mode="Markdown"
            ) 
            return

        if user_id not in user_data: return
        
        # REGISTRATION STATES

        # 1. Membership Status 
        if "membership_status" not in user_data[user_id]:
            status_text = message.text
            if status_text not in ["Current Student", "Graduated within 3 years"]:
                await message.answer("⚠️ Please select a valid membership status using the buttons.")
                return
            
            user_data[user_id]["membership_status"] = status_text
            save_data()  # Save after each step
            await message.answer(
                "➡️ **Step 2 of 9: Full Name**\n\n"
                "Please enter your **full legal name** (First Name, Father's Name, Grandfather's Name) as it appears on official documents. This will be printed on your Digital ID.", 
                reply_markup=ReplyKeyboardMarkup(keyboard=[[]], resize_keyboard=True),
                parse_mode="Markdown"
            ) 
            return


        # 2. Full Name
        if "full_name" not in user_data[user_id]:
            user_data[user_id]["full_name"] = message.text
            save_data()  # Save after each step
            await message.answer(
                "➡️ **Step 3 of 9: University Name**\n\n"
                "Please enter the **full name of your University** (e.g., Addis Ababa University, Haramaya University).",
                parse_mode="Markdown"
            ) 
            return
            
        # 3. University
        if "university" not in user_data[user_id]:
            user_data[user_id]["university"] = message.text
            save_data()  # Save after each step
            await message.answer(
                "➡️ **Step 4 of 9: University Region**\n\n"
                "Please select the **Region** where your University is located. This forms part of your unique membership ID structure.", 
                reply_markup=region_kb,
                parse_mode="Markdown"
            ) 
            return
            
        # 4. Region Selection 
        if "region" not in user_data[user_id]:
            selected_region = message.text
            if selected_region not in REGION_MAP:
                await message.answer("⚠️ Please select a valid region using the provided buttons.")
                return
                
            user_data[user_id]["region"] = selected_region
            user_data[user_id]["region_code"] = REGION_MAP[selected_region]
            save_data()  # Save after each step
            
            await message.answer(
                "➡️ **Step 5 of 9: Academic Level**\n\n"
                "Please specify your **highest** or **current** academic program.", 
                reply_markup=education_level_kb,
                parse_mode="Markdown"
            ) 
            return
        
        # 5. Education Level (Handles saving level and moving to Year/Grad year)
        if "education_level" not in user_data[user_id]:
            level_text = message.text
            if level_text not in ["Bachelor's Degree", "Master's Degree"]:
                await message.answer("⚠️ Please use the keyboard buttons for Academic Level.")
                return
                
            user_data[user_id]["education_level"] = level_text
            save_data()  # Save after each step
            
            if user_data[user_id]["membership_status"] == "Current Student":
                await message.answer(
                    "➡️ **Step 6 of 9: Current Academic Year**\n\n"
                    "Please enter your **current academic year** (e.g., enter `1`, `2`, `3`, `4`, or `5`).",
                    reply_markup=ReplyKeyboardMarkup(keyboard=[[]], resize_keyboard=True),
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    "➡️ **Step 6 of 9: Graduation Year**\n\n"
                    "Please enter the **year you graduated** (e.g., `2023`).",
                    reply_markup=ReplyKeyboardMarkup(keyboard=[[]], resize_keyboard=True),
                    parse_mode="Markdown"
                )
            return

        # 6. Year Info (Current Student)
        if user_data[user_id]["membership_status"] == "Current Student" and "year" not in user_data[user_id] and message.text:
            user_data[user_id]["year"] = message.text
            save_data()  # Save after each step
            await message.answer(
                "➡️ **Step 7 of 9: Selfie Photo**\n\n"
                "Please upload a **clear, recent, passport-style selfie photo**. This image will be printed directly on your Digital ID card. Make sure it has a plain background.",
                parse_mode="Markdown"
            )
            return

        # 6. Year Info (Graduate)
        if user_data[user_id]["membership_status"] == "Graduated within 3 years" and "graduation_year" not in user_data[user_id] and message.text:
            user_data[user_id]["graduation_year"] = message.text
            save_data()  # Save after each step
            await message.answer(
                "➡️ **Step 7 of 9: Selfie Photo**\n\n"
                "Please upload a **clear, recent, passport-style selfie photo**. This image will be printed directly on your Digital ID card. Make sure it has a plain background.",
                parse_mode="Markdown"
            )
            return


        # 7. Selfie Upload 
        if "photo_file_id" not in user_data[user_id]:
            if message.photo:
                user_data[user_id]["photo_file_id"] = message.photo[-1].file_id
                save_data()  # Save after each step
                # 8. University ID Upload (Detailed)
                await message.answer(
                    "➡️ **Step 8 of 9: University ID Card**\n\n"
                    "Please upload a clear photo of your **valid University ID Card (Student or Staff)**. This is crucial for verifying your current affiliation.",
                    parse_mode="Markdown"
                )
            else:
                await message.answer("❌ Please send a valid photo for your selfie.")
            return

        # 8. University ID Upload (Detailed)
        if "uni_id_file" not in user_data[user_id]:
            if message.photo:
                user_data[user_id]["uni_id_file"] = message.photo[-1].file_id
                save_data()  # Save after each step
                # 9. Proof Upload (Detailed)
                await message.answer(
                    "➡️ **Step 9 of 9: Registration Slip**\n\n"
                    "Finally, upload a clear image or PDF of your **EPSA Registration Payment Slip**. This confirms your successful payment and completes your registration.",
                    parse_mode="Markdown"
                )
            else:
                await message.answer("❌ Please send a photo of your University ID.")
            return

        # 9. Proof Document Upload (Final Step)
        if "proof" not in user_data[user_id]:
            if message.photo or message.document:
                file_id = message.photo[-1].file_id if message.photo else message.document.file_id
                user_data[user_id]["proof"] = file_id
                
                menu_to_send = admin_menu if user_id == ADMIN_ID else main_menu
                await message.answer(
                    "🎉 **Registration Complete!**\n\n"
                    "Your application has been submitted for review. An administrator will verify your details and payment slip. You will receive a notification and your Digital ID Card upon approval. Thank you for registering!", 
                    reply_markup=menu_to_send,
                    parse_mode="Markdown"
                )
                
                # Notify admin of new registration
                await bot.send_message(ADMIN_ID, f"🔔 New registration submitted by {user_data[user_id]['full_name']} (ID: {user_id}). Check '📋 View Pending Registrations' to review.")
                
                # Save data
                save_data()
                
                # No automatic forwarding of files to admin chat anymore
                # Pending applications are now only visible/listed in "View Pending Registrations"
                # Admin must use "Get File by ID" to review them

            else:
                await message.answer("❌ Please send a valid image or PDF for your registration slip.")

    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 