#!/usr/bin/env python3
'''
Ping and/or portscan a list of hosts addresses
Extract the host adresses or subnets from command line arguments or read them from file
Use treads to speedup the process

20201027  2.7  primus  added a command line parser
20200826  2.6  primus  make use ipaddress functionality new in python 3.7
20200129  2.5  primus  unix and windows comptible
20160309  1.0  primus  development
''' 
__version__='2.7'

import re, os, sys 
import socket
from threading import Thread
import argparse
import subprocess
import platform
import ipaddress
import logging
  
def ip2dns(ptr):
  '''
  Try to resolve the ip number to a fqdn
  '''
  try:    
    return socket.getfqdn(ptr)
  except Exception as e:
    logging.debug('ip2dns {} {}'.format(ptr, e))
  return ptr 

def parser_init():
  parser = argparse.ArgumentParser(description='Check subnets or ip adresses by scanning ports')
  parser.add_argument('-i','--ip',       type=str, default='',                    help='addresses or subnets')
  parser.add_argument('-f','--file',     type=str, default='',                    help='read addresses or subnets from file')
  parser.add_argument(     '--port',     type=str, default='22,139,445,80,443',   help='regular ports to scan')
  parser.add_argument(     '--scan',     action='store_true',                     help='scan the addresses')
  parser.add_argument(     '--ping',     action='store_true',                     help='ping the addresses')
  parser.add_argument(     '--scanmax',  type=int, default=260,                   help='scan limit')
  parser.add_argument('-r','--resolve',  action='store_true',                     help='resolve the addresses')
  parser.add_argument('-v','--version',  action='version',                        version='%(prog)s  {}'.format(__version__))
  parser.add_argument('-d','--debug',    action='store_true',                     help='set log level to debug')
  parser.add_argument('rest', nargs='*')
  args = parser.parse_args()
  args.logger = logging.getLogger()
  args.logger.setLevel(logging.INFO)
  if args.debug:
    args.logger.setLevel(logging.DEBUG)
  if args.ip == '' and args.rest:
    args.ip=' '.join(map(str, args.rest))
  return args 


class host(object):
  '''
  Class to store the various host checks 
  '''
  def __init__(self, address):
    self.address = address
    self.ping    = ''
    self.ports   = []
    self.str     = '{}'.format(address)
    self.fqdn    = ''

  def __repr__(self):
    return '{:28} {:>8} {:16} {:40} '.format(self.str, self.ping, ' '.join(map(str, sorted(self.ports))), self.fqdn)


class find_ipv4_ipv6_addresses_or_subnet(object):
  '''
  Find all valid ipv4/ipv6 addresses or subnets from command line arguments or from a file 
  Make use of ipaddress functionality new in python 3.7 to validate the adresses or subnets
  Expand subnets to host addresses
  '''
  def __init__(self, args):
    self.hosts = {}
    self.args  = args
    self.add_hosts(self.args.ip)
    if self.args.file != '':
      with open(self.args.file,'r') as fh:
        for line in fh:
          self.add_hosts(line.strip())

  def add_hosts(self, line):
    for word in line.split():
      try:  # try a host address
        hst = ipaddress.ip_address(word)
        self.hosts.update({hst: host(hst)})
      except Exception as e:
        try: # maybe a network
          nw = ipaddress.ip_network(word, strict=False)
          if nw.num_addresses < self.args.scanmax:
            for hst in nw.hosts():
              self.hosts.update({hst: host(hst)})
          else:
            logging.warning('too many hosts to scan in this subnet {}'.format(nw))
        except Exception as e:
          logging.debug('{} {}'.format(word, e))    

  def __iter__(self):
    for hst in sorted(self.hosts.keys(), key=ipaddress.get_mixed_type_key):
      yield self.hosts[hst]  # yield the host class instance

  def total_hosts(self):
    return len(self.hosts)


class get_host_info(object):
  '''
  Retrieve a list of host instances and try to extract the portscan, ping and fqdn parameters
  Use threads to speedup the proces
  '''
  def __init__(self, args, hosts):
    self.args  = args
    self.hosts = hosts
    if self.hosts.total_hosts() <= self.args.scanmax:
      self.do_threads()
    else:
      logging.warning('too many hosts to examine')

  def do_threads(self):
    '''
    Create a list of all ping and portscan actions and start them simultaneous
    '''
    thr=[]
    ipv6info = False
    for hst in hosts:
      if self.args.scan:
        if isinstance(hst.address, ipaddress.IPv4Address):  # ipv6 checks not implemented yet
          for port in re.findall( r'[0-9]+', self.args.port):
            thr.append(Thread(target = self.check_port, args = (hst, int(port))))
        else:
          ipv6info = True
      if self.args.ping:
        if isinstance(hst.address, ipaddress.IPv4Address):  # ipv6 checks not implemented yet
          thr.append(Thread(target = self.check_ping, args = (hst,)))
        else:
          ipv6info = True
      if self.args.resolve:
        hst.fqdn = ip2dns(hst.str)
    if ipv6info:
      logging.info('ping6 or ipv6 sockets tests are not implemented yet')
    
    for thread in thr:
      thread.start()  #  start all threads
    for thread in thr:
      thread.join()   #  and wait till all ready

  def check_port(self, host, port):
    '''
    Open a socket to a host to examine if it is responding on that port
    This routine works for ipv4 sockets, ipv6 sockets are not implemented yet 
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)    
    logging.debug('check_port {} {}'.format(host.str, port))
    if s.connect_ex((host.str, port)) == 0:  
      host.ports.append(port)
    s.close()

  def check_ping(self, host):
    '''
    It's a pity, this routine is very system dependent )-;
    If there are no ping responses or wrong response time's you 
    probably have to fix the search regexp here for your system and language
    '''
    param = '-c'
    host.ping = 'timeout'
    if platform.system().lower()=='windows' :
      param = '-n'
    with subprocess.Popen(['ping', param, '1', host.str],  stdout=subprocess.PIPE, bufsize=0) as proc:
      for line in proc.stdout.read().decode('utf-8').splitlines():
        logging.debug('check_ping {}'.format(line))
        z=re.search('=([ 0-9.]+)ms',line)
        if z:
          host.ping = float(z.group(1))
          return


if __name__ == '__main__':
  args = parser_init()
  hosts = find_ipv4_ipv6_addresses_or_subnet(args)
  get_host_info(args, hosts)
  for host in hosts:
    print(host)
