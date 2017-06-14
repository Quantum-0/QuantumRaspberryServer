from flask import Flask, render_template, request, redirect
import os
import psutil
import socket

app = Flask(__name__)

# Корень
@app.route('/')
def index():
	return 'Привет, я малинка'

# Запуск "матрицы" на подключённом экране
@app.route('/matrix/<i>')
def matrix(i):
	if i=='1': # Если 1
		os.system('sudo cmatrix 1>/dev/tty1 &')
	elif i=='0': # Если же 0
		os.system('sudo killall cmatrix')
		os.system('sudo clear > /dev/tty1')
	else:
		return 'Error'
	return 'Done'

# Выключение
@app.route('/shutdown')
def shutdown():
	os.system('sudo shutdown -h now &')
	return 'Shutdowning Raspberry Pi..'

# Перезагрузка
@app.route('/reboot')
def reboot():
	os.system('sudo reboot &')
	return 'Rebooting Raspberry Pi..'

# Запуск Spigot-сервера
@app.route('/minecraft/spigot')
def spigot():
	os.system('sudo java -Xms384M -Xmx740M -jar /home/minecraft/spigot-1.11.2.jar nogui')
	return 'Done'

# Запуск CraftBukkit-сервера
@app.route('/minecraft/bukkit')
def bukkit():
	os.system('sudo java -Xms384M -Xmx740M -jar /home/minecraft/craftbukkit-1.11.2.jar nogui')
	return 'Done'

# Запуск Vanila-сервера с Forge
@app.route('/minecraft/forge')
def forge():
	os.system('sudo java -Xms384M -Xmx740M -jar /home/minecraft/forge-1.11.2-13.20.0.2228-universal.jar nogui')
	return 'Done'

# Перезапуск ботов
@app.route('/restart_bots')
def restartbots():
	os.system('sudo killall mono')
	os.system('/home/pi/Autorun/Autorun.py')
	return 'Done'

# Статистика RAM
@app.route('/memory/<val>')
def freemem(val):
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
@app.route('/cpu_temp')
def cputemp():
	return getCPUtemperature()

# Статистика использования процессора
@app.route('/cpu')
def cpuusage():
	return str(psutil.cpu_percent(interval=1))

# Запуск сервиса motion
@app.route('/motion/start')
def startmotion():
	os.system('sudo service motion start &')
	return redirect(request.url[:request.url.index('5000')] + '8081/', code=302)

# Остановка сервиса motion
@app.route('/motion/stop')
def stopmotion():
	os.system('sudo service motion stop')
	return 'Stopped'

# Проверка текущего состояния сервиса motion
@app.route('/motion')
def statusmotion():
	#os.system('sudo service motion stop')
	return ''

# Запуск стриминга на Picarto
@app.route('/stream/picarto')
def picarto_stream():
	os.system('ffmpeg -f v4l2 -framerate 20 -video_size 640x480 -i /dev/video0 -c:v libx264 -b:v 500k -maxrate 500k -bufsize 500k -an -f flv rtmp://live.us.picarto.tv/golive/...')
	return 'Stream started'

# Запуск стриминга на YouTube
@app.route('/stream/youtube')
def youtube_stream():
	os.system('ffmpeg -ar 44100 -ac 2 -acodec pcm_s16le -f s16le -ac 2 -i /dev/zero -f v4l2 -c:a aac -framerate 5 -video_size 640x480 -i /dev/video0 -c:v libx264 -b:v 200k -maxrate 200k -bufsize 200k -vcodec h264 -g 60 -strict experimental -f flv rtmp://a.rtmp.youtube.com/live2/...')
	return 'Stream started'

# update системы
@app.route('/update')
def update():
	os.system('sudo killall cmatrix')
	os.system('sudo apt-get update & > /dev/tty1')
	return 'Updating..'

# upgrade системы
@app.route('/upgrade')
def upgrate():
	os.system('sudo killall cmatrix')
	os.system('sudo apt-get upgrade & > /dev/tty1')
	return 'Upgrading..'

def getCPUtemperature():
	res = os.popen('vcgencmd measure_temp').readline()
	return(res.replace("temp=","").replace("'C\n",""))







if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0', port = 5000)