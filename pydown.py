import requests
import yaml
from concurrent.futures import ThreadPoolExecutor as threads
import concurrent.futures

import time
import datetime as dt
import smtplib
from email.mime.text import MIMEText
from os import path

log_level = 0
log_file = '/var/log/pydown.log'
debug = True
smtp_port = 25
to_address = None
from_address = None
smtp_server = 'localhost'

def send_mail(msg):
    msg = str(dt.datetime.now()) + " " + msg
    log(f'Sending: {msg}')

    if debug == False:
        try:
            msg = MIMEText(msg)
            msg['Subject'] = 'PYDown notice'
            msg['From'] = from_address
            msg['To'] = to_address
            with smtplib.SMTP(smtp_server, smtp_port) as s:
                s.sendmail(msg['From'], [msg['To']], msg.as_string())
        except Exception as e:
            log(str(dt.datetime.now()) + ' ' + str(e.args[1]))

def check(website,delay=5,notify=True,renotify=False):
    notified = False
    prev_err_key = None

    log(f"Checking {website}")
    while(1):
        try:
            with requests.Session() as session:
                res = session.get(website,timeout=10)
                res.raise_for_status()
                if res.status_code == 200 and prev_err_key != None:
                    #We'll always only notify once.
                    send_mail(f'Restored {website}')
                    
                prev_err_key = None
                notified = False

        except requests.exceptions.HTTPError as e:
            errc_key = e.args[0]
            if prev_err_key != errc_key:
                prev_err_key = errc_key
                notified = False;
                
            if notified == False and notify == True:
                if renotify == False:
                    notified = True
                send_mail(f'{str(website)} shows {str(e)}')
        except Exception as e:
            log(str(e))
                
        #For now we are ignoring other request related errors. They
        #become increasingly difficult to deal with and we are mostly
        #interested in errors that aren't connection related. Those are
        #caught by our aws reporting.
        time.sleep(delay)

def log(msg):
    if log_level >= 2:
        if log_level == 3:
            print(msg)
        try:
            with open(log_file, 'a') as log:
                log.write(msg + "\n")
        except Exception as e:
            print(e)
            exit(1)
            
    elif log_level == 1:
        print(msg)
    else:
        return
      
if __name__ == '__main__':
    config = None
    prog_path = path.dirname(__file__)
    if(path.exists('/etc/pydown/pydown-config.yml')):
        config = '/etc/pydown/pydown-config.yml'
    elif(path.exists('~/.pydown-config.yml')):
        config = '~/.pydown-config.yml'
    elif(path.exists(prog_path + '/pydown-config.yml')):
        config = prog_path + '/pydown-config.yml'
    else:
        print('Cannot find pydown-config.yml file.')
        exit(1)
    
    with open(config, 'r') as file:
        conf = yaml.safe_load(file)
        notify = False
        delay = 5
        renotify = False
        
        if 'smtp_server' in conf:
            smtp_server = conf['smtp_server']
            
        if 'delay' in conf:
            delay = conf['delay']
        
        if 'notify' in conf:
            notify = conf['notify']
                
        if 'renotify' in conf:
            renotify = conf['renotify']
                    
        if 'contact' not in conf:
            print('No contact address to send to. Check your configuration. Exiting.')
            exit(1)
        to_address = conf['contact']

        if 'sender' not in conf:
            print('No from address. Check your configuration. Existing.')
            exit(1)
        from_address = conf['sender']
        
        if 'smtp_port' in conf:
            smtp_port = conf['smtp_port']
            
        if 'log_level' in conf:
            log_level = conf['log_level']

        if 'log_file' in conf:
            log_file = conf['log_file']

        if 'debug' in conf:
            debug = conf['debug']

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(conf['websites'])) as executor:
                futures = [
                    executor.submit(check, site, delay, notify=notify, renotify=renotify)
                    for site in conf['websites']
                ]
                # Optionally wait for completion and propagate exceptions
                for future in concurrent.futures.as_completed(futures):
                    future.result()  # This will re-raise any exception from the task
        except Exception as e:
            # Handle broken thread pool
            print(f"Thread pool error: {e}")


