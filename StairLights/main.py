from utime import time, sleep
from pixel import Pixel
import ujson as json
from vl53l1x import VL53L1X

# SYSTEM FUNCTIONS
def restart(params):
  global client, CLIENT_ID, CLIENT_NAME
  reason = params['reason']
  print("<< Restarting. [{}] >>".format(reason))
  msg = '{} [{}] restarting. Reason: {}'.format(CLIENT_NAME, CLIENT_ID, reason)
  client.publish(TOPIC_PUB, msg)
  sleep(2)
  machine.reset()
  
sys_funcs = {
  'restart' : restart,
}

# MQTT CONNECTION, CONSTANTS & VARIABLES
CLIENT_ID = ubinascii.hexlify(machine.unique_id())
CLIENT_NAME = 'StairsESP8266'
TOPIC_SUB = 'house/lights/stairs'
TOPIC_PUB = 'house/devices'

last_message = time()
message_interval = 10
counter = 1

def connect_and_subscribe(client_id, server, topic_sub):
  client = MQTTClient(client_id, server)
  client.set_callback(sub_cb)
  client.connect()
  client.subscribe(topic_sub)
  print('<< Connected to MQTT broker at {}; subscribed to topic "{}" >>'.format(server, topic_sub))
  return client

def sub_cb(topic, msg):
  print("Raw Msg: {}".format(msg)) #! For debugging only
  msg = json.loads(msg)
  target = msg['target']
  command = msg['command']
  params = msg['params']
  
  if target == 'system':
    global sys_funcs
    sys_funcs[command](params)
  
  elif target == 'lights':
    global lights
    print("command: {}\nparams: {}\ntype: {}".format(command, params, type(params)))
    lights.execute(command, params)

def check_in(client, client_name, counter, topic_pub):
  msg = '{} [{}] online. Count [{}]'.format(client_name, client.client_id, counter)
  client.publish(topic_pub, msg)
  print("<< Checked in >>")
  last_message = time()
  counter += 1
  return counter, last_message

try:
  client = connect_and_subscribe(CLIENT_ID, SERVER, TOPIC_SUB)
except OSError as e:
  restart(params={'reason' : e})

# INSTANTIATING THE PIXELS
PIN = 13
TOTAL_PIXELS = 120
STRIPS = 4
lights = Pixel(PIN, TOTAL_PIXELS, STRIPS)
# CHECKING THE LIGHT ARRAY
print("<< Checking light array >>")
lights.check_array()
print("<< Check complete >>")

# TOF FUNCTIONS
def tof_average(tof, samples=32):
  l = []
  [l.append(tof.read()) for i in range(samples)]
  avg = sum(l) / len(l)
  lo_error = avg - 20
  hi_error = avg + 20
  return lo_error, avg, hi_error

# INSTANTIATING THE TOF SENSOR
tof = VL53L1X()
base_reading = tof_average(tof)
print("<< TOF Base Reading: {} >>".format(base_reading))

# MAIN LOOP
while True:
  try:
    # CHECK MESSAGES
    client.check_msg()

    # PUBLISH MESSAGE IF APPROPRIATE
    if (time() - last_message) > (message_interval * counter):
      counter, last_message = check_in(client, CLIENT_NAME, counter, TOPIC_PUB)
    
    lo_error, distance, hi_error = tof_average(tof)
    #[ ]: Compare this to the distance of the lights
    # print("<< Lo: {} < Dist: {} < Hi: {} >>".format(lo_error, distance, hi_error))
    
  except OSError as e:
    restart(params={'reason' : e})