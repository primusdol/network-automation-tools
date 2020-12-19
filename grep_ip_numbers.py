#!/usr/bin/env python3
'''
grep all ipv4 numbers from a file and try to resolve the addresses

20201027 1.1  primus  better error handling
20201023 1.0  primus  included argparse
20191015 0.1  primus  develop
'''
__version__ = '1.1'

import re, os
import socket
import argparse
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def parser_init():
  parser = argparse.ArgumentParser(description='grep all ip numbers from a file and try to resolve the addresses')
  parser.add_argument('file'            ,type=str,            help='input filename')
  parser.add_argument('-d','--debug'    ,action='store_true', help='log level debug')
  parser.add_argument('-v','--version'  ,action='version', version='%(prog)s  {}'.format(__version__))
  return parser.parse_args() 

def ipsort(s):
  '''
  use the hex value to sort the ip numbers
  '''
  ss=s.split('/')  # if there is a cidr or subnet strip it
  try:
    return '0x{:02x}{:02x}{:02x}{:02x}'.format(*map(int, ss[0].split('.')))
  except: 
    return s

def ip2fqdn(ip):
  '''
  convert an ip number to a fqdn
  '''
  try:
    return socket.getfqdn(ip.strip())
  except Exception as e:
    logging.info('ip2fqdn {} {}'.format(ip, e))
  return query

class find_ip_numbers_in_file(object):
  '''
  grep all ip numbers from a file and try to resolve the addresses
  input args from argsparse, args.file and args.debug must be defined
  '''
  def __init__(self, args):
    self.args = args
    self.ips  = {}
    self.parse_file()

  def parse_file(self):
    if not os.path.exists(self.args.file): 
      raise FileNotFoundError(self.args.file)
    with open(self.args.file, 'r') as fp: 
      for line in fp:
        for ip in re.findall('[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', line):  # does it look like an ip number ?
          if self.args.debug:                                                          # note this does not check if it is a valid ip
            logging.debug('\t{:16} {:40} {}'.format(ip, ip2fqdn(ip), line.strip()))
          if ip not in self.ips.keys(): 
            self.ips.update({ip:1})
          else:
            self.ips[ip] += 1   # increment the ip number counter if already found

  def __repr__(self):
    rs = '{:16}\t{:5}\t{}\n'.format('ip', 'count', 'fqdn')
    for k in sorted(self.ips.keys(), key=ipsort):
      rs += '{:16}\t{:5d}\t{}\n'.format(k, self.ips[k], ip2fqdn(k))
    rs += 'found {} different ip numbers in {}\n'.format(len(self.ips),self.args.file)
    return rs

if __name__ == '__main__':
  args = parser_init()
  print(find_ip_numbers_in_file(args))
