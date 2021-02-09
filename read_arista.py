#!/usr/bin/env python3
'''
Lees de Arista switch interfaces uit en verzamel de parameters 
die nodig zijn om de cisco-naar-arista patchlijst inzichtelijk te maken'

20210128  1.0  rusl  copy van lees_cisco.py
'''

__version__ = '1.0'

import os, sys, re
from netmiko import ConnectHandler
import time
import argparse
import getpass
import pyaes
import binascii
import hashlib
import random
from threading import Thread
import logging

#sys.path.append('../../scripts')
#import netwerk

  
def sortableport(port):      # converteer poortnummers van 1 cijfer naar 2 cijfers met voorloop nul, zodat we kunnen sorteren
  si=''
  for n in re.sub('Et', '', port).split('/'):
    si = '{}/{:02d}'.format(si, int(n))
  si = si.strip('/')
  return 'Et' + si

class switchlijst(object): 
  '''
  Cloudvision heeft een export to csv optie bij de devices
  Deze file lezen we hier in voor het overzicht en ipnummers van alle arista apparatuur
  
  bornal243-021,streaming / compliant / provisioned,7050SX3-48C8,4.25.1F,1.12.1,10.56.63.41,94:8e:d3:0b:e4:1d,JPE20442591
  '''
  def __init__(self, args):
    self.args     = args
    self.fname    = os.path.join(self.args.path, 'cvp-device-inventory.csv') 
    self.swl      = {}
    if os.path.exists(self.fname):
      with open(self.fname) as fp:
        for line in fp.read().splitlines():
          if re.search('^born',line):
            sw = line.split(',')
            for i in range(len(sw)):
              sw[i]=sw[i].strip()
            self.swl.update({sw[0]:sw[1:]}) 
      logging.info('arista devices gelezen')
    else:
      logging.error('arista devices niet gevonden {}'.format(os.path.basename(self.fname)))

  def __iter__(self):  
    for i in sorted(self.swl.keys()):
      yield i

  def get_ip(self, sw_name):  
    return self.swl[sw_name][4]  # hier mag nog wel een error checkje bij (-;

  def report(self):
    for i in self.__iter__():
      print(i, self.swl[i])



class lees_arista(object):

  def __init__(self, args):
    self.args     = args
    self.swl      = switchlijst(args)
    self.switch   = {}
    self.switchpo = {}
    self.lldp     = []

#    self.swl.report()
    self.do_treats()

  def do_treats(self):
    thr=[]
    for swn in self.swl: 
      if re.search('born..24[3|4]-', swn):  # alle leafs selectie = 'born.l24[3|4]-'
        thr.append(Thread(target = self.do_switch, args = (swn, )))
    for thread in thr:
      thread.start()  #  start ze allemaal
    for thread in thr:
      thread.join()   # en wacht tot ze allemaal klaar zijn

  def do_switch(self, swn):
    time.sleep(random.uniform(0,20)) # trap ze niet allemaal op precies hetzelfde moment af
    logging.info('{} processing'.format(swn))
    self.switch.update({swn:[]})
    self.switchpo.update({swn:[]})
    try:
      ssh_sw = ConnectHandler(device_type='arista_eos', ip=self.swl.get_ip(swn), username=self.args.user, password=self.args.password)
      time.sleep(0.5)
      ssh = ssh_sw.send_command('show int status')
      for line in ssh.splitlines():
        z = re.search('(^Et[0-9\/]+)', line)             # is het een Et interface
        if z :
          intf = sortableport(z.group(1))
          self.switch[swn].append('{:13}\t{}'.format(intf, line))
#          if re.search(' connected ', line) and not re.search(' f-path ', line): # moet wel de moeite waard zijn (-;
#            self.do_interface(swn, ip, intf, ssh_sw)
        z = re.search('(^Po[0-9]+)', line)                # of misschien een port-channel
        if z :
          po = z.group(1)
          self.switchpo[swn].append('{:13}\t{}'.format(po, line))
#          self.do_port_channel(swn, ip, po, ssh_sw)
      ssh = ssh_sw.send_command('show lldp neighbors')
      for line in ssh.splitlines():
        z = re.search('(^Et[0-9\/]+)', line)             # is het een Et interface
        if z:
          intf = sortableport(z.group(1))
          s = line.split()
          s[1] = re.sub('.rechtspraak.minjus.nl','',s[1])
          if re.search('(^Ethernet[0-9\/]+)', s[2]) :       # is het een Et interface
            s[2] = sortableport(re.sub('hernet','',s[2]))
          self.lldp.append('{}\t{}\t{}\t{}'.format(swn, intf, s[1], s[2]))
    except Exception as e:
      logging.error('{} {}'.format(swn, e))

#  def do_interface(self, swn, ip, intf, ssh_sw):
#    logging.info('{} {} processing'.format(swn, intf))
#    ssh = ssh_sw.send_command('sh run int {} all | no-more'.format(intf))
#    for line in ssh.splitlines():
#      self.switch[swn].append('{:13}\t{}'.format(intf, line))
#
#  def do_port_channel(self, swn, ip, po, ssh_sw):
#    logging.info('{} {} processing'.format(swn, po))
#    ssh = ssh_sw.send_command('sh run int {} | no-more'.format(po))
#    for line in ssh.splitlines():
#      self.switchpo[swn].append('{:13}\t{}'.format(po, line))

  def save(self):
    fname = os.path.join(self.args.path, 'arista.db')  
    with open(fname, 'w') as fp:
      for k,v in sorted(self.switch.items()):
        for intf in v:
          fp.write('{}\t{}\n'.format(k, intf)) 
      for k,v in sorted(self.switchpo.items()):
        for po in v:
          fp.write('{}\t{}\n'.format(k, po)) 
    logging.info('saved {}'.format(os.path.basename(fname)))

  def save_lldp(self):
    fname = os.path.join(self.args.path, 'arista_lldp.db')  
    with open(fname, 'w') as fp:
      for l in sorted(self.lldp):
        fp.write('{}\n'.format(l)) 
    logging.info('lldp saved {}'.format(os.path.basename(fname)))


def parser_init():
  osp = os.path.join('//rechtspraak.minjus.nl/','/Services/Repository/Netwerk/users/rusl/cloudvision/')
  parser = argparse.ArgumentParser(description='lees de arista switch interfaces uit en verzamel de parameters die nodig zijn voor de migratie')
  parser.add_argument('-d','--debug',     action='store_true',              help='logging debug')
  parser.add_argument(     '--info',      action='store_true',default=True, help='logging info')
  parser.add_argument('-u','--user',      type=str, default='',             help='user')
  parser.add_argument('-p','--password',  type=str, default='',             help='password, als deze leeg is krijg je een prompt')
  parser.add_argument(     '--path',      type=str, default=osp,            help='working directory path')
  parser.add_argument('-v','--version',   action='version', version='%(prog)s  {version}'.format(version=__version__))
  args = parser.parse_args()
  h = hashlib.sha256(os.environ.get('USERNAME').encode())
  if h.hexdigest() == 'e6ddd588134906b6bc14d938ea5fb24678989523484e7695ba429cb41b8bcfdf':
    aes           = pyaes.AESModeOfOperationCTR(os.environ.get('sleutel').encode())
    args.user     = aes.decrypt(binascii.unhexlify('bc9e200ff77a')).decode('utf-8')
    aes           = pyaes.AESModeOfOperationCTR(os.environ.get('sleutel').encode())
    args.password = aes.decrypt(binascii.unhexlify('90812710f531ae')).decode('utf-8')
  if args.user == '' :
    args.user = input('user     :')
  if args.password == '' :
    args.password = getpass.getpass(prompt='password : ')
  if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
  else:
    logging.getLogger().setLevel(logging.INFO)
  return args

if __name__ == '__main__':
  args = parser_init()
#  netwerk.mylogger(args=args)
  logging.info('starting {} {} door {}'.format(os.path.basename(sys.argv[0]),__version__, args.user))
  la = lees_arista(args)
  la.save()
  la.save_lldp()
