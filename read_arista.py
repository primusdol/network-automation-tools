#!/usr/bin/env python3
'''
Read the Arista switch interfaces and collect common parameters 
Use a Cloudvison device export for the list of Arista switches

20210209  1.1  primus  standalone version
20210128  1.0  primus  copy from read_cisco.py
'''

__version__ = '1.1'

import os, sys, re
from netmiko import ConnectHandler
import time
import argparse
import getpass
import random
from threading import Thread
import logging

  
def sortableport(port):      # convert interface numbers from 1 digit to 2 withc leading zero, so we can sort on it
  si=''
  for n in re.sub('Et', '', port).split('/'):
    si = '{}/{:02d}'.format(si, int(n))
  si = si.strip('/')
  return 'Et' + si

class switchlijst(object): 
  '''
  Use a Cloudvison device export for the list of Arista switches
  
  arista243-021,streaming / compliant / provisioned,7050SX3-48C8,4.25.1F,1.12.1,10.10.10.10,aa:bb:cc:dd:ee:ff,serial
  '''
  def __init__(self, args):
    self.args     = args
    self.fname    = os.path.join(self.args.path, 'cvp-device-inventory.csv') 
    self.swl      = {}
    if os.path.exists(self.fname):
      with open(self.fname) as fp:
        for line in fp.read().splitlines():
          if re.search('^arista',line):         # change this filter for your names
            sw = line.split(',')
            for i in range(len(sw)):
              sw[i]=sw[i].strip()
            self.swl.update({sw[0]:sw[1:]}) 
      logging.info('found arista devices')
    else:
      logging.error('arista devices not found {}'.format(os.path.basename(self.fname)))

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
#      if re.search('arista..24[3|4]-', swn):  # use this filter te select the only a part of the devices
      thr.append(Thread(target = self.do_switch, args = (swn, )))
    for thread in thr:
      thread.start()  # start all threads
    for thread in thr:
      thread.join()   # and wait till completed

  def do_switch(self, swn):
    time.sleep(random.uniform(0,20)) # not all at exact the same time
    logging.info('{} processing'.format(swn))
    self.switch.update({swn:[]})
    self.switchpo.update({swn:[]})
    try:
      ssh_sw = ConnectHandler(device_type='arista_eos', ip=self.swl.get_ip(swn), username=self.args.user, password=self.args.password)
      time.sleep(0.5)
      ssh = ssh_sw.send_command('show int status')
      for line in ssh.splitlines():
        z = re.search('(^Et[0-9\/]+)', line)             # is it a Et interface
        if z :
          intf = sortableport(z.group(1))
          self.switch[swn].append('{:13}\t{}'.format(intf, line))
        z = re.search('(^Po[0-9]+)', line)                # or a Po channel
        if z :
          po = z.group(1)
          self.switchpo[swn].append('{:13}\t{}'.format(po, line))
      ssh = ssh_sw.send_command('show lldp neighbors')
      for line in ssh.splitlines():
        z = re.search('(^Et[0-9\/]+)', line)             # is it a Et interface
        if z:
          intf = sortableport(z.group(1))
          s = line.split()
          if re.search('(^Ethernet[0-9\/]+)', s[2]) :
            s[2] = sortableport(re.sub('hernet','',s[2]))
          self.lldp.append('{}\t{}\t{}\t{}'.format(swn, intf, s[1], s[2]))
    except Exception as e:
      logging.error('{} {}'.format(swn, e))

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
  osp = '/home/cloudvision/'
  parser = argparse.ArgumentParser(description='Read the Arista switch interfaces and collect common parameters')
  parser.add_argument('-d','--debug',     action='store_true',              help='logging debug')
  parser.add_argument(     '--info',      action='store_true',default=True, help='logging info')
  parser.add_argument('-u','--user',      type=str, default='',             help='user')
  parser.add_argument('-p','--password',  type=str, default='',             help='password')
  parser.add_argument(     '--path',      type=str, default=osp,            help='working directory path')
  parser.add_argument('-v','--version',   action='version', version='%(prog)s  {version}'.format(version=__version__))
  args = parser.parse_args()
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
  logging.info('starting {} {} by {}'.format(os.path.basename(sys.argv[0]),__version__, args.user))
  la = lees_arista(args)
  la.save()
  la.save_lldp()
