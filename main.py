# this project has been written  by ILTERAY for MEKAR company
import time
from time import sleep
from struct import unpack
import network
import machine
import json
import socket
import math
import gc
import BlynkLib
import wifimgr
from ssd1351 import Display, color565
from machine import Pin, SPI, ADC
from xglcd_font import XglcdFont
from mfrc522 import MFRC522
from struct import unpack
from hx711_pio import HX711
# hx711 pin definitions
pin_OUT = Pin(7, Pin.IN, pull=Pin.PULL_DOWN)
pin_SCK = Pin(6, Pin.OUT)
hx711 = HX711(pin_SCK, pin_OUT)
# ----------------#
gc.enable()
with open('config.json', 'r') as f:  # read the json file
    config = json.load(f)
"""termistor pin tanimlama"""
thermistor = machine.ADC(26)
"""screen spi begin"""
spi = SPI(1, baudrate=48000000, sck=Pin(10), mosi=Pin(11))
display = Display(spi, dc=Pin(12), cs=Pin(13), rst=Pin(14))
"""card reader spi begin"""
reader = MFRC522(spi_id=0, sck=2, miso=4, mosi=3, cs=1, rst=0)
""" Setup the Rotary Encoder"""
sw_pin = Pin(16, Pin.IN, Pin.PULL_UP)
clk_pin = Pin(17, Pin.IN, Pin.PULL_UP)
dt_pin = Pin(18, Pin.IN, Pin.PULL_UP)
previous_value = True
button_down = False
""""cooler & mixer pin definition"""
cooler_pin = Pin(20, Pin.OUT)
mixer_pin = Pin(21, Pin.OUT)
"""fonts prepairing"""
arcadepix = XglcdFont('fonts/ArcadePix9x11.c', 9, 11)
unispace = XglcdFont('fonts/Unispace12x24.c', 12, 24)
"""constants"""
width = 128
height = 128
line = 1
highlight = 1
shift = 0
list_length = 0
previous_C = 0
previous_gr = 0
previous_ml = 0
steinhart_y = 40
weight_y = steinhart_y + 24
liter_y = weight_y + 24
display.contrast(config['brightness'])
mixer_state = False
temp_treshould_state = False
last_toggle_time = time.ticks_ms()


def write_config():
    with open('config.json', 'w') as f:
        json.dump(config, f)


def center_text(y, text, font, color):
    global center, w
    w = font.measure_text(text)  # Measure length of text in pixels
    # Calculate position for centered text
    center = int(display.width / 2 - w / 2)
    display.draw_text(center, y, text, font, color)
    return center


def draw_image(image_path, x, y, width, height):
    display.draw_image(image_path, x, y, width, height)


def home():
    global text
    display.clear()
    if network.WLAN(network.STA_IF).isconnected():
        draw_image('assets/4.raw', 102, 0, 24, 24)  # offline icon
    elif network.WLAN(network.STA_IF).isconnected() == False:
        draw_image('assets/3.raw', 102, 0, 24, 24)  # online icon
    if cooler_pin.value() == 0:
        draw_image('assets/8.raw', 0, 0, 24, 24)  # cooler off icon
    elif cooler_pin.value() == 1:
        draw_image('assets/2.raw', 0, 0, 24, 24)  # cooler on icon
    if mixer_pin.value() == 0:
        draw_image('assets/10.raw', 25, 0, 24, 24)  # mixer off icon
    elif mixer_pin.value() == 1:
        draw_image('assets/6.raw', 25, 0, 24, 24)  # mixer on icon
    if mixer_pin.value() == 0 or cooler_pin.value() == 0:
        draw_image('assets/11.raw', 50, 0, 24, 24)  # mixer & cooler off icon
    elif mixer_pin.value() == 1 and cooler_pin.value() == 1:
        draw_image('assets/7.raw', 50, 0, 24, 24)  # mixer & cooler on icon
    if config['fancond'] == 0:
        draw_image('assets/9.raw', 75, 0, 24, 24)  # fan off icon
    elif config['fancond'] == 1:
        draw_image('assets/5.raw', 75, 0, 0, 24)  # fan on icon
    if config['alertcond'] == 1:
        draw_image('assets/alarm.raw', 0, 52, 24, 24)  # alert icon


def read_uids():
    with open("card_lib.dat") as f:
        lines = f.readlines()
    return [line.strip("\n") for line in lines]


def rfidread():
    display.clear()
    center_text(0, "KART OKUT", arcadepix, color565(
        0, 255, 0))  # call for center the text
    draw_image('assets/rfidread.raw', 14, 14, 100, 100)
    rfid_timout = 0
    while rfid_timout <= 20:
        reader.init()
        (stat, tag_type) = reader.request(reader.REQIDL)
        # print('request stat:',stat,' tag_type:',tag_type)
        if stat == reader.OK:
            (stat, uid) = reader.SelectTagSN()
            if stat == reader.OK:
                PreviousCard = uid
                try:
                    uids = read_uids()
                except BaseException:
                    uids = []
                if reader.tohexstring(
                        uid) == '[0xD3, 0x56, 0xCE, 0x95]' or reader.tohexstring(uid) in uids:
                    access = True
                    rfiddone()
                    sleep(1)
                    gc.collect()
                    mainmenu()
                else:
                    rfidno()
                    break
            else:
                pass
        else:
            PreviousCard = [0]
        rfid_timout += 1
        sleep(0.5)
    home()


def rfiddone():
    display.clear()
    center_text(0, "KART OKUNDU", arcadepix, color565(
        72, 222, 105))  # call for center the text
    draw_image('assets/rfiddone.raw', 14, 20, 100, 100)


def rfidno():
    display.clear()
    center_text(
        0,
        "GECERSIZ KART",
        arcadepix,
        color565(
            198,
            59,
            59))  # call for center the text
    draw_image('assets/rfidno.raw', 14, 20, 100, 100)
    sleep(2)
    home()


def draw_message(text):
    display.fill_rectangle(0, 115, 128, 13, color565(0, 0, 0))
    display.draw_text(0, 115, text, arcadepix, color565(255, 255, 255))


def set_time():  # get time function
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    addr = socket.getaddrinfo("pool.ntp.org", 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
    finally:
        s.close()
    val = unpack("!I", msg[40:44])[0]
    t = val - 2208978000  # gmt+3 saat dilimini ayarladik
    tm = time.gmtime(t)
    machine.RTC().datetime(
        (tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))


def display_time():
    dcurrent_time = "{}.{}.{} {:02d}:{:02d}".format(
        machine.RTC().datetime()[2], machine.RTC().datetime()[1], machine.RTC().datetime()[0], int(
            machine.RTC().datetime()[4]), int(
            machine.RTC().datetime()[5]))
    center_text(30, dcurrent_time, arcadepix, color565(
        255, 255, 255))  # call for center the text


def temperature():
    global previous_C, steinhart, blynk
    temperature_reads = [thermistor.read_u16() for _ in range(5)]
    temperature_value = sum(temperature_reads) / len(temperature_reads)
    try:
        R = 100000 / (65535 / temperature_value - 1)
        steinhart = math.log(R / 10000.0) / 3950.0
        steinhart += 1.0 / (25.0 + 273.15)
        steinhart = (1.0 / steinhart) - 273.15 + config['thermistor_offset']
        if previous_C != unispace.measure_text(str(round(steinhart, 1))):
            center_text(steinhart_y, "       ", unispace, color565(0, 255, 0))
        center_text(
            steinhart_y, str(
                round(
                    steinhart, 1)), unispace, color565(
                0, 255, 0))
        display.draw_text(center +
                          unispace.measure_text(str(round(steinhart, 1))) +
                          5, steinhart_y +
                          10, "C", arcadepix, color565(255, 255, 255))
        previous_C = unispace.measure_text(str(round(steinhart, 1)))
        return steinhart
    except BaseException:
        draw_message("HATA [T1]")
    if network.WLAN(network.STA_IF).isconnected():
        try:
            if steinhart > config['cooler']['tempmax']:
                blynk.log_event("high_temperature")
            elif steinhart < config['cooler']['tempmin']:
                blynk.log_event("lower_temp")
            blynk.virtual_write(5, steinhart)
        except Exception as e:
            print("temperautre sync error:", e)
    del temperature_reads


def weight():
    global previous_gr, previous_ml, blynk
    weights = []
    for i in range(5):
        weights.append(
            ((hx711.read() /
              config['weight']['scale_factor']) -
                config['weight']['self_weight']))
    # okunan raw values degerlerinin ortalamasi alinir
    weight = round((sum(weights) / len(weights)))
    if weight <= 1:
        weight = 0
    liter = round((weight / 1.033))

    if previous_gr != unispace.measure_text(str(weight)):
        center_text(
            weight_y,
            "              ",
            unispace,
            color565(
                0,
                0,
                255))  # call for center the text
    if previous_ml != unispace.measure_text(str(liter)):
        center_text(
            liter_y,
            "              ",
            unispace,
            color565(
                0,
                0,
                255))  # call for center the text
    center_text(
        weight_y,
        str(weight),
        unispace,
        color565(
            0,
            0,
            255))  # call for center the text
    display.draw_text(
        center +
        unispace.measure_text(
            str(weight)) +
        5,
        weight_y +
        10,
        "kg",
        arcadepix,
        color565(
            37,
            80,
            255))  # KG
    previous_gr = unispace.measure_text(str(weight))
    center_text(
        liter_y,
        str(liter),
        unispace,
        color565(
            255,
            80,
            37))  # call for center the text
    display.draw_text(
        center +
        unispace.measure_text(
            str(liter)) +
        5,
        liter_y +
        10,
        "L",
        arcadepix,
        color565(
            255,
            80,
            0))  # L
    previous_ml = unispace.measure_text(str(liter))
    if network.WLAN(network.STA_IF).isconnected():
        try:
            blynk.virtual_write(10, weight)
        except Exception as e:
            print("Weight sync errror:", e)
            draw_message("HATA [W]")

    del weights


temperature()


def init_blynk():
    try:
        return BlynkLib.Blynk(wifimgr.read_blynk_auth())
    except BaseException:
        return None


try:
    draw_message("wifi baglaniyor")
    wifimgr.get_connection('first_start')
except Exception as e:
    print("wifimgr hatsi: ", e)
    draw_message("wifi baglanamdi")
try:
    blynk = init_blynk()

    @blynk.on("connected")
    def blynk_connected(ping):
        draw_message("Server Baglandi")

    @blynk.on("disconnected")
    def blynk_disconnected():
        draw_message("Baglanti Kesildi")
        home()

    @blynk.on("V*")
    def blynk_handle_vpins(pin, value):
        if pin == '0' and config['cooler']['tempset'] != round(
                float(value[0]), 1):
            config['cooler']['tempset'] = round(float(value[0]), 1)
            write_config()
            draw_message("tempset: {}".format(config['cooler']['tempset']))
        elif pin == '1':
            if value[0] == '1' and config['cooler']['coolercond'] == 'PASIF':
                config['cooler']['coolercond'] = 'AKTIF'
                cooler_pin.value(1)
                home()
                draw_message(
                    "SOGUTUCU: {}".format(
                        config['cooler']['coolercond']))
            elif value[0] == '0' and config['cooler']['coolercond'] == 'AKTIF':
                config['cooler']['coolercond'] = 'PASIF'
                cooler_pin.value(0)
                home()
                draw_message(
                    "SOGUTUCU: {}".format(
                        config['cooler']['coolercond']))
            write_config()
        elif pin == '2' and config['cooler']['tempmax'] != round(float(value[0]), 1):
            config['cooler']['tempmax'] = round(float(value[0]), 1)
            write_config()
            draw_message("MAX UYARI: {}".format(config['cooler']['tempmax']))
        elif pin == '3' and config['cooler']['tempmin'] != round(float(value[0]), 1):
            config['cooler']['tempmin'] = round(float(value[0]), 1)
            write_config()
            draw_message("MIN UYARI: {}".format(config['cooler']['tempmin']))
        elif pin == '4':
            if value[0] == '1' and config['mixer']['mixercond'] == 'PASIF':
                config['mixer']['mixercond'] = 'AKTIF'
                mixer_pin.value(1)
                home()
                draw_message(
                    "KARIST. : {}".format(
                        config['mixer']['mixercond']))
            elif value[0] == '0' and config['mixer']['mixercond'] == 'AKTIF':
                config['mixer']['mixercond'] = 'PASIF'
                mixer_pin.value(0)
                home()
                draw_message(
                    "KARIST. : {}".format(
                        config['mixer']['mixercond']))
            write_config()
        elif pin == '6' and config['mixer']['mixerwork'] != int(round(float(value[0]), 0)):
            config['mixer']['mixerwork'] = int(round(float(value[0]), 0))
            write_config()
            draw_message(
                "KARIST. C: {} DK".format(
                    config['mixer']['mixerwork']))
        elif pin == '7' and config['mixer']['mixerwait'] != int(round(float(value[0]), 0)):
            config['mixer']['mixerwait'] = int(round(float(value[0]), 0))
            write_config()
            draw_message(
                "KARIST. B: {} DK".format(
                    config['mixer']['mixerwait']))
        elif pin == '8' and config['cooler']['temptolerance'] != round(float(value[0]), 1):
            config['cooler']['temptolerance'] = round(float(value[0]), 1)
            write_config()
            draw_message(
                "TOLERANS: {}".format(
                    config['cooler']['temptolerance']))
        elif pin == '9' and config['thermistor_offset'] != round(float(value[0]), 1):
            config['thermistor_offset'] = round(float(value[0]), 1)
            write_config()
            draw_message("T OFFSET: {}".format(config['thermistor_offset']))
except Exception as e:
    print("blynk virtual sync", e)


def mixer_toogle(current_time):
    global mixer_state, temp_treshould_state, last_toggle_time
    try:
        cooler_pin.value(0)
        if mixer_state == False and (
                current_time -
                last_toggle_time) >= (
                config['mixer']['mixerwork'] *
                60000):  # 60000 olacak
            mixer_pin.value(0)
            mixer_state = True
            last_toggle_time = current_time
            home()
        if mixer_state and (
                current_time -
                last_toggle_time) >= (
                config['mixer']['mixerwait'] *
                60000):
            mixer_pin.value(1)
            mixer_state = False
            last_toggle_time = current_time
            home()
    except Exception as e:
        print("toggle error:", e)


def home_returner():
    try:
        gc.collect()
        main()
    except Exception as e:
        print("otomatik dönmedi", e)
        machine.reset()


def mainmenureturner():
    try:
        gc.collect()
        mainmenu()
    except Exception as e:
        machine.reset()


def blynkrun():
    if network.WLAN(network.STA_IF).isconnected():
        try:
            blynk.run()  # blynk cloud connection
        except Exception as e:
            print("blynk.run(): ", e)


home()

"""--------------------------------------------------------------------------------"""
"""---------------------------------ABOUT------------------------------------------"""
"""--------------------------------------------------------------------------------"""


def about_page():
    global button_down, previous_value

    def aboutpage():
        display.clear()
        center_text(0, "HAKKINDA", arcadepix, color565(0, 255, 0))
        center_text(30, "MEKAR", unispace, color565(255, 0, 0))
        center_text(
            70,
            "mekarteknoloji.com",
            arcadepix,
            color565(
                255,
                255,
                255))
        center_text(100, config['version'], arcadepix, color565(255, 255, 255))

    def returner():
        gc.collect()
        mainmenu()
    aboutpage()
    previous_time = time.ticks_ms()

    while True:
        try:
            gc.collect()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time
            # Check for encoder rotated
            if previous_value != dt_pin.value():
                previous_time = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        returner()
                    # Turned Right
                    else:
                        returner()
                previous_value = dt_pin.value()

            if sw_pin.value() == False and not button_down:
                previous_time = current_time
                button_down = True
                returner()
                sleep(0.01)

            if sw_pin.value() and button_down:
                button_down = False
            sleep(0.01)
            if elapsed_time >= 30000:  # 1 saniye geçti
                previous_time = current_time  # Geçen zamanı sıfırla
                home_returner()
        except Exception as e:
            print(e)


"""--------------------------------------------------------------------------------"""
"""-------------------------------ABOUT END----------------------------------------"""
"""--------------------------------------------------------------------------------"""

"""--------------------------------------------------------------------------------"""
"""--------------------------------SETTINGS----------------------------------------"""
"""--------------------------------------------------------------------------------"""


def settings_menu():
    global button_down, blynk, previous_value, highlight, shift
    box = ['', config['thermistor_offset'],
           config['brightness'], '', '', '', '']
    file_list = [
        '< GERI',
        'T OFFSET',
        'KONTRST',
        'WIFI',
        'KART EKLE',
        'KART SIL',
        'GUNCELLE',
        'SIFIRLA']
    if len(file_list) >= 6:
        total_lines = 6
    else:
        total_lines = len(file_list)

    def read_uids():
        with open("card_lib.dat") as f:
            lines = f.readlines()
        uids = []
        for line in lines:
            uids.append(line.strip("\n"))
        return uids

    def write_uids(uids):
        with open("card_lib.dat", "a") as f:
            f.write("%s\n" % (uids))

    def card_generator(cond):
        display.clear()
        center_text(0, "KART EKLEME", arcadepix, color565(0, 255, 0))
        center_text(50, "KART", arcadepix, color565(0, 255, 0))
        center_text(64, "OKUTUN", arcadepix, color565(0, 255, 0))
        from mfrc522 import MFRC522
        import utime

        def uidToString(uid):
            mystring = ""
            for i in uid:
                mystring = "%02X" % i + mystring
            return mystring
        reader = MFRC522(spi_id=0, sck=2, miso=4, mosi=3, cs=1, rst=0)
        try:
            while True:
                reader.init()
                (stat, tag_type) = reader.request(reader.REQIDL)
                # print('request stat:',stat,' tag_type:',tag_type)
                if stat == reader.OK:
                    (stat, uid) = reader.SelectTagSN()
                    if stat == reader.OK:
                        try:
                            uids = read_uids()
                        except Exception as e:
                            uids = {}
                            print(e)
                        if cond == 'add':
                            if reader.tohexstring(uid) in uids:
                                center_text(
                                    50, "KART", arcadepix, color565(
                                        0, 255, 0))
                                center_text(
                                    64, "KAYITLI", arcadepix, color565(
                                        180, 0, 0))
                                time.sleep_ms(1000)
                            else:
                                write_uids(reader.tohexstring(uid))
                                center_text(
                                    50, "KART", arcadepix, color565(
                                        0, 255, 0))
                                center_text(
                                    64, "KAYDEDILDI", arcadepix, color565(
                                        0, 255, 0))
                                time.sleep_ms(1000)
                        elif cond == 'delete':
                            if reader.tohexstring(uid) in uids:
                                uids.remove(reader.tohexstring(uid))
                                with open("card_lib.dat", "w") as f:
                                    for line in uids:
                                        f.write(line)
                                center_text(
                                    50, "KART", arcadepix, color565(
                                        0, 255, 0))
                                center_text(
                                    64, "SILINDI", arcadepix, color565(
                                        0, 255, 0))
                                time.sleep_ms(1000)
                            else:
                                center_text(
                                    50, "KART", arcadepix, color565(
                                        0, 255, 0))
                                center_text(
                                    64, "LISTEDE YOK", arcadepix, color565(
                                        0, 0, 255))
                                time.sleep_ms(1000)
                        PreviousCard = uid
                        break
                    else:
                        pass
                else:
                    PreviousCard = [0]
                time.sleep_ms(50)

        except KeyboardInterrupt:
            pass

    def set_brghts(a, setid):
        display.clear()
        global previous_value, button_down
        center_text(int((display.height - unispace.height - 2) / 2),
                    str(a), unispace, color565(0, 255, 0))
        while True:
            if previous_value != dt_pin.value():
                if dt_pin.value() == False:
                    if clk_pin.value() == False:
                        if setid == 1:
                            a -= 1
                            a = round(a)
                            if a <= 0:
                                a = 0
                        elif setid == 0:
                            a -= 0.1
                            a = round(a, 1)
                        display.clear()
                        center_text(int((display.height - unispace.height - 2) / 2),
                                    str(a), unispace, color565(0, 255, 0))
                        if setid == 1:
                            display.contrast(a)
                        time.sleep_ms(10)
                    else:
                        if setid == 1:
                            a += 1
                            a = round(a)
                            if a >= 15 and setid == 1:
                                a = 15
                        elif setid == 0:
                            a += 0.1
                            a = round(a, 1)
                        display.clear()
                        center_text(int((display.height - unispace.height - 2) / 2),
                                    str(a), unispace, color565(0, 255, 0))
                        if setid == 1:
                            display.contrast(a)
                        time.sleep_ms(10)
                previous_value = dt_pin.value()
            time.sleep_ms(10)
            if sw_pin.value() == False and not button_down:
                button_down = True
                if setid == 1:
                    config['brightness'] = a
                    box[3] = config['brightness']
                elif setid == 0:
                    config['thermistor_offset'] = a
                    box[1] = config['thermistor_offset']
                write_config()
                time.sleep_ms(10)
                break
            time.sleep_ms(10)

            if sw_pin.value() and button_down:
                button_down = False
            time.sleep_ms(10)
        return a

    def show_menu(menu, box):
        """ Shows the menu on the screen"""
        # bring in the global variables
        global line, highlight, shift, list_length
        # menu variables
        item = 1
        boxitem = 2
        line = 1
        line_height = 20
        # display.fill_rectangle(0, 0, width , height, color565(128, 0, 255)) #background color
        # Shift the list of files so that it shows on the display
        list_length = len(menu)
        short_list = menu[shift:shift + total_lines]
        box_list_length = len(box)
        sort_box_list = box[shift:shift + total_lines]
        display.clear()
        for item, boxitem in zip(short_list, sort_box_list):
            if highlight == line:
                display.draw_text(
                    0,
                    (line - 1) * line_height + 5,
                    '>',
                    arcadepix,
                    color565(
                        255,
                        255,
                        255))  # menu item pointer
                display.draw_text(
                    10,
                    (line - 1) * line_height + 5,
                    item,
                    arcadepix,
                    color565(
                        255,
                        255,
                        255))  # menu item text
                display.draw_text(
                    90,
                    (line - 1) * line_height + 5,
                    str(boxitem),
                    arcadepix,
                    color565(
                        0,
                        255,
                        0))  # menu item's values
            else:
                display.draw_text(
                    10,
                    (line - 1) * line_height + 5,
                    item,
                    arcadepix,
                    color565(
                        255,
                        255,
                        255))  # rest of menu items
                display.draw_text(
                    90,
                    (line - 1) * line_height + 5,
                    str(boxitem),
                    arcadepix,
                    color565(
                        0,
                        255,
                        0))  # rest of menu items's values
            line += 1

    def factory_settings():
        try:
            config['mixer']['mixercond'] = config['default']['mixercond']
            config['mixer']['mixerwait'] = config['default']['mixerwait']
            config['mixer']['mixerwork'] = config['default']['mixerwork']
            config['cooler']['temptolerance'] = config['default']['temptolerance']
            config['cooler']['tempmin'] = config['default']['tempmin']
            config['cooler']['coolercond'] = config['default']['coolercond']
            config['cooler']['tempmax'] = config['default']['tempmax']
            config['cooler']['tempset'] = config['default']['tempset']
            config['fancond'] = config['default']['fancond']
            config['thermistor_offset'] = config['default']['thermistor_offset']
            config['brightness'] = config['default']['brightness']
            config['setup'] = 'false'
            os.remove('wifi.dat')
            os.remove('card_lib.dat')
            write_config()
            time.sleep(1)
        except BaseException:
            display.clear()
            center_text(
                0, "SIFIRLAMA HATSAI", arcadepix, color565(
                    72, 222, 105))  # call for center the text
        machine.reset()

    def wifi_client_setup():
        display.clear()
        center_text(60, "WIFI KURULUMU", arcadepix, color565(0, 255, 0))
        time.sleep_ms(1000)
        display.clear()
        center_text(10, "WIFI ISMI:", arcadepix, color565(0, 255, 0))
        center_text(30, "MEKAR DEVICE", arcadepix, color565(255, 255, 255))
        center_text(50, "SIFRE:", arcadepix, color565(0, 255, 0))
        center_text(70, "asdfghjk", arcadepix, color565(255, 255, 255))
        center_text(90, "IP:", arcadepix, color565(0, 255, 0))
        center_text(110, "192.168.4.1", arcadepix, color565(255, 255, 255))
        wlan = wifimgr.get_connection()
        if network.WLAN(network.STA_IF).isconnected():
            display.clear()
            center_text(60, "BAGLI", arcadepix, color565(0, 255, 0))
            time.sleep_ms(2000)
        if not network.WLAN(network.STA_IF).isconnected():
            display.clear()
            center_text(60, "HATA", arcadepix, color565(255, 0, 0))
            time.sleep_ms(2000)

    def launch(filename):
        if filename == '< GERI':
            mainmenureturner()
        elif filename == 'T OFFSET':
            setid = 0
            set_brghts(config['thermistor_offset'], setid)
        elif filename == 'KONTRST':
            setid = 1
            set_brghts(config['brightness'], setid)
        elif filename == 'SIFIRLA':
            factory_settings()
        elif filename == 'WIFI':
            wifi_client_setup()
        elif filename == 'KART EKLE':
            card_generator('add')
        elif filename == 'KART SIL':
            card_generator('delete')
        elif filename== 'GUNCELLE':
            if network.WLAN(STA_IF).isconnected():
                center_text(60,"GUNCELLENIYOR", arcadepix,color565(255,0,0))
                exec(open('updater.py').read())
            else:
                display.clear()
                center_text(60,"WIFI", arcadepix,color565(255,0,0))
                center_text(80,"BAGLANTISI", arcadepix,color565(255,0,0))
                center_text(100,"YOK", arcadepix,color565(255,0,0))
    show_menu(file_list, box)
    previous_time = time.ticks_ms()
    msg_prev_time = time.ticks_ms()
    while True:
        try:
            gc.collect()
            blynkrun()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time
            msg_runout_time = current_time - msg_prev_time
            # Check for encoder rotated
            if previous_value != dt_pin.value():
                previous_time = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        if highlight > 1:
                            highlight -= 1
                        else:
                            if shift > 0:
                                shift -= 1
                    # Turned Right
                    else:
                        if highlight < total_lines:
                            highlight += 1
                        else:
                            if shift + total_lines < list_length:
                                shift += 1
                    show_menu(file_list, box)
                previous_value = dt_pin.value()
            time.sleep_ms(5)

            if sw_pin.value() == False and not button_down:
                previous_time = current_time
                button_down = True
                launch(file_list[(highlight - 1) + shift])
                show_menu(file_list, box)
            time.sleep_ms(5)

            if sw_pin.value() and button_down:
                button_down = False
            time.sleep_ms(5)
            if elapsed_time >= 1000:  # 1 saniye geçti
                previous_time = current_time  # Geçen zamanı sıfırla
                if network.WLAN(network.STA_IF).isconnected():
                    try:
                        blynk.virtual_write(9, config['thermistor_offset'])
                    except Exception as e:
                        print(e)
            if msg_runout_time >= 30000:  # 1 saniye geçti
                msg_prev_time = current_time
                home_returner()
        except Exception as e:
            print(e)
            machine.reset()


"""--------------------------------------------------------------------------------"""
"""-------------------------------SETTINGS END-------------------------------------"""
"""--------------------------------------------------------------------------------"""

"""--------------------------------------------------------------------------------"""
"""----------------------------------WEIGHT----------------------------------------"""
"""--------------------------------------------------------------------------------"""


def weight_menu():
    global button_down, temp_treshould_state, blynk, previous_value, highlight, shift
    box = [
        '',
        '',
        '',
        '',
        config['weight']['scale_factor'],
        config['weight']['self_weight']]
    file_list = [
        '< GERI',
        config['weight']['weightcond'],
        'DARA',
        'KALIBRASYON',
        'CARPAN A.',
        'TANK AG.']
    if len(file_list) >= 6:
        total_lines = 6
    else:
        total_lines = len(file_list)
    steinhart_y = 40
    weight_y = steinhart_y + 24
    liter_y = weight_y + 24

    def set_temp(a, setid):
        display.clear()
        global previous_value, button_down
        center_text(int((display.height - unispace.height - 2) / 2),
                    str(a), unispace, color565(0, 255, 0))
        while True:
            if previous_value != dt_pin.value():
                if dt_pin.value() == False:
                    if clk_pin.value() == False:
                        a -= 1
                        a = round(a)
                        if a <= 0:
                            a = 0
                        display.clear()
                        center_text(int((display.height - unispace.height - 2) / 2),
                                    str(a), unispace, color565(0, 255, 0))
                        sleep(0.01)
                    else:
                        a += 1
                        a = round(a)
                        display.clear()
                        center_text(int((display.height - unispace.height - 2) / 2),
                                    str(a), unispace, color565(0, 255, 0))
                        sleep(0.01)
                    try:
                        if setid == 1:
                            weights = []
                            for i in range(5):
                                weights.append(
                                    ((hx711.read() / a) - config['weight']['self_weight']))
                            # okunan raw values degerlerinin ortalamasi alinir
                            weight = round((sum(weights) / len(weights)), 2)
                            center_text(
                                80, str(weight), unispace, color565(
                                    0, 0, 255))  # call for center the text
                            display.draw_text(
                                center +
                                unispace.measure_text(
                                    str(weight)) +
                                5,
                                weight_y +
                                10,
                                "KG",
                                arcadepix,
                                color565(
                                    37,
                                    80,
                                    255))  # gr
                            del weights
                    except Exception as e:
                        print(e)
                previous_value = dt_pin.value()
            if sw_pin.value() == False and not button_down:
                button_down = True
                a = round(a)
                if setid == 1:
                    config['weight']['scale_factor'] = a
                    box[4] = config['weight']['scale_factor']
                elif setid == 2:
                    config['weight']['self_weight'] = a
                    box[5] = config['weight']['self_weight']
                write_config()
                break
            sleep(0.01)

            if sw_pin.value() and button_down:
                button_down = False
            sleep(0.01)
        return a

    def show_menu(menu, box):
        """ Shows the menu on the screen"""
        # bring in the global variables
        global line, highlight, shift, list_length
        # menu variables
        item = 1
        line = 1
        line_height = 20
        # display.fill_rectangle(0, 0, width , height, color565(128, 0, 255)) #background color
        # Shift the list of files so that it shows on the display
        list_length = len(menu)
        short_list = menu[shift:shift + total_lines]
        box_list_length = len(box)
        sort_box_list = box[shift:shift + total_lines]
        display.clear()
        for item, boxitem in zip(short_list, sort_box_list):
            if highlight == line:
                # display.fill_rectangle(0,(line-1)*line_height,
                # width,line_height,color565(46, 56, 64)) #highlighted area for
                # each menu item
                display.draw_text(
                    0,
                    (line - 1) * line_height + 5,
                    '>',
                    arcadepix,
                    color565(
                        255,
                        255,
                        255))  # menu item pointer
                if item == "AKTIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            0,
                            255,
                            0))  # menu item text
                elif item == "PASIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            0,
                            0))  # menu item text
                else:
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            255,
                            255))  # menu item text
                display.draw_text(
                    90,
                    (line - 1) * line_height + 5,
                    str(boxitem),
                    arcadepix,
                    color565(
                        0,
                        255,
                        0))  # menu item's values
            else:
                if item == "AKTIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            0,
                            255,
                            0))  # menu item text
                elif item == "PASIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            0,
                            0))  # menu item text
                else:
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            255,
                            255))  # menu item text
                # display.draw_text(10, (line-1)*line_height +5, item ,
                # arcadepix, color565(255, 255, 255)) #rest of menu items
                display.draw_text(
                    90,
                    (line - 1) * line_height + 5,
                    str(boxitem),
                    arcadepix,
                    color565(
                        0,
                        255,
                        0))  # rest of menu items's values
            line += 1

    def calibrate_weight_sensor():
        global button_down
        display.clear()
        center_text(55, "20kg AGIRLIGI", arcadepix, color565(0, 255, 0))
        center_text(70, "KOYUN", arcadepix, color565(0, 255, 0))
        measurement = False
        while measurement != True:
            if sw_pin.value() == False and not button_down:
                button_down = True

                raw_values1 = []
                for i in range(5):
                    raw_values1.append(hx711.read())
                # okunan raw values degerlerinin ortalamasi alinir
                raw_value1 = sum(raw_values1) / len(raw_values1)
                measurement = True
                sleep(1)

            if sw_pin.value() and button_down:
                button_down = False
        sleep(0.01)
        display.clear()
        center_text(55, "20kg AGIRLIGI", arcadepix, color565(0, 255, 0))
        center_text(70, "ALIN", arcadepix, color565(0, 255, 0))
        sleep(2)
        display.clear()
        center_text(55, "60kg AGIRLIGI", arcadepix, color565(0, 255, 0))
        center_text(70, "KOYUN", arcadepix, color565(0, 255, 0))
        measurement = False
        while measurement != True:
            if sw_pin.value() == False and not button_down:
                button_down = True

                raw_values2 = []
                for i in range(5):
                    raw_values2.append(hx711.read())
                # okunan raw values degerlerinin ortalamasi alinir
                raw_value2 = sum(raw_values2) / len(raw_values2)
                measurement = True
                sleep(1)

            if sw_pin.value() and button_down:
                button_down = False
        sleep(0.01)
        try:
            # scale factor  ortalamasi alinir
            scale_factor = round(
                (raw_value1 - raw_value2) / (float(20) - float(60)))
            config['weight']['scale_factor'] = scale_factor
            display.clear()
            write_config()
            center_text(55, "KALIBRASYON", arcadepix, color565(0, 255, 0))
            center_text(70, "TAMAM", arcadepix, color565(0, 255, 0))
            sleep(2)
        except BaseException:
            display.clear()
            center_text(55, "KALIBRASYON", arcadepix, color565(0, 255, 0))
            center_text(70, "HATASI", arcadepix, color565(0, 255, 0))
            sleep(2)

    def tare():
        display.clear()
        center_text(55, "DARA ALINIYOR", arcadepix, color565(0, 255, 0))
        tares = []
        for i in range(5):
            tares.append(hx711.read())
        config['weight']['self_weight'] = round(
            ((sum(tares) / len(tares)) / config['weight']['scale_factor']),
            1)  # okunan raw values degerlerinin ortalamasi alinir
        write_config()
        time.sleep_ms(1000)
        display.clear()
        center_text(55, "DARA ALINDI", arcadepix, color565(0, 255, 0))
        time.sleep_ms(1000)

    def launch(filename):
        if filename == '< GERI':
            mainmenureturner()
        elif filename == file_list[1]:
            if config['weight']['weightcond'] == "AKTIF":
                config['weight']['weightcond'] = "PASIF"
            elif config['weight']['weightcond'] == "PASIF":
                config['weight']['weightcond'] = "AKTIF"
            write_config()
            file_list[1] = config['weight']['weightcond']
        elif filename == 'CARPAN A.':
            set_temp(config['weight']['scale_factor'], 1)
        elif filename == 'KALIBRASYON':
            calibrate_weight_sensor()
        elif filename == 'DARA':
            tare()
        elif filename == 'TANK AG.':
            set_temp(config['weight']['self_weight'], 2)
    show_menu(file_list, box)
    previous_time = time.ticks_ms()
    screen_timeout_in = time.ticks_ms()
    while True:
        try:
            gc.collect()
            blynkrun()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time  # Geçen süreyi kontrol et
            screen_timeout = current_time - screen_timeout_in  # Geçen süreyi kontrol et
            if elapsed_time >= 1000:  # 1 saniye geçti
                #             if network.WLAN(network.STA_IF).isconnected():
                #                 try:
                #                     blynk.virtual_write(4,config['mixer']['mixercond'])
                #                     blynk.virtual_write(6,config['mixer']['mixerwork'])
                #                     blynk.virtual_write(7,config['mixer']['mixerwait'])
                #                 except Exception as e:
                #                     print("blynk.wirtual_write(): ",e)
                previous_time = current_time  # Geçen zamanı sıfırla
            if previous_value != dt_pin.value():
                screen_timeout_in = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        if highlight > 1:
                            highlight -= 1
                        else:
                            if shift > 0:
                                shift -= 1
                    else:
                        if highlight < total_lines:
                            highlight += 1
                        else:
                            if shift + total_lines < list_length:
                                shift += 1
                    show_menu(file_list, box)
                previous_value = dt_pin.value()
            if sw_pin.value() == False and not button_down:
                screen_timeout_in = current_time
                button_down = True
                launch(file_list[(highlight - 1) + shift])
                show_menu(file_list, box)
            sleep(0.01)
            if sw_pin.value() and button_down:
                button_down = False
            sleep(0.01)
            if screen_timeout >= 30000:  # 1 saniye geçti
                screen_timeout_in = current_time  # Geçen zamanı sıfırla
                home_returner()
        except Exception as e:
            print("while(): ", e)


"""--------------------------------------------------------------------------------"""
"""--------------------------------WEIGHT END--------------------------------------"""
"""--------------------------------------------------------------------------------"""


"""--------------------------------------------------------------------------------"""
"""----------------------------------MIXER-----------------------------------------"""
"""--------------------------------------------------------------------------------"""


def mixer_menu():
    global button_down, temp_treshould_state, blynk, previous_value, highlight, shift
    box = ['', '', config['mixer']['mixerwork'], config['mixer']['mixerwait']]
    file_list = [
        '< GERI',
        config['mixer']['mixercond'],
        'CALISMA DK',
        'BEKLEME DK']
    if len(file_list) >= 6:
        total_lines = 6
    else:
        total_lines = len(file_list)

    def set_temp(a, setid):
        display.clear()
        global previous_value, button_down
        center_text(int((display.height - unispace.height - 2) / 2),
                    str(a), unispace, color565(0, 255, 0))
        while True:
            if previous_value != dt_pin.value():
                if dt_pin.value() == False:
                    if clk_pin.value() == False:
                        a -= 1
                        a = round(a)
                        if a <= 0:
                            a = 0
                        display.clear()
                        center_text(int((display.height - unispace.height - 2) / 2),
                                    str(a), unispace, color565(0, 255, 0))
                        sleep(0.01)
                    else:
                        a += 1
                        a = round(a)
                        if a >= 99:
                            a = 99
                        display.clear()
                        center_text(int((display.height - unispace.height - 2) / 2),
                                    str(a), unispace, color565(0, 255, 0))
                        sleep(0.01)
                previous_value = dt_pin.value()
            if sw_pin.value() == False and not button_down:
                button_down = True
                a = round(a)
                if setid == 1:
                    config['mixer']['mixerwork'] = a
                    box[2] = config['mixer']['mixerwork']
                elif setid == 2:
                    config['mixer']['mixerwait'] = a
                    box[3] = config['mixer']['mixerwait']
                write_config()
                break
            sleep(0.01)

            if sw_pin.value() and button_down:
                button_down = False
            sleep(0.01)
        return a

    def show_menu(menu, box):
        """ Shows the menu on the screen"""
        # bring in the global variables
        global line, highlight, shift, list_length
        # menu variables
        item = 1
        boxitem = 2
        line = 1
        line_height = 20
        # display.fill_rectangle(0, 0, width , height, color565(128, 0, 255)) #background color
        # Shift the list of files so that it shows on the display
        list_length = len(menu)
        short_list = menu[shift:shift + total_lines]
        box_list_length = len(box)
        sort_box_list = box[shift:shift + total_lines]
        display.clear()
        for item, boxitem in zip(short_list, sort_box_list):
            if highlight == line:
                display.draw_text(
                    0,
                    (line - 1) * line_height + 5,
                    '>',
                    arcadepix,
                    color565(
                        255,
                        255,
                        255))  # menu item pointer
                if item == "AKTIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            0,
                            255,
                            0))  # menu item text
                elif item == "PASIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            0,
                            0))  # menu item text
                else:
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            255,
                            255))  # menu item text
                display.draw_text(
                    110,
                    (line - 1) * line_height + 5,
                    str(boxitem),
                    arcadepix,
                    color565(
                        0,
                        255,
                        0))  # menu item's values
            else:
                if item == "AKTIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            0,
                            255,
                            0))  # menu item text
                elif item == "PASIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            0,
                            0))  # menu item text
                else:
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            255,
                            255))  # menu item text
                # display.draw_text(10, (line-1)*line_height +5, item ,
                # arcadepix, color565(255, 255, 255)) #rest of menu items
                display.draw_text(
                    110,
                    (line - 1) * line_height + 5,
                    str(boxitem),
                    arcadepix,
                    color565(
                        0,
                        255,
                        0))  # rest of menu items's values
            line += 1

    def launch(filename):
        if filename == '< GERI':
            mainmenureturner()
        elif filename == file_list[1]:
            if config['mixer']['mixercond'] == "AKTIF":
                config['mixer']['mixercond'] = "PASIF"
                mixer_pin.value(0)
            elif config['mixer']['mixercond'] == "PASIF":
                config['mixer']['mixercond'] = "AKTIF"
                mixer_pin.value(1)
            write_config()
            file_list[1] = config['mixer']['mixercond']

        elif filename == 'CALISMA DK':
            setid = 1
            set_temp(config['mixer']['mixerwork'], setid)
        elif filename == 'BEKLEME DK':
            setid = 2
            set_temp(config['mixer']['mixerwait'], setid)

    show_menu(file_list, box)

    previous_time = time.ticks_ms()
    screen_timeout_in = time.ticks_ms()
    while True:
        try:
            gc.collect()
            blynkrun()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time  # Geçen süreyi kontrol et
            screen_timeout = current_time - screen_timeout_in  # Geçen süreyi kontrol et
            if elapsed_time >= 1000:  # 1 saniye geçti
                if network.WLAN(network.STA_IF).isconnected():
                    try:
                        blynk.virtual_write(4, config['mixer']['mixercond'])
                        blynk.virtual_write(6, config['mixer']['mixerwork'])
                        blynk.virtual_write(7, config['mixer']['mixerwait'])
                    except Exception as e:
                        print("blynk.wirtual_write(): ", e)
                previous_time = current_time  # Geçen zamanı sıfırla
            # Check for encoder rotated
            if previous_value != dt_pin.value():
                screen_timeout_in = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        if highlight > 1:
                            highlight -= 1
                        else:
                            if shift > 0:
                                shift -= 1
                    # Turned Right
                    else:
                        if highlight < total_lines:
                            highlight += 1
                        else:
                            if shift + total_lines < list_length:
                                shift += 1
                    show_menu(file_list, box)
                previous_value = dt_pin.value()

            if sw_pin.value() == False and not button_down:
                screen_timeout_in = current_time
                button_down = True

                launch(file_list[(highlight - 1) + shift])
                show_menu(file_list, box)
            sleep(0.01)

            if sw_pin.value() and button_down:
                button_down = False
            sleep(0.01)
            if screen_timeout >= 30000:  # 1 saniye geçti
                screen_timeout_in = current_time  # Geçen zamanı sıfırla
                home_returner()
        except Exception as e:
            print("while(): ", e)


"""--------------------------------------------------------------------------------"""
"""---------------------------------MIXER END--------------------------------------"""
"""--------------------------------------------------------------------------------"""

"""--------------------------------------------------------------------------------"""
"""----------------------------------COOLER ---------------------------------------"""
"""--------------------------------------------------------------------------------"""


def cooler_menu():
    global button_down, temp_treshould_state, blynk, previous_value, highlight, shift
    box = [
        '',
        '',
        config['cooler']['tempset'],
        config['cooler']['tempmax'],
        config['cooler']['tempmin'],
        config['cooler']['temptolerance']]
    file_list = [
        '< GERI',
        config['cooler']['coolercond'],
        'SABIT',
        'UYARI MAX',
        'UYARI MIN',
        'TOLERANS']
    if len(file_list) >= 6:
        total_lines = 6
    else:
        total_lines = len(file_list)

    def set_temp(a, setid):
        display.clear()
        global previous_value, button_down
        center_text(int((display.height - unispace.height - 2) / 2),
                    str(a), unispace, color565(0, 255, 0))
        while True:
            if previous_value != dt_pin.value():
                if dt_pin.value() == False:
                    if clk_pin.value() == False:
                        a -= 0.1
                        a = round(a, 1)
                        if a <= 0:
                            a = 0
                        display.clear()
                        center_text(int((display.height - unispace.height - 2) / 2),
                                    str(a), unispace, color565(0, 255, 0))
                        sleep(0.01)
                    else:
                        a += 0.1
                        a = round(a, 1)
                        if a >= 24:
                            a = 24
                        display.clear()
                        center_text(int((display.height - unispace.height - 2) / 2),
                                    str(a), unispace, color565(0, 255, 0))
                        sleep(0.01)
                previous_value = dt_pin.value()
            if sw_pin.value() == False and not button_down:
                button_down = True
                a = round(a, 1)
                if setid == 0:
                    config['cooler']['tempset'] = a
                    box[2] = config['cooler']['tempset']
                elif setid == 1:
                    config['cooler']['tempmax'] = a
                    box[3] = config['cooler']['tempmax']
                elif setid == 2:
                    config['cooler']['tempmin'] = a
                    box[4] = config['cooler']['tempmin']
                elif setid == 3:
                    config['cooler']['temptolerance'] = a
                    box[5] = config['cooler']['temptolerance']
                write_config()
                break
            sleep(0.01)

            if sw_pin.value() and button_down:
                button_down = False
            sleep(0.01)
        return a

    def show_menu(menu, box):
        """ Shows the menu on the screen"""
        # bring in the global variables
        global line, highlight, shift, list_length
        item = 1
        boxitem = 1
        line = 1
        line_height = 20
        list_length = len(menu)
        short_list = menu[shift:shift + total_lines]
        box_list_length = len(box)
        sort_box_list = box[shift:shift + total_lines]
        display.clear()
        for item, boxitem in zip(short_list, sort_box_list):
            if highlight == line:
                # display.fill_rectangle(0,(line-1)*line_height,
                # width,line_height,color565(46, 56, 64)) #highlighted area for
                # each menu item
                display.draw_text(
                    0,
                    (line - 1) * line_height + 5,
                    '>',
                    arcadepix,
                    color565(
                        255,
                        255,
                        255))  # menu item pointer
                if item == "AKTIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            0,
                            255,
                            0))  # menu item text
                elif item == "PASIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            0,
                            0))  # menu item text
                else:
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            255,
                            255))  # menu item text
                display.draw_text(
                    98,
                    (line - 1) * line_height + 5,
                    str(boxitem),
                    arcadepix,
                    color565(
                        255,
                        255,
                        255))  # menu item's values
            else:
                if item == "AKTIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            0,
                            255,
                            0))  # menu item text
                elif item == "PASIF":
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            0,
                            0))  # menu item text
                else:
                    display.draw_text(
                        10,
                        (line - 1) * line_height + 5,
                        item,
                        arcadepix,
                        color565(
                            255,
                            255,
                            255))  # menu item text
                display.draw_text(
                    98,
                    (line - 1) * line_height + 5,
                    str(boxitem),
                    arcadepix,
                    color565(
                        255,
                        255,
                        255))  # rest of menu items's values
            line += 1

    def launch(filename):
        if filename == '< GERI':
            mainmenureturner()
        elif filename == file_list[1]:
            if config['cooler']['coolercond'] == "AKTIF":
                config['cooler']['coolercond'] = "PASIF"
                cooler_pin.value(0)
            elif config['cooler']['coolercond'] == "PASIF":
                config['cooler']['coolercond'] = "AKTIF"
                cooler_pin.value(1)
            write_config()
            file_list[1] = config['cooler']['coolercond']
        elif filename == 'SABIT':
            setid = 0
            set_temp(config['cooler']['tempset'], setid)
        elif filename == 'UYARI MAX':
            setid = 1
            set_temp(config['cooler']['tempmax'], setid)
        elif filename == 'UYARI MIN':
            setid = 2
            set_temp(config['cooler']['tempmin'], setid)
        elif filename == 'TOLERANS':
            setid = 3
            set_temp(config['cooler']['temptolerance'], setid)

    show_menu(file_list, box)
    previous_time = time.ticks_ms()
    screen_timeout_in = time.ticks_ms()

    while True:

        try:
            gc.collect()
            blynkrun()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time  # Geçen süreyi kontrol et
            screen_timeout = current_time - screen_timeout_in  # Geçen süreyi kontrol et
            if elapsed_time >= 1000:  # 1 saniye geçti
                try:
                    blynk.virtual_write(0, config['cooler']['tempset'])
                    blynk.virtual_write(2, config['cooler']['tempmax'])
                    blynk.virtual_write(3, config['cooler']['tempmin'])
                    blynk.virtual_write(8, config['cooler']['temptolerance'])
                except BaseException:
                    pass
                previous_time = current_time  # Geçen zamanı sıfırla
            # Check for encoder rotated
            if previous_value != dt_pin.value():
                screen_timeout_in = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        if highlight > 1:
                            highlight -= 1
                        else:
                            if shift > 0:
                                shift -= 1
                    # Turned Right
                    else:
                        if highlight < total_lines:
                            highlight += 1
                        else:
                            if shift + total_lines < list_length:
                                shift += 1
                    show_menu(file_list, box)
                previous_value = dt_pin.value()
            time.sleep_ms(5)

            if sw_pin.value() == False and not button_down:
                screen_timeout_in = current_time
                button_down = True

                launch(file_list[(highlight - 1) + shift])
                show_menu(file_list, box)
            time.sleep_ms(5)

            if sw_pin.value() and button_down:
                button_down = False
            time.sleep_ms(5)
            if screen_timeout >= 30000:  # 1 saniye geçti
                screen_timeout_in = current_time  # Geçen zamanı sıfırla
                home_returner()
        except OSError:
            time.sleep_ms(1000)
            machine.reset()


"""--------------------------------------------------------------------------------"""
"""--------------------------------COOLER END--------------------------------------"""
"""--------------------------------------------------------------------------------"""

"""--------------------------------------------------------------------------------"""
"""---------------------------------MAIN MENU -------------------------------------"""
"""--------------------------------------------------------------------------------"""


def mainmenu():
    menu = [
        ('GERI', 'main()'),
        ('SOGUTUCU', 'cooler_menu()'),
        ('KARISTIRICI', 'mixer_menu()'),
        ('AGIRLIK', 'weight_menu()'),
        ('AYARLAR', 'settings_menu()'),
        ('HAKKINDA', 'about_page()')
    ]

    width = 128
    line = 1
    highlight = 1
    shift = 0
    list_length = 0
    if len(menu) >= 6:
        total_lines = 6
    else:
        total_lines = len(menu)

    previous_value = True
    button_down = False

    def show_menu(menu):
        """ Shows the menu on the screen"""
        # bring in the global variables
        global line, list_length
        # menu variables
        item = 1
        line = 1
        line_height = 20
        list_length = len(menu)
        short_list = menu[shift:shift + total_lines]
        display.clear()
        for item, ifilename in short_list:
            if highlight == line:
                display.draw_text(
                    0,
                    (line - 1) * line_height + 5,
                    '>',
                    arcadepix,
                    color565(
                        255,
                        255,
                        255))
                display.draw_text(
                    10,
                    (line - 1) * line_height + 5,
                    item,
                    arcadepix,
                    color565(
                        255,
                        255,
                        255))
            else:
                display.draw_text(
                    10,
                    (line - 1) * line_height + 5,
                    item,
                    arcadepix,
                    color565(
                        255,
                        255,
                        255))
            line += 1
        return ifilename

    def launch(filename):
        eval(filename[1])

    show_menu(menu)
    previous_time = time.ticks_ms()

    while True:
        try:
            gc.collect()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time
            # Check for encoder rotated
            if previous_value != dt_pin.value():
                previous_time = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        if highlight > 1:
                            highlight -= 1
                        else:
                            if shift > 0:
                                shift -= 1
                    # Turned Right
                    else:
                        if highlight < total_lines:
                            highlight += 1
                        else:
                            if shift + total_lines < list_length:
                                shift += 1
                    show_menu(menu)
                previous_value = dt_pin.value()

            if sw_pin.value() == False and not button_down:
                previous_time = current_time
                button_down = True
                launch(menu[(highlight - 1) + shift])

            if sw_pin.value() and button_down:
                button_down = False
            time.sleep_ms(10)
            if elapsed_time >= 30000:  # 1 saniye geçti
                previous_time = current_time  # Geçen zamanı sıfırla
                home_returner()
        except Exception as e:
            print(e)


"""--------------------------------------------------------------------------------"""
"""------------------------------MAIN MENU END-------------------------------------"""
"""--------------------------------------------------------------------------------"""


def main():
    home()
    global button_down, steinhart, temp_treshould_state, blynk
    previous_time = time.ticks_ms()
    msg_prev_time = time.ticks_ms()

    while True:
        try:
            blynkrun()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time
            msg_runout_time = current_time - msg_prev_time
            # Geçen süreyi kontrol et
            if elapsed_time >= 1000:  # 1 saniye geçti
                gc.collect()
                if network.WLAN(network.STA_IF).isconnected():
                    try:
                        blynk.sync_virtual(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
                    except Exception as e:
                        print("blynk sync wirtual: ", e)
                        draw_message("sync. hatasi")
                    display_time()
                temperature()
                weight()
                previous_time = current_time  # Geçen zamanı sıfırla
            if msg_runout_time >= 30000:
                display.fill_rectangle(0, 115, 128, 13, color565(0, 0, 0))
                text = " "
                msg_prev_time = current_time
                if machine.RTC().datetime()[0] < 2023 and network.WLAN(
                        network.STA_IF).isconnected():
                    set_time()

            if sw_pin.value() == False and not button_down:
                button_down = True
                rfidread()
            if sw_pin.value() and button_down:
                button_down = False

            if steinhart >= config['cooler']['tempset'] + \
                    config['cooler']['temptolerance'] and config['cooler']['coolercond'] == 'AKTIF' and config['mixer']['mixercond'] == 'AKTIF':
                cooler_pin.value(1)
                mixer_pin.value(1)
                if not temp_treshould_state:
                    home()
                temp_treshould_state = True
            if steinhart < config['cooler']['tempset'] and config['mixer']['mixercond'] == 'AKTIF':
                temp_treshould_state == False
                mixer_toogle(current_time)
            if steinhart >= config['cooler']['tempset'] and temp_treshould_state == False and config['mixer']['mixercond'] == 'AKTIF':
                mixer_toogle(current_time)
            sleep(0.01)
        except Exception as e:
            print("main loop error: ", e)
            draw_message("HATA [M]")


if __name__ == "__main__":
    main()
