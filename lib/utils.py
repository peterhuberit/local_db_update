#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar  8 16:56:49 2020

@author: huberp
"""

import subprocess
import paramiko
import mysql.connector

def parameterizer(func):
    '''
    decorator
    It pass the required parameters from a bunch of dict value to the function.
    Some note: ok I know it's a bit overhead here but hey, it's a demo
    '''
    def wrapper(*args, **kwargs):
        return func(*args, *[kwargs[p] for p in func.__code__.co_varnames if p in kwargs])
    return wrapper

def remote_cmd(cmd, ssh, desc=''):
    desc = '' if desc == '' else desc+' '
    print('~ {}[remote cmd]'.format(desc))
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd)
    [print('  [out]', line.strip("\n")) for line in ssh_stdout]
    [print('  [err]', line.strip("\n")) for line in ssh_stderr]
    print('  OK')

def local_cmd(cmd, desc=''):
    desc = '' if desc == '' else desc+' '
    print('~ {}[local cmd]..'.format(desc))
    result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stdout:
        print('  [out]', result.stdout.decode('utf-8'), end='')
    if result.stderr:
        print('  [err]', result.stderr.decode('utf-8'), end='')
    print('  OK')

@parameterizer
def get_ssh_connection(remote_ssh_server, remote_ssh_port, remote_ssh_user, remote_ssh_key):
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(remote_ssh_server, remote_ssh_port, username=remote_ssh_user, key_filename=remote_ssh_key)

    return ssh

@parameterizer
def cnx(local_db_user, local_db_pwd, local_db_host, local_db):
    return mysql.connector.connect(user=local_db_user,
              password=local_db_pwd,
              host=local_db_host,
              database=local_db,
              charset='utf8',
              use_unicode=True,
              use_pure=True)

def db_local_cmd(cnx, cmd):
    cursor = cnx.cursor()
    print('~ {}'.format(cmd))
    cursor.execute(cmd)
    cnx.commit()