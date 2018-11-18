# -*- coding: utf-8 -*-
import terrariumLogging
logger = terrariumLogging.logging.getLogger(__name__)

import datetime
import time
import os.path
import glob
import re
from pyownet import protocol
from hashlib import md5

from terrariumUtils import terrariumUtils, terrariumSingleton
from terrariumAnalogSensor import terrariumSKUSEN0161Sensor
from terrariumBluetoothSensor import terrariumMiFloraSensor
from terrariumGPIOSensor import terrariumYTXXSensorDigital, terrariumDHT11Sensor, terrariumDHT22Sensor, terrariumAM2302Sensor, terrariumHCSR04Sensor
from terrariumI2CSensor import terrariumSHT2XSensor, terrariumHTU21DSensor, terrariumSi7021Sensor, terrariumBME280Sensor, terrariumChirpSensor, terrariumVEML6075Sensor, terrariumSHT3XSensor

from gevent import monkey, sleep
monkey.patch_all()

class terrariumSensorCache(terrariumSingleton):
  def __init__(self):
    self.__cache = {}
    logger.debug('Initialized sensors cache')

  def add_sensor(self,address,sensor,force = False):
    if force or address not in self.__cache:
      self.__cache[address] = sensor
      logger.debug('Added new sensor to sensors cache with hash: {}. Total in cache: {}'.format(address,len(self.__cache)))

  def get_sensor(self,address):
    if address in self.__cache:
      return self.__cache[address]

    return None

class terrariumRemoteSensor(object):
  hardwaretype = 'remote'

  def __init__(self,url):
    self.__url = None
    self.__value = None
    if terrariumUtils.parse_url(url) is not False:
      self.__url = url

  def __get_raw_data(self):
    if self.__url is not None:
      self.__value = terrariumUtils.get_remote_data(self.__url)

  def __enter__(self):
    """used to enable python's with statement support"""
    return self

  def __exit__(self, type, value, traceback):
    """with support"""

  def get_current(self):
    self.__get_raw_data()
    return None if not terrariumUtils.is_float(self.__value) else float(self.__value)

  def get_temperature(self):
    return self.get_current()

  def get_humidity(self):
    return self.get_current()

  def get_moisture(self):
    return self.get_current()

  def get_conductivity(self):
    return self.get_current()

  def get_distance(self):
    return self.get_current()

  def get_ph(self):
    return self.get_current()

  def get_light(self):
    return self.get_current()

  def get_uva(self):
    return self.get_current()

  def get_uvb(self):
    return self.get_current()

  def get_fertility(self):
    return self.get_current()

  def get_co2(self):
    return self.get_current()

  def get_volume(self):
    return self.get_current()

class terrarium1WSensor(object):
  hardwaretype = 'w1'

  W1_BASE_PATH = '/sys/bus/w1/devices/'
  W1_TEMP_REGEX = re.compile(r'(?P<type>t|f)=(?P<value>[0-9\-]+)',re.IGNORECASE)

  def __init__(self,path):
    self.__path = None
    self.__value = None
    path = os.path.join(terrarium1WSensor.W1_BASE_PATH,path,'w1_slave')
    if os.path.isfile(path):
      self.__path = path

  def __get_raw_data(self):
    if self.__path is not None and os.path.isfile(self.__path):
      with open(self.__path, 'r') as w1data:
        data = w1data.read()
        w1data = terrarium1WSensor.W1_TEMP_REGEX.search(data)
        if w1data:
          # Found data
          self.__value = float(w1data.group('value')) / 1000.0

  def __enter__(self):
    """used to enable python's with statement support"""
    return self

  def __exit__(self, type, value, traceback):
    """with support"""

  def get_current(self):
    self.__get_raw_data()
    return None if not terrariumUtils.is_float(self.__value) else float(self.__value)

  def get_temperature(self):
    return self.get_current()

  @staticmethod
  def scan():
    # Scanning w1 system bus
    for address in glob.iglob(terrarium1WSensor.W1_BASE_PATH + '[1-9][0-9]-*'):
      if not os.path.isfile(address + '/w1_slave'):
        break

      data = ''
      with open(address + '/w1_slave', 'r') as w1data:
        data = w1data.read()

      w1data = terrarium1WSensor.W1_TEMP_REGEX.search(data)
      if w1data:
        # Found valid data
        yield (os.path.basename(address),'temperature' if 't' == w1data.group('type') else 'humidity')

class terrariumOWFSSensor(object):
  __CACHE_TIMEOUT = 29

  hardwaretype = 'owfs'

  def __init__(self,sensor,host='localhost',port=4304):
    self.__sensor = sensor
    self.__host = host
    self.__port = port
    self.__temperature = None
    self.__humidity = None

    self.__cached_data = {'temperature' : None,
                          'humidity'    : None,
                          'last_update' : 0}

  def __get_raw_data(self,force_update = False):
    starttime = int(time.time())
    if force_update or starttime - self.__cached_data['last_update'] > terrariumOWFSSensor.__CACHE_TIMEOUT:
      if self.__port > 0:
        try:
          proxy = protocol.proxy(self.__host, self.__port)
          try:
            self.__cached_data['temperature'] = float(proxy.read('/{}/temperature'.format(self.__sensor[:-2])))
            self.__cached_data['last_update'] = starttime
          except protocol.OwnetError:
            pass

          try:
            self.__cached_data['humidity'] = float(proxy.read('/{}/humidity'.format(self.__sensor[:-2])))
            self.__cached_data['last_update'] = starttime
          except protocol.OwnetError:
            pass

        except Exception as ex:
          logger.warning('OWFS file system is not actve / installed on this device!')

  def __enter__(self):
    """used to enable python's with statement support"""
    return self

  def __exit__(self, type, value, traceback):
    """with support"""

  def get_temperature(self):
    value = None
    logger.debug('Read temperature value from sensor type \'%s\' with address %s' % (self.__class__.__name__,self.__sensor))
    self.__get_raw_data()
    if terrariumUtils.is_float(self.__cached_data['temperature']):
      value = float(self.__cached_data['temperature'])

    logger.debug('Got data from temperature sensor type \'%s\' with address %s: temperature: %s' % (self.__class__.__name__,self.__sensor,value))
    return value

  def get_humidity(self):
    value = None
    logger.debug('Read humidity value from sensor type \'%s\' with address %s' % (self.__class__.__name__,self.__sensor))
    self.__get_raw_data()
    if terrariumUtils.is_float(self.__cached_data['humidity']):
      value = float(self.__cached_data['humidity'])

    logger.debug('Got data from humidity sensor type \'%s\' with address %s: moisture: %s' % (self.__class__.__name__,self.__sensor,value))
    return value

  @staticmethod
  def scan():
    try:
      proxy = protocol.proxy('localhost', 4304)
      for sensor in proxy.dir(slash=False, bus=False):
        stype = proxy.read(sensor + '/type').decode()
        address = proxy.read(sensor + '/address').decode()
        try:
          temp = float(proxy.read(sensor + '/temperature'))
          yield(address,'temperature')
        except protocol.OwnetError:
          pass

        try:
          humidity = float(proxy.read(sensor + '/humidity'))
          yield(address,'humidity')
        except protocol.OwnetError:
          pass

    except Exception as ex:
      logger.warning('OWFS file system is not actve / installed on this device!')

class terrariumSensor(object):
  UPDATE_TIMEOUT = 30
  ERROR_TIMEOUT = 10

  VALID_SENSOR_TYPES   = ['temperature','humidity','moisture','conductivity','distance','ph','light','uva','uvb','fertility','co2','volume']
  VALID_HARDWARE_TYPES = []

  # Append OWFS to the list of valid sensors
  VALID_HARDWARE_TYPES.append(terrariumOWFSSensor.hardwaretype)

  # Append remote sensor(s) to the list of valid sensors
  VALID_HARDWARE_TYPES.append(terrariumRemoteSensor.hardwaretype)

  # Append 1-wire sensor(s) to the list of valid sensors
  VALID_HARDWARE_TYPES.append(terrarium1WSensor.hardwaretype)

  # Append DHT sensor(s) to the list of valid sensors
  VALID_HARDWARE_TYPES.append(terrariumDHT11Sensor.hardwaretype)
  VALID_HARDWARE_TYPES.append(terrariumDHT22Sensor.hardwaretype)
  VALID_HARDWARE_TYPES.append(terrariumAM2302Sensor.hardwaretype)

  # Append I2C sensor(s) to the list of valid sensors
  VALID_HARDWARE_TYPES.append(terrariumSHT2XSensor.hardwaretype)
  VALID_HARDWARE_TYPES.append(terrariumHTU21DSensor.hardwaretype)
  VALID_HARDWARE_TYPES.append(terrariumSi7021Sensor.hardwaretype)
  VALID_HARDWARE_TYPES.append(terrariumBME280Sensor.hardwaretype)
  VALID_HARDWARE_TYPES.append(terrariumChirpSensor.hardwaretype)
  VALID_HARDWARE_TYPES.append(terrariumVEML6075Sensor.hardwaretype)
  VALID_HARDWARE_TYPES.append(terrariumSHT3XSensor.hardwaretype)

  # Append YTXX sensor(s) to the list of valid sensors
  VALID_HARDWARE_TYPES.append(terrariumYTXXSensorDigital.hardwaretype)

  # Append hc-sr04 sensor(s) to the list of valid sensors
  VALID_HARDWARE_TYPES.append(terrariumHCSR04Sensor.hardwaretype)

  # Appand analog sensor(s) to the list of valid sensors
  VALID_HARDWARE_TYPES.append(terrariumSKUSEN0161Sensor.hardwaretype)

  # Appand analog sensor(s) to the list of valid sensors
  VALID_HARDWARE_TYPES.append(terrariumMiFloraSensor.hardwaretype)

  def __init__(self, id, hardware_type, sensor_type, sensor, name = '', callback_indicator = None):
    self.__sensor_cache = terrariumSensorCache()

    self.id = id

    self.__miflora_firmware = None
    self.__miflora_battery = None

    self.notification = True

    self.set_hardware_type(hardware_type)
    self.set_address(sensor)
    self.set_name(name)
    self.set_type(sensor_type,callback_indicator)
    self.set_alarm_min(0)
    self.set_alarm_max(0)
    self.set_limit_min(0)

    # For hc-sr04 set at 10 meters else just '100' value
    if terrariumHCSR04Sensor.hardwaretype == self.get_hardware_type():
      self.set_limit_max(100000)
    # Lux light and fertility values
    elif 'light' == self.get_type() or 'fertility' == self.get_type():
      self.set_limit_max(5000)
    else :
      self.set_limit_max(100)

    # Set custom Chirp calibration values to default
    if 'chirp' == self.get_hardware_type():
      self.set_min_moist_calibration(160)
      self.set_max_moist_calibration(720)
      self.set_temperature_offset_calibration(0)

    if self.id is None:
      sensorid = self.get_address().upper() + self.get_type()
      if self.get_hardware_type() in [terrariumOWFSSensor.hardwaretype,terrarium1WSensor.hardwaretype]:
        sensorid = sensorid.replace('-','').replace('.','')
      self.id = md5(sensorid.encode()).hexdigest()

    self.current = None
    self.last_update = datetime.datetime.fromtimestamp(0)
    logger.info('Loaded %s %s sensor \'%s\' on location %s.' % (self.get_hardware_type(),self.get_type(),self.get_name(),self.get_address()))

    self.update()

  @staticmethod
  def scan(unit_indicator):
    starttime = time.time()
    logger.debug('Start scanning for temperature/humidity sensors')
    sensor_list = []

    # Scanning OWFS sensors
    for (sensor,sensortype) in terrariumOWFSSensor.scan():
      sensor_list.append(terrariumSensor(None,
                                         terrariumOWFSSensor.hardwaretype,
                                         sensortype,
                                         str(sensor),
                                         callback_indicator=unit_indicator))

    # Scanning w1 system bus
    for (sensor,sensortype) in terrarium1WSensor.scan():
      sensor_list.append(terrariumSensor(None,
                                         terrarium1WSensor.hardwaretype,
                                         sensortype,
                                         str(sensor),
                                         callback_indicator=unit_indicator))

    # Scanning bluetooth devices
    for (sensor,sensortype) in terrariumMiFloraSensor.scan():
      sensor_list.append(terrariumSensor(None,
                                         terrariumMiFloraSensor.hardwaretype,
                                         sensortype,
                                         str(sensor),
                                         callback_indicator=unit_indicator))

    logger.info('Found %d temperature/humidity sensors in %.5f seconds' % (len(sensor_list),time.time() - starttime))
    return sensor_list

  def update(self, force = False):
    now = datetime.datetime.now()
    if now - self.last_update > datetime.timedelta(seconds=terrariumSensor.UPDATE_TIMEOUT) or force:
      logger.debug('Updating %s %s sensor \'%s\'' % (self.get_hardware_type(),self.get_type(), self.get_name()))
      old_current = self.get_current()
      current = None

      try:
        starttime = time.time()
        hardwaresensor = None
        address = [self.get_address(),None,None] if ',' not in self.get_address() else self.get_address().split(',')
        if len(address) == 2:
          address.append(None)

        cache_hash = md5((self.get_hardware_type() + self.get_address()).encode()).hexdigest()
        hardwaresensor = self.__sensor_cache.get_sensor(cache_hash)

        if hardwaresensor is None:
          if terrariumRemoteSensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumRemoteSensor(address[0])
          elif terrarium1WSensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrarium1WSensor(address[0])
          elif terrariumOWFSSensor.hardwaretype == self.get_hardware_type():
            # Dirty hack for OWFS sensors.... ;)
            hardwaresensor = terrariumOWFSSensor(address[0])

          elif terrariumSHT2XSensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumSHT2XSensor(address[0],address[1])
          elif terrariumHTU21DSensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumHTU21DSensor(address[0],address[1])
          elif terrariumSi7021Sensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumSi7021Sensor(address[0],address[1])
          elif terrariumBME280Sensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumBME280Sensor(address[0],address[1])
          elif terrariumVEML6075Sensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumVEML6075Sensor(address[0],address[1])
          elif terrariumSHT3XSensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumSHT3XSensor(address[0],address[1])

          elif terrariumChirpSensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumChirpSensor(address[0],address[1],self.get_min_moist_calibration(),
                                                                        self.get_max_moist_calibration(),
                                                                        self.get_temperature_offset_calibration())

          elif terrariumYTXXSensorDigital.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumYTXXSensorDigital(address[0],address[1])

          elif terrariumDHT11Sensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumDHT11Sensor(address[0],address[1])
          elif terrariumDHT22Sensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumDHT22Sensor(address[0],address[1])
          elif terrariumAM2302Sensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumAM2302Sensor(address[0],address[1])

          elif terrariumSKUSEN0161Sensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumSKUSEN0161Sensor(address[0],address[1])

          elif terrariumHCSR04Sensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumHCSR04Sensor(address[0],address[1],address[2])

          elif terrariumMiFloraSensor.hardwaretype == self.get_hardware_type():
            hardwaresensor = terrariumMiFloraSensor(address[0])

          self.__sensor_cache.add_sensor(cache_hash,hardwaresensor)

        if hardwaresensor is not None:
          if terrariumMiFloraSensor.hardwaretype == self.get_hardware_type():
            self.__miflora_firmware = hardwaresensor.get_firmware()
            self.__miflora_battery = hardwaresensor.get_battery()

          with hardwaresensor as sensor:
            if 'temperature' == self.get_type():
              current = sensor.get_temperature()
            elif 'humidity' == self.get_type():
              current = sensor.get_humidity()
            elif 'moisture' == self.get_type():
              current = sensor.get_moisture()
            elif 'conductivity' == self.get_type():
              current = sensor.get_conductivity()
            elif 'distance' == self.get_type():
              current = sensor.get_distance()
            elif 'ph' == self.get_type():
              current = sensor.get_ph()
            elif 'light' == self.get_type():
              current = sensor.get_light()
            elif 'uva' == self.get_type():
              current = sensor.get_uva()
            elif 'uvb' == self.get_type():
              current = sensor.get_uvb()
            elif 'fertility' == self.get_type():
              current = sensor.get_fertility()
            elif 'co2' == self.get_type():
              current = sensor.get_co2()
            elif 'volume' == self.get_type():
              current = sensor.get_volume()

          del hardwaresensor

        if current is None or not (self.get_limit_min() <= current <= self.get_limit_max()):
          # Invalid current value.... log and ingore
          logger.warning('Measured value %s%s from %s sensor \'%s\' is outside valid range %.2f%s - %.2f%s in %.5f seconds.' % (current,
                                                                                                                                self.get_indicator(),
                                                                                                                                self.get_type(),
                                                                                                                                self.get_name(),
                                                                                                                                self.get_limit_min(),
                                                                                                                                self.get_indicator(),
                                                                                                                                self.get_limit_max(),
                                                                                                                                self.get_indicator(),
                                                                                                                                time.time()-starttime))

        elif not self.__within_limits(current,20):
          logger.warning('Measured value %s%s from %s sensor \'%s\' is erratic compared to previous value %s%s in %.5f seconds.' % (current,
                                                                                                                                self.get_indicator(),
                                                                                                                                self.get_type(),
                                                                                                                                self.get_name(),
                                                                                                                                self.get_current(),
                                                                                                                                self.get_indicator(),
                                                                                                                                time.time()-starttime))

        else:
          self.current = current
          self.last_update = now
          logger.info('Updated %s sensor \'%s\' from %.2f%s to %.2f%s in %.5f seconds' % (self.get_type(),
                                                                                          self.get_name(),
                                                                                          old_current,
                                                                                          self.get_indicator(),
                                                                                          self.get_current(),
                                                                                          self.get_indicator(),
                                                                                          time.time()-starttime))
      except Exception as ex:
        logger.error('Error updating %s %s sensor \'%s\' with error:' % (self.get_hardware_type(),
                                                                              self.get_type(),
                                                                              self.get_name()))
        logger.exception(ex)

  def __within_limits(self,current_value, percentage = 10.0):
    if self.current is None or self.get_type() in ['uva','uvb','light'] or self.get_hardware_type() in ['ytxx-digital']:
      return True

    total_area = abs(self.get_limit_max() - self.get_limit_min()) # 100%
    diff = abs(self.current - current_value)

    diff_percentage = (diff / total_area) * 100.0

    return diff_percentage < percentage


  def get_data(self):
    data = {'id' : self.get_id(),
            'hardwaretype' : self.get_hardware_type(),
            'address' : self.get_address(),
            'type' : self.get_type(),
            'indicator' : self.get_indicator(),
            'name' : self.get_name(),
            'current' : self.get_current(),
            'alarm_min' : self.get_alarm_min(),
            'alarm_max' : self.get_alarm_max(),
            'limit_min' : self.get_limit_min(),
            'limit_max' : self.get_limit_max(),
            'alarm' : self.get_alarm(),
            'error' : not self.is_active()
            }

    if 'chirp' == self.get_hardware_type():
      data['min_moist'] = self.get_min_moist_calibration()
      data['max_moist'] = self.get_max_moist_calibration()
      data['temp_offset'] = self.get_temperature_offset_calibration()

    if 'miflora' == self.get_hardware_type():
      data['firmware'] = self.__miflora_firmware
      data['battery'] = self.__miflora_battery

    return data

  def get_id(self):
    return self.id

  def get_hardware_type(self):
    return self.hardwaretype

  def set_hardware_type(self,hwtype):
    if hwtype in terrariumSensor.VALID_HARDWARE_TYPES:
      self.hardwaretype = hwtype

  def set_type(self,sensortype,indicator):
    if sensortype in terrariumSensor.VALID_SENSOR_TYPES:
      self.type = sensortype
      self.__indicator = indicator

  def get_type(self):
    return self.type

  def get_indicator(self):
    # Use a callback from terrariumEngine for 'realtime' updates
    return self.__indicator(self.get_type())

  def get_address(self):
    return self.sensor_address

  def set_address(self,address):
    if isinstance(address, str):
      self.sensor_address = address

  def set_name(self,name):
    self.name = str(name)

  def get_name(self):
    return self.name

  def get_alarm_min(self):
    return self.alarm_min

  def set_alarm_min(self,limit):
    self.alarm_min = float(limit)

  def get_alarm_max(self):
    return self.alarm_max

  def set_alarm_max(self,limit):
    self.alarm_max = float(limit)

  def get_limit_min(self):
    return self.limit_min

  def set_limit_min(self,limit):
    self.limit_min = float(limit)

  def get_limit_max(self):
    return self.limit_max

  def set_limit_max(self,limit):
    self.limit_max = float(limit)

  def set_min_moist_calibration(self,limit):
    self.__min_moist = float(limit)

  def get_min_moist_calibration(self):
    return self.__min_moist

  def set_max_moist_calibration(self,limit):
    self.__max_moist = float(limit)

  def get_max_moist_calibration(self):
    return self.__max_moist

  def set_temperature_offset_calibration(self,limit):
    self.__temp_offset = float(limit)

  def get_temperature_offset_calibration(self):
    return self.__temp_offset

  def get_current(self, force = False):
    current = 0 if self.current is None else self.current
    indicator = self.get_indicator().lower()

    if 'f' == indicator:
      current = terrariumUtils.to_fahrenheit(current)
    elif 'k' == indicator:
      current = terrariumUtils.to_kelvin(current)
    elif 'inch' == indicator:
      current = terrariumUtils.to_inches(current)
    elif 'usgall' == indicator:
      current = terrariumUtils.to_us_gallons(current)
    elif 'ukgall' == indicator:
      current = terrariumUtils.to_uk_gallons(current)

    return float(current)

  def get_alarm(self):
    return not self.get_alarm_min() <= self.get_current() <= self.get_alarm_max()

  def is_active(self):
    return datetime.datetime.now() - self.last_update < datetime.timedelta(minutes=terrariumSensor.ERROR_TIMEOUT)

  def notification_enabled(self):
    return self.notification == True

  def stop(self):
    logger.info('Cleaned up sensor %s at location %s' % (self.get_name(), self.get_address()))
