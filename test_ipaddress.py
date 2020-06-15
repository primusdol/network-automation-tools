#!/usr/bin/env python3
'''
test ipaddress functionality new in python 3.7
'''
import ipaddress

s1=ipaddress.IPv4Network('10.10.0.0/16')
s2=ipaddress.IPv4Network('10.10.10.0/24')
s3=ipaddress.IPv4Network('10.10.11.0/24')

print(s2, s1, s2.subnet_of(s1)) 

s4=list(ipaddress.collapse_addresses([s2,s3]))
print(s4)

s4=list(s1.address_exclude(s2))
print(s4)