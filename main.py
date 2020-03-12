#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 30 17:45:56 2019

@author: huberp

Update tables in local mysql database from a remote one with encrypted dump through ssh tunnel.

Usage:
- create a file on the remote server in your home folder which contains the credentials for the dump encryption:
    mkdir ~/conf && echo 'MYSQL_DUMP_ENCODE_PASSWORD="<OPENSSL_ENCODER_PASSWORD>"' > ~/conf/enc.cnf
- make a copy from the cnf.json.empty file as config/cnf.json and fill it with ssh and db connection data. The encoded_dump_pwd value is must be equal with the value of MYSQL_DUMP_ENCODE_PASSWORD from the enc.cnf file.
- make couple of list yml file of tabels what you want to update in your local db in the lists/ folder, use the list.yml.DIST as example

"""

import yaml
import os
import timeit
import json
from scp import SCPClient
import warnings
import sys
from datetime import datetime
import lib.utils as utils

DEFAULT_OPTIONS = [['INDIVIDUAL TABLE', 'update table by input']]
list_files = sorted(os.listdir("lists"));

def main():
    print("\nUPDATE T A B L E S\n")
    warnings.filterwarnings('ignore')
    option_cnt      = print_list()
    selected_option = select_list(option_cnt)
    start           = timeit.default_timer()
    with open(os.path.join('/home/ghi/repos/_github/database_update/config','cnf.json'), 'r') as data:
        print(data)
        cnf = json.load(data)

    cnx = utils.cnx(**cnf)
    utils.db_local_cmd(cnx, "SET GLOBAL max_allowed_packet = 10000000000;")
    utils.db_local_cmd(cnx, "SET NAMES 'utf8';")
    utils.db_local_cmd(cnx, "SET CHARACTER SET utf8;")

    print('~ create ssh connection')
    ssh = utils.get_ssh_connection(**cnf)

    if selected_option in range(len(DEFAULT_OPTIONS)):
        table = input('Enter table name : ')
        update_table(table, ssh, **cnf)
    else:
        data = update_tables_by_list_file(selected_option, ssh, cnf)
        update_date_in_list_file(selected_option, data)

    stop = timeit.default_timer()
    print("\nDONE ({} sec)".format(round(stop-start)))

def print_list():
    for i, file, description, last_update in get_list_file_data():
        print('- {}. {} [last update: {}]: {}'.format(str(i), os.path.join(file), (last_update or '-'), description))
    print (44 * '-')

    return i

def select_list(option_cnt):
    selected_option = input('Enter your choice [0-{} or x (exit)] : '.format(option_cnt))

    if selected_option == 'x':
        print("exiting")
        sys.exit()

    try:
        selected_option = int(selected_option)
    except:
        print("it's not an option")
        select_list(option_cnt)

    if selected_option not in range(option_cnt+len(DEFAULT_OPTIONS)):
        print("it's not an option")
        select_list(option_cnt)

    print("selected:", selected_option)

    return selected_option

def get_list_file_data():
    for i, option in enumerate(DEFAULT_OPTIONS):
        yield i, option[0], option[1], '-'

    for i,file in enumerate(list_files):
        with open(os.path.join('lists',file), 'r') as stream:
            try:
                c = yaml.safe_load(stream)
                yield i+len(DEFAULT_OPTIONS), file, c['description'] if 'description' in c else '', c['last_update'] if 'last_update' in c else ''
            except ValueError as e:
                sys.exit('ERROR: invalid json file: {} - {}'.format(os.path.join('config',file), e))

def update_tables_by_list_file(selected_option, ssh, cnf):
    list_file = get_selected_file(selected_option)
    with open(os.path.join('lists',list_file), 'r') as stream:
        try:
            data = yaml.safe_load(stream)
            [update_table(table, ssh, **cnf) for table in data['tables']]
        except yaml.YAMLError as exc:
            print(exc)

    return data

def update_date_in_list_file(selected_option, data):
    list_file = get_selected_file(selected_option)
    with open(os.path.join('lists',list_file), 'w') as stream:
        now = datetime.now()
        data['last_update'] = now.strftime("%d/%m/%Y %H:%M:%S")
        yaml.dump(data, stream, default_flow_style=False)

def get_selected_file(selected_option):
    return list_files[selected_option - len(DEFAULT_OPTIONS)]

@utils.parameterizer
def update_table(table, ssh,
                 remote_db_host, remote_db_user, remote_db_pwd, remote_db,
                 local_db_user, local_db_host, local_db_pwd, local_db,
                 dump_folder, encoded_dump_pwd):
    print("\n~ UPDATE TABLE: {}".format(table))

    cmd = "mysqldump -h {} -u {} -p{} {} --lock-tables=false {} > {}.sql".format(remote_db_host, remote_db_user, remote_db_pwd, remote_db, table, table)
    utils.remote_cmd(cmd, ssh, 'dump table')

    cmd = "source 'conf/enc.cnf' && tar cz {}.sql | openssl enc -aes-256-cbc -pass pass:$MYSQL_DUMP_ENCODE_PASSWORD -e > {}.tar.gz.enc".format(table, table)
    utils.remote_cmd(cmd, ssh, 'encoding')

    print('~ download encoded dump', end='.. ')
    with SCPClient(ssh.get_transport()) as scp:
        scp.get('~/{}.tar.gz.enc'.format(table), '{}.tar.gz.enc'.format(os.path.join(dump_folder,table)))

    print('OK')

    cmd = 'cd {} && openssl aes-256-cbc -d -pass pass:{} -in {}.tar.gz.enc -out {}.tar.gz && tar -xzvf {}.tar.gz'.format(dump_folder, encoded_dump_pwd, table, table, table)
    utils.local_cmd(cmd, 'uncompress')

    cmd = 'mysql --host={} --user={} --password={} --binary-mode --init-command="SET SESSION FOREIGN_KEY_CHECKS=0;" {} < {}.sql'.format(local_db_host, local_db_user, local_db_pwd, local_db, os.path.join(dump_folder,table))
    utils.local_cmd(cmd, 'update table')

    cmd = 'rm {}.sql {}.tar.gz.enc'.format(table, table)
    utils.remote_cmd(cmd, ssh, 'delete dump on remote')

    print('~ delete dump on local')
    os.remove(os.path.join('.',dump_folder,table+'.sql'))
    os.remove(os.path.join('.',dump_folder,table+'.tar.gz'))
    os.remove(os.path.join('.',dump_folder,table+'.tar.gz.enc'))
    print('  OK')

if __name__ == '__main__':
    main()
