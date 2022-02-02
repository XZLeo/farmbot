'''
Communicate with the server at the manufacturer
Not useful for the local drive script
'''
import paho.mqtt.client as mqtt
import json
import time
from uuid import uuid4 # 通用唯一标识符 ( Universally Unique Identifier )
import logging #日志模块

# values over max (and under min) will be clipped
MAX_X = 2400
MAX_Y = 1200
MAX_Z = 469  # TODO test this one!

def coord(x, y, z):
  return {"kind": "coordinate", "args": {"x": x, "y": y, "z": z}} # 返回json 嵌套对象

def move_request(x, y, z):
  return {"kind": "rpc_request",  # 返回 json对象，对象内含数组
          "args": {"label": ""},
          "body": [{"kind": "move_absolute",
                    "args": {"location": coord(x, y, z),
                             "offset": coord(0, 0, 0),
                             "speed": 100}}]}

def take_photo_request():
  return {"kind": "rpc_request",
          "args": {"label": ""}, #label空着是为了在blocking_request中填上uuid，唯一识别码
          "body": [{"kind": "take_photo", "args": {}}]}

def clip(v, min_v, max_v):
  if v < min_v: return min_v
  if v > max_v: return max_v
  return v

class FarmbotClient(object):

  def __init__(self, device_id, token):

    self.device_id = device_id
    self.client = mqtt.Client() # 类元素继承了另一个对象
    self.client.username_pw_set(self.device_id, token) #传入 用户名和密码
    self.client.on_connect = self._on_connect  #？？？
    self.client.on_message = self._on_message

    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s",
                        filename='farmbot_client.log',
                        filemode='a')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s\t%(message)s"))
    logging.getLogger('').addHandler(console)

    self.connected = False
    self.client.connect("clever-octopus.rmq.cloudamqp.com", 1883, 60)  #前面的url要运行按README.md中request_token.py 后面俩是TCP Port, Websocket Port
    self.client.loop_start()
    # 初始化函数里就会连接到服务器上，所以每次实例化一个新的client时，就已经连上了


  def shutdown(self):
    self.client.disconnect()
    self.client.loop_stop()

  def move(self, x, y, z):
    x = clip(x, 0, MAX_X)
    y = clip(y, 0, MAX_Y)
    z = clip(z, 0, MAX_Z)
    status_ok = self._blocking_request(move_request(x, y, z)) # 发请求
    logging.info("MOVE (%s,%s,%s) [%s]", x, y, z, status_ok) #存日志，包括执行了什么“move x y z +返回值 ”

  def take_photo(self):
    # TODO: is this enough? it's issue a request for the photo, but is the actual capture async?
    status_ok = self._blocking_request(take_photo_request())
    logging.info("TAKE_PHOTO [%s]", status_ok)

  def _blocking_request(self, request, retries_remaining=3):
    if retries_remaining==0:
      logging.error("< blocking request [%s] OUT OF RETRIES", request) #尝试3次，然后在日志中记录错误
      return False

    self._wait_for_connection() #在哪定义的？

    # assign a new uuid for this attempt
    self.pending_uuid = str(uuid4())
    request['args']['label'] = self.pending_uuid #接收move_request函数的json对象
    logging.debug("> blocking request [%s] retries=%d", request, retries_remaining)

    # send request off 发送请求
    self.rpc_status = None
    self.client.publish("bot/" + self.device_id + "/from_clients", json.dumps(request))

    # wait for response
    timeout_counter = 600  # ~1min 等待1s
    while self.rpc_status is None:          #这个self.rpc_status 是应答的flag
      time.sleep(0.1)
      timeout_counter -= 1
      if timeout_counter == 0:
        logging.warn("< blocking request TIMEOUT [%s]", request) #时间到了，无应答
        return self._blocking_request(request, retries_remaining-1)
    self.pending_uuid = None

    # if it's ok, we're done!
    if self.rpc_status == 'rpc_ok':
      logging.debug("< blocking request OK [%s]", request)
      return True

    # if it's not ok, wait a bit and retry
    if self.rpc_status == 'rpc_error':
      logging.warn("< blocking request ERROR [%s]", request)
      time.sleep(1)
      return self._blocking_request(request, retries_remaining-1)

    # unexpected state (???)
    msg = "unexpected rpc_status [%s]" % self.rpc_status
    logging.error(msg)
    raise Exception(msg)


  def _wait_for_connection(self):
    # TODO: better way to do all this async event driven rather than with polling :/
    timeout_counter = 600  # ~1min
    while not self.connected: #用一个self.connected判断连上了没有，若没连上，等待
      time.sleep(0.1)
      timeout_counter -= 1
      if timeout_counter == 0:
        raise Exception("unable to connect")

  def _on_connect(self, client, userdata, flags, rc):
    logging.debug("> _on_connect")
    self.client.subscribe("bot/" + self.device_id + "/from_device")
    self.connected = True
    logging.debug("< _on_connect")

  def _on_message(self, client, userdata, msg):
    resp = json.loads(msg.payload.decode())
    if resp['args']['label'] != 'ping':
      logging.debug("> _on_message [%s] [%s]", msg.topic, resp)
    if msg.topic.endswith("/from_device") and resp['args']['label'] == self.pending_uuid:
      self.rpc_status = resp['kind']
