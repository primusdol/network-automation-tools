#!/usr/bin/env python3
'''
Expand or compress a hyphen comma seperated HPE/Aruba switch portlist
example A1,A3-A6  ->  A1,A3,A4,A5,A6
HPE/Aruba interface names exists of a number with 1 or 2 digits which may be preceded by a unit letter.

20200615  1.2  primus  better input validation
20190202  1.1  primus  implemented class iterator 
20181207  1.0  primus  development
'''

__version__ = '1.2'

import re

class portrange(object):
  def  __init__(self, s):
    '''
    Expand or compress a hyphen comma seperated HPE/Aruba switch portlist
    Control overlapping ranges or double interface numbers.
    '''
    self.ll={}
    self.add(s)

  def add(self, s):
    s=s.upper()
    s=re.sub(r'[^A-Z0-9,-]','',s)  # strip all possible illegal characters from input
    s=s.strip(',-')                # these are allowed, but not at begin or end
    for x in s.split(','):
      t=x.split('-')
      if len(t)==1:
        self.append(self.portname(t[0]))
      elif len(t)==2:
        self.appendrange(self.portname(t[0]), self.portname(t[1]))
      else:
        raise SyntaxError('portrange at {}'.format(s))

  def portname(self, port):
    '''
    HPE/Aruba interface names exists of a number with 1 or 2 digits which may be preceded by a unit letter.
    '''
    z=re.search(r'^([A-Z]{0,1})([0-9]{1,2})$',port)
    if z:
      return (z.group(1), int(z.group(2)))   # letter, integer
    raise SyntaxError('portname at {}'.format(port))

  def append(self, pn):  # insert if not already present
    if pn[0] not in self.ll.keys():
      self.ll.update({pn[0]:[pn[1]]})
    else:
      if pn[1] not in self.ll[pn[0]]:
        self.ll[pn[0]].append(pn[1])
        self.ll[pn[0]] = sorted(self.ll[pn[0]])

  def appendrange(self, pn1, pn2):
    if pn1[0] == pn2[0]:  # range only with same unit letters
      if pn1[1] < pn2[1]: # lower interfaces must be first in list
         for i in range(pn1[1], pn2[1]+1):
           self.append((pn1[0], i))
         return
    raise SyntaxError('portrange at {}{:02d}-{}{:02d}'.format(pn1[0], pn1[1], pn2[0], pn2[1]))

  def __repr__(self):
    s=''
    for letter in sorted(self.ll.keys()):
      i = 0 
      while i < len(self.ll[letter]):
        a = self.ll[letter][i]
        while i < len(self.ll[letter])-1 and self.ll[letter][i]+1 == self.ll[letter][i+1]: 
          i += 1
        b = self.ll[letter][i]
        if b - a > 1:
          s+='{}{}-{}{},'.format(letter,a,letter,b)
        elif b - a == 1:
          s+='{}{},{}{},'.format(letter,a,letter,b)
        else:
          s+='{}{},'.format(letter,a)
        i += 1
    return s.strip(',')

  def __iter__(self):
    for letter in sorted(self.ll.keys()):
      for number in self.ll[letter]:
        yield('{}{:02d}'.format(letter, number))

if __name__ == '__main__':
  pl=portrange(',-8,24,a5-a 7,c5-c6	,a1,A5-A	9,A3-A10,8,03-9,05-07,c04,-	\n\n')
  for interface in pl:
    print(interface)
  print(pl)