from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import telebot
import logging
import pygame
import pygame.camera
import RPi.GPIO as GPIO
import threading
import time
import os

TOKEN = '1717084972:AAH1l2ouvIscXUKX6dz77QW_ebTgn9W7fto'

ADMIN_USER_ID = (338179859,175048449)
LED_PIN = 3
PIR_PIN = 11
VIDEO_FILE_FORMAT = '.mkv'

# Enable Logging
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

isSensorEnabled = False
isMuteNotifications = False

last_chat_id = -1
keyboard = []

pygame.init()
pygame.camera.init()
pygame.camera.list_cameras() 

cam = pygame.camera.Camera("/dev/video0", (640,426))
bot = telebot.TeleBot(TOKEN)

def setup():
    GPIO.setmode(GPIO.BOARD) 
    GPIO.setwarnings(False)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.setup(PIR_PIN, GPIO.IN)

def destroy():
    GPIO.output(LED_PIN, GPIO.LOW)
    GPIO.cleanup() 

def log_params(method_name, message):
    logger.debug("Method: %s\nFrom: %s\nchat_id: %d\nText: %s" %
                (method_name,
                 message.from_user,
                 message.chat.id,
                 message.text))

@bot.message_handler(commands=['start'])
def start(message):
    global keyboard
    
    log_params('start', message)
    
    telegram_user = message.from_user
    
    if telegram_user.id  not in ADMIN_USER_ID:
        bot.send_message(message.chat.id, text="Salalamu alleikum brother")
        
        return
           
    keyboard = [
        [InlineKeyboardButton("Start sensor", callback_data='start_sensor')],
        [
            InlineKeyboardButton("Get capture", callback_data='get_capture'),
            InlineKeyboardButton("Get video", callback_data='get_video')
        ],
    ]

    bot.send_message(chat_id=message.chat.id,
                         text="Supported commands:",
                         reply_markup=InlineKeyboardMarkup(keyboard))

def sendCapture(chat_id):
    filename = datetime.now().strftime('%d-%m-%Y %H:%M:%S') + '.jpg'
    
    if (os.path.exists(filename)):
        bot.send_photo(chat_id, photo=open(filename, 'rb'))
    else:
        cam.start()
        pygame.image.save(cam.get_image(), filename)
        cam.stop()

        bot.send_photo(chat_id, photo=open(filename, 'rb'))

def get_capture(chat_id):
    sendCapture(chat_id)
    bot.send_message(chat_id=chat_id,
                     text="Supported commands:",
                     reply_markup=InlineKeyboardMarkup(keyboard))

def sendVideo(chat_id):
    filename = sorted(list(filter(lambda x: x.endswith(VIDEO_FILE_FORMAT), os.listdir())))[-1]

    bot.send_video(chat_id, open(filename, 'rb'))

def captureVideo():
    filename = datetime.now().strftime('%d-%m-%Y %H:%M:%S') + VIDEO_FILE_FORMAT
    
    os.system("ffmpeg -f v4l2 -framerate 25 -video_size 640x426 -i /dev/video0 -t 5 -c copy \"" + filename + "\"")
    
    return filename

def get_video(chat_id):
    bot.send_message(chat_id=chat_id,
                     text="Capturing video..")
        
    filename = captureVideo()

    bot.send_message(chat_id=chat_id,
                     text="Sending video..")
    bot.send_video(chat_id, open(filename, 'rb'))
    bot.send_message(chat_id=chat_id,
                     text="Supported commands:",
                     reply_markup=InlineKeyboardMarkup(keyboard))

def sensorJob():
    global isSensorEnabled
    global keyboard
    
    isRecording = False
    
    while isSensorEnabled:
        i = GPIO.input(PIR_PIN)
        
        GPIO.output(LED_PIN, i)
        
        if (i == 1 and not isRecording):
            isRecording = True
            
            if (not isMuteNotifications):
                sendCapture(last_chat_id)
        
        if (isRecording):
            captureVideo()
        
        if (i == 0 and isRecording):
            if (not isMuteNotifications):
                sendVideo(last_chat_id)
            
            isRecording = False
        
        time.sleep(0.1)
        
    if (isRecording):
        sendVideo(last_chat_id)
    
    keyboard = [
        [InlineKeyboardButton("Start sensor", callback_data='start_sensor')],
        [
            InlineKeyboardButton("Get capture", callback_data='get_capture'),
            InlineKeyboardButton("Get video", callback_data='get_video')
        ],
    ]

    bot.send_message(chat_id=last_chat_id,
                     text="Sensor stopped")
    bot.send_message(chat_id=last_chat_id,
                         text="Supported commands:",
                         reply_markup=InlineKeyboardMarkup(keyboard))

def start_sensor(chat_id):
    global keyboard
    global isSensorEnabled
    global last_chat_id
    
    last_chat_id = chat_id
    isSensorEnabled = True
    
    threading.Thread(target=sensorJob).start()
    
    keyboard = [
        [
            InlineKeyboardButton("Stop sensor", callback_data='stop_sensor'),
            InlineKeyboardButton("Mute notifications", callback_data='mute_notifications')
        ]
    ]

    bot.send_message(chat_id=chat_id,
                         text="Sensor started")
    bot.send_message(chat_id=chat_id,
                         text="Supported commands:",
                         reply_markup=InlineKeyboardMarkup(keyboard))
    
def stop_sensor(chat_id):
    global keyboard
    global last_chat_id
    
    last_chat_id = -1
    isSensorEnabled = False
    
    GPIO.output(LED_PIN, GPIO.LOW)
    
    keyboard = [
        [InlineKeyboardButton("Start sensor", callback_data='start_sensor')],
        [
            InlineKeyboardButton("Get capture", callback_data='get_capture'),
            InlineKeyboardButton("Get video", callback_data='get_video')
        ],
    ]

    bot.send_message(chat_id=chat_id,
                         text="Sensor stop requested")

def mute_notifications(chat_id):
    global keyboard
    
    isMuteNotifications = True
    
    keyboard = [
        [
            InlineKeyboardButton("Stop sensor", callback_data='stop_sensor'),
            InlineKeyboardButton("Unmute notifications", callback_data='unmute_notifications')
        ]
    ]

    bot.send_message(chat_id=chat_id,
                         text="Notifications muted")
    bot.send_message(chat_id=chat_id,
                         text="Supported commands:",
                         reply_markup=InlineKeyboardMarkup(keyboard))

def unmute_notifications(chat_id):
    global keyboard
    
    isMuteNotifications = False
    
    keyboard = [
        [
            InlineKeyboardButton("Stop sensor", callback_data='stop_sensor'),
            InlineKeyboardButton("Mute notifications", callback_data='mute_notifications')
        ]
    ]

    bot.send_message(chat_id=chat_id,
                         text="Notifications unmuted")
    bot.send_message(chat_id=chat_id,
                         text="Supported commands:",
                         reply_markup=InlineKeyboardMarkup(keyboard))

@bot.callback_query_handler(func=lambda call: True)
def button(call):
    globals()[call.data](call.message.chat.id)

def main():
    setup()
    bot.polling(none_stop=False, interval=5, timeout=20)
    destroy()

if __name__ == '__main__':
    main()