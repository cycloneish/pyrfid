import sys
import hid

def findDevice():
  try:
    hiddev = hid.device()
    hiddev.open(0x0483, 0x5750)
  except Exception as e:
    print 'RFID Reader/Writer: ' + e.message
    exit()

  return hiddev

def checksum(cmd):
  length = len(cmd)
  result = 0xffff
  if length > 0:
    v4 = length
    v6 = length
    v5 = 0
    v2 = 0
    while True:
      if v5 % 8 == 0:
        v4 = cmd[v2] << 8
        v2 += 1
      v7 = result ^ v4
      result *= 2
      v4 *= 2
      if v7 & 0x8000:
        result ^= 0x1021
      v5 += 1
      v6 -= 1
      if v6 == 0:
        break
  return result & 0xffff
  
def xorSpecial(cmd):
  xorbuffer = bytearray.fromhex('49 61 6D 48 58 4A')      
  xindex = 0
  for i in range(len(cmd)):
    cmd[i] ^= xorbuffer[xindex]
    xindex += 1
    if xindex == len(xorbuffer):
      xindex = 0

def byteStaffingIn(cmd):
  output = bytearray()
  i = 0
  while i < len(cmd):
    if cmd[i] == 0xf2:
      i += 1
      if cmd[i] == 0:
        output.append(0xf0)
      elif cmd[i] == 1:
        output.append(0xf1)
      elif cmd[i] == 2:
        output.append(0xf2)
    else:
      output.append(cmd[i])
    i += 1
  return output
    
def byteStaffingOut(cmd):
  output = bytearray()
  for i in range(len(cmd)):
    if cmd[i] == 0xf0:
      output.append(0xf2)
      output.append(0x00)
    elif cmd[i] == 0xf1:
      output.append(0xf2)
      output.append(0x01)
    elif cmd[i] == 0xf2:
      output.append(0xf2)
      output.append(0x02)
    else:
      output.append(cmd[i])
  return output

def extractResponseData(buf):
  output = bytearray()
  startFlag = 0
  for i in range(len(buf)):
    if startFlag == 0:
      if buf[i] == 0xf0:
        startFlag = 1
    else:
      if buf[i] == 0xf1:
        break
      else:
        output.append(buf[i])
  return output

def prepareCommand(cmd):
  sum = checksum(cmd)
  cmd.append(sum & 0xff)
  cmd.append((sum >> 8) & 0xff)
  print 'cmd: ' + ''.join('{:02x} '.format(x) for x in cmd)
  xorSpecial(cmd)
  print 'xored cmd: ' + ''.join('{:02x} '.format(x) for x in cmd)
  staffed = byteStaffingOut(cmd)
  staffed.insert(0, 0xf0)
  staffed.append(0xf1)

  padding = 64 - len(staffed)
  i = 0
  while i < padding:
    staffed.append(0)
    i += 1
  print 'usb hid buffer: ' + ''.join('{:02x} '.format(x) for x in staffed)
  return staffed 

def checkResponse(data):
  if data:
    data = byteStaffingIn(extractResponseData(data))
    xorSpecial(data)
    sum = (data[len(data)-2] & 0xff) + ((data[len(data)-1] << 8) & 0xff00)
    data.pop()
    data.pop()
    print 'reader response: ' + ''.join('{:02x} '.format(x) for x in data)
    calcsum = checksum(data)
    print 'recvsum = {:04x}, calcsum = {:04x}'.format(sum, calcsum)
    if sum == calcsum:
      return data
    else:
      return bytearray()
  return bytearray()  

def readerTransaction(dev, cmd):
  usbbuf = prepareCommand(cmd)
  dev.write(usbbuf)
  data = dev.read(64)
  data = checkResponse(data)
  return data

#def connect(rfiddev):
#  cmd = bytearray.fromhex('00 00 00 00 00 01 01 00 00')
#  data = readerTransaction(rfiddev, cmd)
#  if len(data) > 0:
#      #print 'RFID Reader/Writer connection done.'
#      return True
#  return False

def readTag(rfiddev):
  cmd = bytearray.fromhex('42 00 18 00 01 00 00 00 00')
  data = readerTransaction(rfiddev, cmd)
  tag = bytearray()
  if len(data) > 0:
    idx = len(data) - 1
    while idx >= (len(data) - 5):
      tag.append(data[idx])
      idx -= 1
    print 'RFID TAG: ' + ''.join('{:02x} '.format(x) for x in tag)

def write4305(rfiddev, tag):
  cmd = bytearray.fromhex('42 00 18 00 01 00 02 01 06 00')
  tag.reverse()
  for x in tag:
    cmd.append(x)
  data = readerTransaction(rfiddev, cmd)
  if len(data) > 9 and data[9] != 0xf3:
    print 'RFID TAG write done.'
  else:
    print 'RFID TAG write failed.'

def writet55xx(rfiddev, tag):
  cmd = bytearray.fromhex('42 00 18 00 01 00 01 01 06 00')
  tag.reverse()
  for x in tag:
    cmd.append(x)
  data = readerTransaction(rfiddev, cmd)
  if len(data) > 9 and data[9] != 0xf3:
    print 'RFID TAG write done.'
  else:
    print 'RFID TAG write failed.'

if len(sys.argv) == 2 and sys.argv[1] == 'read':
  d = findDevice()
  readTag(d)

elif len(sys.argv) == 4 and sys.argv[1] == 'write' and sys.argv[2] == '4305':
  tag = bytearray.fromhex(sys.argv[3])
  if len(tag) == 5:
    d = findDevice()
    write4305(d, tag)

elif len(sys.argv) == 4 and sys.argv[1] == 'write' and sys.argv[2] == 't55xx':
  tag = bytearray.fromhex(sys.argv[3])
  if len(tag) == 5:
    d = findDevice()
    writet55xx(d, tag)

else:
  print 'usage: '
  print '  rfid.py read'
  print '  rfid.py write 4305 XXXXXXXXXX'
  print '  rfid.py write t55xx XXXXXXXXXX'

