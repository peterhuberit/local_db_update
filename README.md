# Update tables in local mysql database from a remote one with encrypted dump through ssh tunnel.

Usage:
- create a file on the remote server in your home folder which contains the credentials for the dump encryption:
    mkdir ~/conf && echo 'MYSQL_DUMP_ENCODE_PASSWORD="<OPENSSL_ENCODER_PASSWORD>"' > ~/conf/enc.cnf
- make a copy from the cnf.json.empty file as config/cnf.json and fill it with ssh and db connection data. The encoded_dump_pwd value is must be equal with the value of MYSQL_DUMP_ENCODE_PASSWORD from the enc.cnf file.
- make couple of list yml file of tabels what you want to update in your local db in the lists/ folder, use the list.yml.DIST as example
