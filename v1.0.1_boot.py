import time,json,gc,os
from ssd1351 import Display, color565
from machine import Pin, SPI, ADC
from xglcd_font import XglcdFont
import wifimgr
import micropython_ota
machine.freq(250000000)

wifimgr.get_connection('first_start')
ota_host = 'https://raw.githubusercontent.com/omrfrkmll'
project_name = 'milk-tank-control/main'
filenames = ['boot.py', 'main.py']
micropython_ota.ota_update(ota_host, project_name, filenames, use_version_prefix=True , hard_reset_device=True, soft_reset_device=False, timeout=5)
spi = SPI(1, baudrate=48000000, sck=Pin(10), mosi=Pin(11))
display = Display(spi, dc=Pin(12), cs=Pin(13), rst=Pin(14))

arcadepix = XglcdFont('fonts/ArcadePix9x11.c', 9, 11)
unispace = XglcdFont('fonts/Unispace12x24.c', 12, 24)
with open('config.json','r') as f:#read the json file
    config = json.load(f)
def unimport_all():
    mod_name =[
        "time",
        "sleep",
        "ssd1351",
        "color565",
        "machine",
        "Pin",
        "SPI",
        "ADC",
        "xglcd_font",
        "MFRC522",
        "BlynkLib",
        "network",
        "json",
        "socket",
        "struct",
        "unpack",
        "math",
        "gc",
        "wifimgr",
        "hx711_pio",
    ]
    for module in mod_name:
        print("unimporting '%s' free: " % module ,gc.mem_free(),"allocated: ",gc.mem_alloc())
        del module
        gc.collect()
        
def write_config():
    with open('config.json','w') as f:
        json.dump(config, f)
def center_text(y,text,font,color):
    global center,w
    w=font.measure_text(text)  # Measure length of text in pixels
    center = int(display.width  / 2 - w / 2)  # Calculate position for centered text
    display.draw_text(center, y, text, font, color)
    return center
def aboutpage():
    center_text(30, "MEKAR", unispace, color565(255, 0, 0))
    center_text(70, "mekarteknoloji.com", arcadepix, color565(255, 255, 255))
    center_text(100, config['version'], arcadepix, color565(255, 255, 255))
    time.sleep(1)
    try:
        print("main.py---->>")
        unimport_all()
        exec(open('main.py').read())
    except Exception as e:
        print(e)
        center_text(70, "cihazi yeninden", arcadepix, color565(255, 255, 255))
        center_text(100, "baslatin", arcadepix, color565(255, 255, 255))
def read_uids():
    with open("card_lib.dat") as f:
        lines = f.readlines()
    uids = {}
    for line in lines:
        uids = line.strip("\n")
    return uids
def write_uids(uids):
    with open("card_lib.dat", "a") as f:
        f.write("%s\n" % (uids))
def card_generator():
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
    reader = MFRC522(spi_id=0,sck=2,miso=4,mosi=3,cs=1,rst=0)
    print("")
    print("Please place card on reader")
    print("")
    PreviousCard = [0]
    try:
        while True:
            reader.init()
            (stat, tag_type) = reader.request(reader.REQIDL)
            #print('request stat:',stat,' tag_type:',tag_type)
            if stat == reader.OK:
                (stat, uid) = reader.SelectTagSN()
                if stat == reader.OK:
                    print(uid)
                    print("Card detected %s" % uidToString(uid))
                    print("Card detected {}  uid={}".format(hex(int.from_bytes(bytes(uid),"little",False)).upper(),reader.tohexstring(uid)))
                    try:
                        uids = read_uids()
                        print(uids)
                    except Exception as e:
                        uids = {}
                        print(e)
                    if reader.tohexstring(uid) in uids:
                        print("card already registered", reader.tohexstring(uid))
                        center_text(50, "KART", arcadepix, color565(0, 255, 0))
                        center_text(64, "KAYITLI", arcadepix, color565(180, 0, 0))
                        config['setup']=True
                        write_config()
                        time.sleep(1)
                    else:
                        write_uids(reader.tohexstring(uid))
                        center_text(50, "KART", arcadepix, color565(0, 255, 0))
                        center_text(64, "KAYDEDILDI", arcadepix, color565(0, 255, 0))
                        config['setup']=True
                        write_config()
                        time.sleep(1)
                    print("Done")
                    PreviousCard = uid
                    break
                else:
                    pass
            else:
                PreviousCard=[0]
            utime.sleep_ms(50)                

    except KeyboardInterrupt:
        pass

if config['setup']!=True or not 'card_lib.dat' in os.listdir():
    display.clear()
    center_text(50, "ILK", arcadepix, color565(0, 255, 0))
    center_text(64, "KURULUM", arcadepix, color565(0, 255, 0))
    time.sleep(2)
    center_text(50, "KART", arcadepix, color565(0, 255, 0))
    center_text(64, "TANIMLAMA", arcadepix, color565(0, 255, 0))
    time.sleep(2)
    card_generator()

aboutpage()
