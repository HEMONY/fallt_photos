import telebot
from telebot import types
from rembg import remove
from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageDraw, ImageFont
from io import BytesIO
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip, ImageClip
from googletrans import Translator
import json

# إعداد البوت والمفاتيح
API_TOKEN = '6665186630:AAEFJwe0PY9P1tfAdq9nBoJtx1YgQb4uiSs'
STABILITY_API_KEY = 'sk-4waRUzV6mGHgE8GXUYeH4EKXlGyLUjBUldrf7E0xpSsZPqPL'
CHANNEL_ID = '@fallt_tec'
OWNER_ID = 588461026  # ضع هنا معرف المستخدم الخاص بك
USERS_DATA_FILE = "users_data.json"

bot = telebot.TeleBot(API_TOKEN)
bot.set_webhook()
stability_api = client.StabilityInference(key=STABILITY_API_KEY, verbose=True)

# تحميل بيانات المستخدمين من ملف JSON
def load_users_data():
    try:
        with open(USERS_DATA_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# حفظ بيانات المستخدمين إلى ملف JSON
def save_users_data(data):
    with open(USERS_DATA_FILE, 'w') as file:
        json.dump(data, file)

# الحصول على عدد المستخدمين
def get_users_count():
    users_data = load_users_data()
    return len(users_data)

# دالة لترجمة النصوص
def translate_text(text, src_lang='ar', dest_lang='en'):
    translator = Translator()
    translated = translator.translate(text, src=src_lang, dest=dest_lang)
    return translated.text

# دالة لمعالجة الصور وإزالة الخلفية
def process_image(image_data):
    image = Image.open(BytesIO(image_data))
    output = remove(image)
    return output

# دالة لتوليد الصور باستخدام Stable Diffusion
def generate_image(prompt):
    translated_prompt = translate_text(prompt)
    answers = stability_api.generate(prompt=translated_prompt)
    for resp in answers:
        for artifact in resp.artifacts:
            if artifact.finish_reason == generation.FILTER:
                raise Exception("Request triggered the safety filters.")
            if artifact.type == generation.ARTIFACT_IMAGE:
                img = Image.open(BytesIO(artifact.binary))
                return img

# دالة لتطبيق الفلاتر على الصور
def apply_filters(image, options):
    if 'blur' in options:
        image = image.filter(ImageFilter.BLUR)
    if 'contour' in options:
        image = image.filter(ImageFilter.CONTOUR)
    if 'sharpen' in options:
        image = image.filter(ImageFilter.SHARPEN)
    if 'grayscale' in options:
        image = ImageOps.grayscale(image)
    if 'invert' in options:
        image = ImageOps.invert(image)
    if 'enhance_color' in options:
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(2.0)
    if 'enhance_contrast' in options:
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
    if 'enhance_brightness' in options:
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(2.0)
    if 'edge_enhance' in options:
        image = image.filter(ImageFilter.EDGE_ENHANCE)
    if 'emboss' in options:
        image = image.filter(ImageFilter.EMBOSS)
    return image

# دالة لتوليد الفيديو بناءً على الوصف
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip, ImageClip
import os

def generate_video(description, style='text', background_color='black'):
    try:
        translated_description = translate_text(description)
        clip_duration = 5  # طول الفيديو بالثواني
        fps = 24  # عدد الإطارات في الثانية

        # إعداد الخلفية بناءً على الاختيار
        background_clip = ColorClip(size=(720, 1280), color=background_color).set_duration(clip_duration)

        if style == 'text':
            # إعداد النص باستخدام Pillow
            img = Image.new('RGB', (720, 1280), color=background_color)
            draw = ImageDraw.Draw(img)
            try:
                # تحميل خط يدعم اللغة العربية
                font = ImageFont.truetype("arial.ttf", 70)  # استبدل "arial.ttf" بخط يدعم اللغة العربية
            except IOError:
                font = ImageFont.load_default()  # استخدام الخط الافتراضي إذا فشل تحميل الخط
            text_width, text_height = draw.textsize(translated_description, font=font)
            text_position = ((img.width - text_width) // 2, (img.height - text_height) // 2)
            draw.text(text_position, translated_description, font=font, fill=(255, 255, 255))

            # حفظ الصورة النصية
            text_image_path = "text_image.png"
            img.save(text_image_path)

            # تحميل الصورة النصية كـ ImageClip
            text_clip = ImageClip(text_image_path).set_duration(clip_duration).set_position('center')
            video = CompositeVideoClip([background_clip, text_clip])
        elif style == 'animated':
            # إضافة تأثيرات متحركة إذا لزم الأمر
            text_clip = TextClip(translated_description, fontsize=70, color='white', size=(720, 1280))
            text_clip = text_clip.set_duration(clip_duration).set_position('center')
            video = CompositeVideoClip([background_clip, text_clip])

        # تحديد مسار حفظ الفيديو
        video_path = "output.mp4"
        video.write_videofile(video_path, codec="libx264", fps=fps)

        # حذف الصورة المؤقتة بعد توليد الفيديو
        if os.path.exists(text_image_path):
            os.remove(text_image_path)

        return video_path
    except Exception as e:
        raise Exception(f"Error generating video: {str(e)}")
# استقبال الصور من المستخدم ومعالجة الخلفية مع المزيد من الخيارات
@bot.message_handler(content_types=['photo'])
def handle_image(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "🔔 **يرجى الاشتراك في القناة لتتمكن من استخدام البوت.**")
        return

    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # تقديم خيارات الفلاتر عبر الأزرار
    markup = types.InlineKeyboardMarkup(row_width=2)
    filters = [
        ('Blur', 'blur'),
        ('Contour', 'contour'),
        ('Sharpen', 'sharpen'),
        ('Grayscale', 'grayscale'),
        ('Invert', 'invert'),
        ('Enhance Color', 'enhance_color'),
        ('Enhance Contrast', 'enhance_contrast'),
        ('Enhance Brightness', 'enhance_brightness'),
        ('Edge Enhance', 'edge_enhance'),
        ('Emboss', 'emboss'),
        ('Remove Background', 'remove_bg')  # إضافة خيار إزالة الخلفية
    ]
    for filter_name, filter_key in filters:
        markup.add(types.InlineKeyboardButton(filter_name, callback_data=filter_key))
    
    bot.reply_to(message, "🔧 **اختر خيارًا من الخيارات أدناه لتطبيقه على الصورة:**", reply_markup=markup)

# التعامل مع اختيار الفلاتر
@bot.callback_query_handler(func=lambda call: True)
def handle_filter_selection(call):
    filter_option = call.data
    file_info = bot.get_file(call.message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    # تحديد ما إذا كان يجب إزالة الخلفية
    remove_bg = (filter_option == 'remove_bg')
    image = process_image(downloaded_file, remove_bg)
    
    if filter_option != 'remove_bg':
        # تطبيق الفلتر المحدد
        filtered_image = apply_filters(image, [filter_option])

        output_buffer = BytesIO()
        filtered_image.save(output_buffer, format='PNG')
        output_buffer.seek(0)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✅ **تم تطبيق الفلتر بنجاح!**",
            reply_markup=None
        )
        bot.send_photo(call.message.chat.id, output_buffer)
    else:
        output_buffer = BytesIO()
        image.save(output_buffer, format='PNG')
        output_buffer.seek(0)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="✅ **تم إزالة الخلفية بنجاح!**",
            reply_markup=None
        )
        bot.send_photo(call.message.chat.id, output_buffer)

# دالة للترحيب وإظهار الخيارات
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "🔔 **يرجى الاشتراك في القناة @fallt_tec لتتمكن من استخدام البوت/n اذا اردت تعديل صورة ارسل الصورة فقط وستظهر لك الاعدادات.**")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    item1 = types.KeyboardButton("عرض الفلاتر")
    item2 = types.KeyboardButton("توليد صورة")
    #item3 = types.KeyboardButton("توليد فيديو")
    item4 = types.KeyboardButton("عرض المساعدة")
    markup.add(item1, item2, item4)
    
    bot.reply_to(message, "👋 **مرحبًا! أنا بوت تعديل الصور.**", reply_markup=markup)

# التعامل مع زر "توليد صورة"
@bot.message_handler(func=lambda message: message.text == 'توليد صورة')
def prompt_generate_image(message):
    bot.reply_to(message, "✏️ **يرجى إرسال الوصف الذي تريد توليد صورة بناءً عليه.**")

# التعامل مع زر "توليد فيديو"
''''@bot.message_handler(func=lambda message: message.text == 'توليد فيديو')
def prompt_generate_video(message):
    bot.reply_to(message, "🎥 **يرجى إرسال الوصف الذي تريد توليد فيديو بناءً عليه.**")
'''
# رسالة المساعدة
@bot.message_handler(func=lambda message: message.text == 'عرض المساعدة')
def send_help(message):
    help_text = """
    📜 **دليل الاستخدام:**
    - **عرض الفلاتر**: عرض قائمة الفلاتر المتاحة.
    - **توليد صورة**: أرسل وصفًا للصورة التي تريد توليدها باستخدام الذكاء الاصطناعي.
    - **توليد فيديو**: أرسل وصفًا للفيديو الذي تريد توليده باستخدام الذكاء الاصطناعي.
    - **عرض المساعدة**: عرض معلومات المساعدة حول كيفية استخدام البوت.
    - **لوحة تحكم المالك**: (متاحة فقط للمالك) للوصول إلى إدارة البوت.
    
    **فلاتر متاحة:**
    - Blur
    - Contour
    - Sharpen
    - Grayscale
    - Invert
    - Enhance Color
    - Enhance Contrast
    - Enhance Brightness
    - Edge Enhance
    - Emboss

    هذا البوت تمت برمجته بواسطة المبرمج @hemonybot.
    """
    bot.reply_to(message, help_text)


# توليد الصورة أو الفيديو بناءً على النص
@bot.message_handler(func=lambda message: True)
def handle_generate(message):
    prompt = message.text.strip()

    if ";;فيديو" in prompt:
        try:
            video = generate_video(prompt.replace('توليد فيديو', '').strip())
            with open(video, "rb") as video_file:
                bot.send_video(message.chat.id, video_file)
        except Exception as e:
            bot.reply_to(message, f"⚠️ **حدث خطأ أثناء توليد الفيديو: {str(e)}**")
    else:
        try:
            generated_image = generate_image(prompt.replace('توليد صورة', '').strip())
            output_buffer = BytesIO()
            generated_image.save(output_buffer, format='PNG')
            output_buffer.seek(0)
            bot.send_photo(message.chat.id, output_buffer)
        except Exception as e:
            bot.reply_to(message, f"⚠️ **حدث خطأ أثناء توليد الصورة: **")

# دالة للتحقق من الاشتراك في القناة
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# بدء البوت
bot.polling()
