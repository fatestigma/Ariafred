# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import sys
import xmlrpclib
from workflow import Workflow
from workflow.notify import notify


def set_query(query):
    os_command = 'osascript -e "tell application \\"Alfred 2\\" to search \\"' + query + '\\""'
    os.system(os_command)


def run_aria():
    os_command = 'export PATH=$PATH:/usr/local/bin:/usr/local/aria2/bin && aria2c --enable-rpc --rpc-listen-all=true --rpc-allow-origin-all -c -D'
    if os.system(os_command) == 0:
        notify('Aria2 has started successfully')
    else:
        notify('Failed to start Aria2, please run manually')


def get_task_name(gid):
    bt = server.tellStatus(secret, gid, ['bittorrent'])
    path = server.getFiles(secret, gid)[0]['path']
    if bt:
        file_num = len(server.getFiles(secret, gid))
        if 'info' in bt:
            bt_name = bt['bittorrent']['info']['name']
        else:
            bt_name = os.path.basename(os.path.dirname(path))
        if not bt_name:
            bt_name = 'Task name not obtained yet'
        name = u'{bt_name} (BT: {file_num} files)'.format(bt_name=bt_name, file_num=file_num)
    else:
        name = os.path.basename(path)
        if not name:
            name = 'Task name not obtained yet'
    return name


def reveal(gid, alfred=False):
    dir = server.tellStatus(secret, gid, ['dir'])['dir']
    filepath = server.getFiles(secret, gid)[0]['path'].encode('utf-8')
    if os.path.exists(filepath):
        if alfred:
            os_command = 'tell application "Alfred 2" to search "%s"' % filepath
            os_command = "osascript -e '%s'" % os_command
        else:
            os_command = 'open -R "%s"' % filepath
    else:
        os_command = 'open "%s" ' % dir
    os.system(os_command)


def pause_all():
    server.pauseAll(secret)
    notify('All active downloads paused')


def resume_all():
    server.unpauseAll(secret)
    notify('All paused downloads resumed')


def switch_task(gid):
    name = get_task_name(gid)
    status = server.tellStatus(secret, gid, ['status'])['status']
    if status in ['active', 'waiting']:
        server.pause(secret, gid)
        notify('Download paused:', name)
    elif status == 'paused':
        server.unpause(secret, gid)
        notify('Download resumed:', name)
    elif status == 'complete':
        pass
    else:
        urls = server.getFiles(secret, gid)[0]['uris']
        if urls:
            url = urls[0]['uri']
            server.addUri(secret, [url])
            server.removeDownloadResult(secret, gid)
            notify('Download resumed:', name)
        else:
            notify('Cannot resume download:', name)


def get_url(gid):
    urls = server.getFiles(secret, gid)[0]['uris']
    if urls:
        url = urls[0]['uri']
        notify('URL has been copied to clipboard:', url)
        print(url, end='')
    else:
        notify('No URL found')


def add_task(url):
    gid = server.addUri(secret, [url])
    notify('Download added:', url)


def add_bt_task(filepath):
    server.addTorrent(secret, xmlrpclib.Binary(open(filepath, mode='rb').read()))
    notify('BT download added:', filepath)


def remove_task(gid):
    name = get_task_name(gid)
    status = server.tellStatus(secret, gid, ['status'])['status']
    if status in ['active', 'waiting', 'paused']:
        server.remove(secret, gid)
    server.removeDownloadResult(secret, gid)
    notify('Download removed:', name)


def clear_stopped():
    server.purgeDownloadResult(secret)
    notify('All stopped downloads cleared')


def quit_aria():
    server.shutdown(secret)
    notify('Aria2 shutting down')
    kill_notifier()

def speed_convert(s):
    try:
        speed = int(s)
        m = speed / (1024 * 1024)
        k = speed / 1024
        if m != 0:
            string = '%d MiB/s' % m
        elif k != 0:
            string = '%d KiB/s' % k
        else:
            string = '%d Byte/s' % speed
        return (s, string)
    except:
        import re
        m = re.match(r'\s*(\d+)\s*(\w+)\s*', s)
        if m:
            number = m.group(1)
            unit = m.group(2)[0]
            if unit == 'K' or unit == 'k':
                exp = 1
                unit = 'KiB/s'
            elif unit == 'M' or unit == 'm':
                exp = 2
                unit = 'MiB/s'
            elif unit == 'G' or unit == 'g':
                exp = 3
                unit = 'GiB/s'
            else:
                exp = 0
                unit = 'Byte/s'
            string = '%s %s' % (number, unit)
            speed = int(number) * (1024 ** exp)
            return (str(speed), string)
        else:
            return ('0', '0 Byte')

def limit_speed(type, speed):
    option = 'max-overall-' + type + '-limit'
    speed_value,speed_string = speed_convert(speed)
    server.changeGlobalOption(secret, {option: speed_value})
    notify('Limit ' + type + ' speed to:', speed_string + '/s')

def limit_num(num):
    server.changeGlobalOption(secret, {'max-concurrent-downloads': num})
    notify('Limit concurrent downloads to:', num)


def kill_notifier():
    with open(wf.cachefile('notifier.pid'), 'r') as pid_file:
        pid = pid_file.readline()
    os_command = 'pkill -TERM -P ' + pid
    os.system(os_command)

def set_rpc(path):
    wf.settings['rpc_path'] = path
    notify('Set RPC path to: ', path)
    kill_notifier()

def set_secret(str):
    wf.settings['secret'] = str
    notify('Set RPC secret to: ', str)
    kill_notifier()

def get_help():
    os_command = 'open https://github.com/Wildog/Ariafred'
    os.system(os_command)


def main(wf):
    command = wf.args[0]

    if command == '--reveal':
        reveal(wf.args[1])
    elif command == '--alfred':
        reveal(wf.args[1], True)
    elif command == '--rm':
        remove_task(wf.args[1])
    elif command == '--add':
        add_task(wf.args[1])
    elif command == '--bt':
        add_bt_task(wf.args[1])
    elif (command == '--pause'
        or command == '--resume'
        or command == '--switch'):
        switch_task(wf.args[1])
    elif command == '--pauseall':
        pause_all()
    elif command == '--resumeall':
        resume_all()
    elif command == '--clear':
        clear_stopped()
    elif command == '--url':
        get_url(wf.args[1])
    elif command == '--rpc-setting':
        set_rpc(wf.args[1])
    elif command == '--secret-setting':
        set_secret(wf.args[1])
    elif command == '--run-aria2':
        run_aria()
    elif command == '--quit':
        quit_aria()
    elif command == '--help':
        get_help()
    elif command == '--limit-download':
        limit_speed('download', wf.args[1])
    elif command == '--limit-upload':
        limit_speed('upload', wf.args[1])
    elif command == '--limit-num':
        limit_num(wf.args[1])
    elif command == '--go-rpc-setting':
        set_query('aria rpc ')
    elif command == '--go-secret-setting':
        set_query('aria secret ')
    elif command == '--go-active':
        set_query('aria active ')
    elif command == '--go-stopped':
        set_query('aria stopped ')
    elif command == '--go-waiting':
        set_query('aria waiting ')
    elif command == '--go-download-limit-setting':
        set_query('aria limit ')
    elif command == '--go-upload-limit-setting':
        set_query('aria limitup ')


if __name__ == '__main__':

    wf = Workflow()
    rpc_path = wf.settings['rpc_path']
    server = xmlrpclib.ServerProxy(rpc_path).aria2
    secret = 'token:' + wf.settings['secret']
    sys.exit(wf.run(main))
