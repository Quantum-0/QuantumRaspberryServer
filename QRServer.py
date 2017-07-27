from flask import Flask, jsonify, abort, render_template, request, redirect, url_for, g, send_from_directory
import subprocess
import os
import psutil
import socket
import signal
import RPi.GPIO as GPIO
import csv
import Adafruit_DHT
import threading
from collections import deque
import datetime
import telebot
import my_token

app = Flask(__name__)

GPIO_LIGHT = 18
GPIO_MOVEMENT = 17

def after_this_request(func):
    if not hasattr(g, 'call_after_request'):
        g.call_after_request = []
    g.call_after_request.append(func)
    return func

@app.after_request
def per_request_callbacks(response):
    for func in getattr(g, 'call_after_request', ()):
        response = func(response)
    return response

# ===================================== WEB INTERFACE =====================================

# Корень
@app.route('/test')
def index_test():
	return 'Привет, я малинка'

# Favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')	

# Index
@app.route('/')
def index():
	return redirect('/panel/status')
	
# Control Panel
@app.route('/panel/<page>')
def index_page(page):
	return render_template('index.html', page=page)
	
# Panel content
@app.route('/panel_get_content/<page>')
def get_content_for_control_panel(page):
	return render_template(page + '.html')

# ======================================== RESTful API ========================================

# Корень
@app.route('/api')
def index_api():
	return 'Quantum Raspberry Server - API v0.3'
	
# =================== Управление ботами ==================

bots = [
	{
		'id': 0,
		'name': 'Quantum Bot',
		'path': '/home/pi/Autorun/Run/RaspberryUSBAndTelegram.exe',
		'running': False,
		'pid': -1,
		'autorun': False
	}
	,
	{
		'id': 1,
		'name': 'Shurya Chat Bot',
		'path': '/home/pi/Autorun/Run/ShuryaChatBot.exe',
		'running': False,
		'pid': -1,
		'autorun': True
	}
	,
	{
		'id': 2,
		'name': 'Reminder Bot',
		'path': '/home/pi/Autorun/Run/ReminderBot.exe',
		'running': False,
		'pid': -1,
		'autorun': False
	}
]

@app.route('/api/bots', methods=['GET'])
def api_bots_list():
	return jsonify({'bots': bots})

@app.route('/api/bots/<int:bot_id>', methods=['GET'])
def api_bot(bot_id):
	bot = list(filter(lambda t: t['id'] == bot_id, bots))
	if len(bot)==0:
		abort(404)
	return jsonify({'bot': bot[0]})

@app.route('/api/bots', methods=['POST'])
def api_add_bot():
	if not request.json or not 'path' in request.json:
		abort(400)
	bot = {
		'id': bots[-1]['id'] + 1,
		'name': request.json.get('name', ""),
		'autorun': request.json.get('autorun', False),
		'path': request.json['path'],
		'pid': -1,
		'running': False
	}
	bots.append(bot)
	SaveBotsToFile()
	return jsonify({'bot': bot}), 201

@app.route('/api/bots/<int:bot_id>', methods=['DELETE'])
def delete_bot(bot_id):
	bot = list(filter(lambda t: t['id'] == bot_id, bots))
	if len(bot) == 0:
		abort(404)
	bots.remove(bot[0])
	SaveBotsToFile()
	return jsonify({'result': True})

@app.route('/api/bots/run/<int:bot_id>', methods=['GET'])
def run_bot(bot_id):
	bot = list(filter(lambda t: t['id'] == bot_id, bots))
	if len(bot) == 0:
		abort(404)
	
	if bot[0]['running']==True:
		return jsonify({'result': False})
	else:
		bot[0]['running'] = True
		_run_bot(bot[0])
		return jsonify({'result': True})

def _run_bot(bot):
	with open(bot['path'] + "stdout.txt","wb") as out, open(bot['path'] + "stderr.txt","wb") as err:
			subproc = subprocess.Popen(["mono", bot['path']], stdout=out, stderr=err)
			bot['pid'] = subproc.pid

@app.route('/api/bots/stop/<int:bot_id>', methods=['GET'])
def stop_bot(bot_id):
	bot = list(filter(lambda t: t['id'] == bot_id, bots))
	if len(bot) == 0:
		abort(404)
	
	if bot[0]['running']==False:
		return jsonify({'result': False})
	else:
		os.system('sudo kill ' + str(bot[0]['pid']))
		#os.kill(bot[0]['pid'], signal.SIGTERM)
		bot[0]['running']=False
		return jsonify({'result': True})

# =================== Матрица в DEV/TTY1 ==================

# Запуск "матрицы" на подключённом экране
@app.route('/api/matrix/<i>')
def matrix(i):
	if i=='1':
		os.system('sudo cmatrix 1>/dev/tty1 &')
	elif i=='0':
		os.system('sudo killall cmatrix')
		os.system('sudo clear > /dev/tty1')
	else:
		abort(400)
	return jsonify({'result': True})

# =================== Выключение и перезагрузка ==================

# Выключение
@app.route('/api/shutdown')
def shutdown():
	@after_this_request
	def closescrypt(response):
		exit()
	GPIO.remove_event_detect(GPIO_MOVEMENT)
	GPIO.cleanup()
	os.system('sudo shutdown -h now &')
	return jsonify({'result': True}) #'Shutdowning Raspberry Pi..'

# Перезагрузка
@app.route('/api/reboot')
def reboot():
	@after_this_request
	def closescrypt(response):
		exit()
	GPIO.remove_event_detect(GPIO_MOVEMENT)
	GPIO.cleanup()
	os.system('sudo reboot &')
	return jsonify({'result': True}) #'Rebooting Raspberry Pi..'

# =========================== GPIO ===========================
	# GPIO.OUT = 0; GPIO.IN = 1
	# GPIO.PUD_OFF = 20; GPIO.PUD_DOWN = 21; GPIO.PUD_UP = 22

# GPIO Setup
@app.route('/api/gpio/<int:channel>', methods=['POST'])
def gpiosetup(channel):
	if not request.json or not 'Direction' in request.json or not 'Resistor' in request.json or not 'Value' in request.json:
		abort(400)
	
	dir = request.json['Direction']
	pull = request.json['Resistor']
	val = request.json['Value']
	
	if (dir == -1):
		abort(400)
		
	if (dir == GPIO.OUT):
		if (pull != GPIO.PUD_OFF and pull != -1):
			abort(400)
		
	if (pull == -1):
		GPIO.setup(channel, dir)
	else:
		GPIO.setup(channel, dir, pull)
		
	if (dir == GPIO.OUT and val != -1):
		GPIO.output(channel, val)
	
	opened_pins.add(channel)
	result = {
		'Channel': channel,
		'Direction': dir,
		'Resistor': pull,
		'Value': GPIO.input(channel)
	}
	return jsonify({'GPIO': result})
	
# GPIO Output
@app.route('/api/gpio/<int:channel>/<int:value>', methods=['GET'])
def gpiooutput(channel, value):
	if (value != 0 and value != 1):
		abort(400)
	
	try:
		GPIO.output(channel, value)
		return jsonify({'result': True})
	except Exception as e:
		return jsonify({'result': False, 'exception': str(e)})

# GPIO Input
@app.route('/api/gpio/<int:channel>', methods=['GET'])
def gpioinput(channel):

	try:
		value = GPIO.input(channel)
		return jsonify({'result': True, 'value': value})
	except Exception as e:
		return jsonify({'result': False, 'exception': str(e)})
		
# GPIO Quick Setup
@app.route('/api/gpio/setup/<int:channel>/<int:dir>', methods=['GET'])
def gpioqsetup(channel, dir):

	try:
		GPIO.setup(channel, dir)
		opened_pins.add(channel)
		return jsonify({'result': True})
	except Exception as e:
		return jsonify({'result': False, 'exception': str(e)})

# =========================== Stats ===========================

opened_pins = set()
dhtdata = {'temp': 0, 'hum': 0}

@app.route('/api/stats', methods=['GET'])
def stats():
	vm = psutil.virtual_memory()	
	
	cpuusg = str(psutil.cpu_percent(interval=1))
	cputemp = getCPUtemperature()
	
	memusd = vm.percent
	memtotal = vm.total
	
	cpu = {
		'usage': cpuusg,
		'temperature': cputemp
	}
	mem = {
		'used': memusd,
		'total': memtotal
	}
	gpio = {pin: GPIO.input(pin) for pin in opened_pins}
	stat = {
		'external': dhtdata,
		'memory': mem,
		'cpu': cpu,
		'gpio': gpio,
	}
	
	return jsonify({'stats': stat})
	
#=========================== High level control ======================

light_settings = {
	'time': False,
	'time_on': datetime.time(hour=22, minute=30, second=0),
	'time_off': datetime.time(hour=2, minute=0, second=0),
	'movement': True,
	'movement_delay': datetime.timedelta(hours=0, minutes=5),
	'movement_from': datetime.time(hour=21, minute=0, second=0),
	'movement_to': datetime.time(hour=3, minute=30, second=0),
	'movement_turn_off_in': None,
	'value': 0 #0 - auto, -1 - off, 1 - on
}
movements = deque()

def halfminutetimer():
	if (light_settings['time']):
		is_between = time_between(light_settings['time_on'], light_settings['time_off'], datetime.datetime.now().time())
		is_light = GPIO.input(GPIO_LIGHT) == GPIO.HIGH
		if (not is_light and is_between):
			GPIO.output(GPIO_LIGHT, True)
		elif (is_light and not is_between):
			GPIO.output(GPIO_LIGHT, False)
		
	if (light_settings['movement_turn_off_in'] != None):
		if datetime.datetime.now() > light_settings['movement_turn_off_in']:
			light_settings['movement_turn_off_in'] = None
			GPIO.output(GPIO_LIGHT, False)
			
	threading.Timer(30.0, halfminutetimer).start()

@app.route('/api/autolight', methods=['GET'])
def get_autolight():
	return jsonify({'settings': light_settings})

@app.route('/api/light', methods=['GET'])
def get_light():
	try:
		value = GPIO.input(GPIO_LIGHT)
		return jsonify({'result': True, 'value': value})
	except Exception as e:
		return jsonify({'result': False, 'exception': str(e)})

@app.route('/api/light/<int:value>', methods=['GET'])
def set_light(value):
	try:
		GPIO.output(GPIO_LIGHT, value)
		return jsonify({'result': True})
	except Exception as e:
		return jsonify({'result': False, 'exception': str(e)})

@app.route('/api/movement/now', methods=['GET'])
def get_now_movement():
	try:
		value = GPIO.input(GPIO_MOVEMENT)
		return jsonify({'result': True, 'value': value})
	except Exception as e:
		return jsonify({'result': False, 'exception': str(e)})
		
@app.route('/api/movement', methods=['GET'])
def get_movements():
	return jsonify({'movements': list(movements)})

def init_high_level_control():
	GPIO.setup(GPIO_LIGHT, GPIO.OUT)
	GPIO.setup(GPIO_MOVEMENT, GPIO.IN)
	GPIO.add_event_detect(GPIO_MOVEMENT, GPIO.BOTH, bouncetime=350, callback=movement_changed_callback) 

# у меня не получилось сделать глобальную переменную( поэтому будет такой костыль
movementstart = {'value': None}
def movement_changed_callback(channel):
	if (GPIO.input(channel) == GPIO.HIGH):
		movement_rising_callback(channel)
	else:
		movement_falling_callback(channel)
def movement_rising_callback(channel):
	movementstart['value'] = datetime.datetime.now()
	if (light_settings['movement'] and time_between(light_settings['movement_from'], light_settings['movement_to'], datetime.datetime.now().time())):
		GPIO.output(GPIO_LIGHT, GPIO.HIGH)	
def movement_falling_callback(channel):
	movements.append({'start': movementstart['value'].isoformat(' '), 'end': datetime.datetime.now().isoformat(' ')})
	if (len(movements) > 64):
		movements.popleft()
	if (light_settings['movement'] and time_between(light_settings['movement_from'], light_settings['movement_to'], datetime.datetime.now().time())):
		light_settings['movement_turn_off_in'] = datetime.datetime.now() + light_settings['movement_delay']
		
def time_between(From, To, current):
	if (From < To):
		return current > From and current < To
	else:
		return current > From or current < To

# ====================== Light control via Telebot =====================

bot = telebot.TeleBot(my_token.TELEBOT_TOKEN) 

@bot.message_handler(commands=['light_on']) #content_types=["text"]
def bot_light_on(message):
	GPIO.output(GPIO_LIGHT, 1)
	bot.send_message(message.chat.id, 'Свет включён')

@bot.message_handler(commands=['light_off'])
def bot_light_on(message):
	GPIO.output(GPIO_LIGHT, 0)
	bot.send_message(message.chat.id, 'Свет выключен')

	
	
	
	
# ====================== Ниже не доделано ============================


# Запуск Spigot-сервера
@app.route('/api/minecraft/spigot')
def spigot():
	os.system('sudo java -Xms384M -Xmx740M -jar /home/minecraft/spigot-1.11.2.jar nogui')
	return 'Done'

# Запуск CraftBukkit-сервера
@app.route('/api/minecraft/bukkit')
def bukkit():
	os.system('sudo java -Xms384M -Xmx740M -jar /home/minecraft/craftbukkit-1.11.2.jar nogui')
	return 'Done'

# Запуск Vanila-сервера с Forge
@app.route('/api/minecraft/forge')
def forge():
	os.system('sudo java -Xms384M -Xmx740M -jar /home/minecraft/forge-1.11.2-13.20.0.2228-universal.jar nogui')
	return 'Done'

# Перезапуск ботов
@app.route('/api/restart_bots')
def restartbots():
	os.system('sudo killall mono')
	os.system('/home/pi/Autorun/Autorun.py')
	return 'Done'

# Перезапуск ботов
@app.route('/api/stop_bots')
def stopbots():
	os.system('sudo killall mono')
	return 'Done'

# Статистика RAM
@app.route('/api/memory/<val>')
def meminfo(val):
	p = psutil.virtual_memory()
	if val=='free':
		return str(100-p.percent)
	elif val=='total':
		return str(p.total)
	elif val=='used':
		return str(p.percent)
	else:
		return '?'

# Текущая температура процессора
@app.route('/api/cpu_temp')
def cputemp():
	return getCPUtemperature()

# Статистика использования процессора
@app.route('/api/cpu')
def cpuusage():
	return str(psutil.cpu_percent(interval=1))

# Запуск сервиса motion
@app.route('/api/motion/start')
def startmotion():
	os.system('sudo service motion start &')
	return redirect(request.url[:request.url.index('5000')] + '8081/', code=302)

# Остановка сервиса motion
@app.route('/api/motion/stop')
def stopmotion():
	os.system('sudo service motion stop')
	return jsonify({'result': True})

# Проверка текущего состояния сервиса motion
@app.route('/api/motion')
def statusmotion():
	output = subprocess.check_output(["service", "sshd", "status"], stderr=subprocess.STDOUT)
	if 'inactive (dead)' in output:
		return 'False'
	else:
		return 'True'

# Запуск стриминга на Picarto
@app.route('/api/stream/picarto')
def picarto_stream():
	os.system('ffmpeg -f v4l2 -framerate 20 -video_size 640x480 -i /dev/video0 -c:v libx264 -b:v 500k -maxrate 500k -bufsize 500k -an -f flv rtmp://live.us.picarto.tv/golive/...')
	return 'Stream started'

# Запуск стриминга на YouTube
@app.route('/api/stream/youtube')
def youtube_stream():
	os.system('ffmpeg -ar 44100 -ac 2 -acodec pcm_s16le -f s16le -ac 2 -i /dev/zero -f v4l2 -c:a aac -framerate 5 -video_size 640x480 -i /dev/video0 -c:v libx264 -b:v 200k -maxrate 200k -bufsize 200k -vcodec h264 -g 60 -strict experimental -f flv rtmp://a.rtmp.youtube.com/live2/...')
	return 'Stream started'

# update системы
@app.route('/api/update')
def update():
	os.system('sudo killall cmatrix')
	os.system('sudo apt-get update & > /dev/tty1')
	return 'Updating..'

# upgrade системы
@app.route('/api/upgrade')
def upgrate():
	os.system('sudo killall cmatrix')
	os.system('sudo apt-get upgrade & > /dev/tty1')
	return 'Upgrading..'

def getCPUtemperature():
	res = os.popen('vcgencmd measure_temp').readline()
	return(res.replace("temp=","").replace("'C\n",""))
	
def LoadBotsFromFile():
	if (os.path.isfile("bots_data.txt")):
		with open("bots_data.txt", "r") as f:
			reader = csv.reader(f, delimiter="|")
			bots = list(reader)
	pass

def SaveBotsToFile():
	with open("bots_data.txt", "w") as f:
		writer = csv.writer(f, delimiter="|")
		writer.writerows(lines)
	pass


def updatedht():
	humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, 4)
	dhtdata['hum'] = humidity
	dhtdata['temp'] = temperature
	threading.Timer(15.0, updatedht).start()

	
# ====================================== Main ========================================

if __name__ == '__main__':
	LoadBotsFromFile()
	
	for b in bots:
		if (b['running']):
			b['running'] = False;
		if (b['autorun']):
			b['running'] = True
			_run_bot(b)
			
	GPIO.setmode(GPIO.BCM)
	init_high_level_control()
	updatedht()
	halfminutetimer()
	bot.polling(none_stop=True)
	app.run(debug=True, host='0.0.0.0', port = 5000) #port for testing