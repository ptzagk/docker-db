#! /usr/bin/env python2.7

import re, base64, string, random, os, subprocess, time, shutil, hashlib, uuid
# pwd is only available on UNIX systems
try:
    import pwd
except ImportError:
    import getpass
    pwd = None

#{{{ Units to bytes

def units2bytes(data):
    ma_units = units2bytes.re_parse.match(str(data))
    if not ma_units: raise RuntimeError('Could not parse %s as number with units.' % repr(data))
    num1, num2, unit, two = ma_units.groups()
    num1 = num1.strip().replace(' ', '')
    if unit is not None: unit = unit.lower()
    if num2 is None: num = int(num1)
    else: num = float("%s.%s" % (num1, num2.strip()))
    if two is None:
        return num * units2bytes.convd[unit]
    return num * units2bytes.convb[unit]
units2bytes.re_parse = re.compile(r'^\s*([0-9]+)(?:[.]([0-9]+))?\s*(?:([KkMmGgTtPpEeZzYy])(i)?)?[Bb]?\s*$')
units2bytes.convf = lambda x: {'k': x ** 1, 'm': x ** 2, 'g': x ** 3, 't': x ** 4, 'p': x ** 5, 'e': x ** 6, 'z': x ** 7, 'y': x ** 8, None: 1}
units2bytes.convd = units2bytes.convf(1000)
units2bytes.convb = units2bytes.convf(1024)

#}}}

#{{{ Bytes to units
def bytes2units(num):
    for x in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
#}}}
 
#{{{ Gen passwd
def gen_passwd(length):
    """
    Generates a new password with given length.
    """
    key = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))
    return key
#}}}
 
#{{{ Gen base64 passwd
def gen_base64_passwd(length):
    """
    Generates a base64 encoded password with given length.
    """
    return base64.b64encode(gen_passwd(length))
#}}}

#{{{ Get effective UID
def get_euid():
    """
    Returns the effective user ID on UNIX systems and a default value on Windows.
    """
    if "geteuid" in dir(os):
        return os.geteuid()
    else:
        return 500
#}}}
 
#{{{ Get effective GID
def get_egid():
    """
    Returns the effective group ID on UNIX systems and a default value on Windows.
    """
    if "getegid" in dir(os):
        return os.getegid()
    else:
        return 500
#}}}

#{{{ Get username
def get_username():
    """
    Returns the (effective) username on UNIX and Windows.
    """
    if "geteuid" in dir(os):
        return pwd.getpwuid(os.geteuid()).pw_name
    else:
        return getpass.getuser()

#}}}

#{{{ Get first interface
def get_first_interface(timeout=1):
    """
    Returns the name and network address of the first interface that is in state UP. 
    Retries until an interface is found or the given time (in seconds) has elapsed.
    """
    iface = 'N/A'
    address = 'N/A'
    found_if_up = False
    time_elapsed = 0
    while found_if_up == False and time_elapsed < timeout:       
        output = subprocess.check_output(['/usr/bin/env', 'ip', 'addr'])
        for line in output.splitlines():
            line = line.strip()
            # found an interface that is UP
            if 'state UP' in line:
                found_if_up = True
                iface = line.split(':')[1].strip()
            # get its inet address (usually 3 lines down)
            if 'inet' in line and found_if_up == True:
                address = line.split(' ')[1].strip()
                return (iface, address)
        # no interface is UP yet
        time.sleep(1)
        time_elapsed += 1
#}}}

#{{{ Get all interfaces
def get_all_interfaces(timeout=1, up_only=True):
    """
    Returns a list of tuples of all interfaces in state UP (if 'up_only' is True).
    Retries until at least one interface is found or the given time (in seconds) has elapsed.
    """

    interfaces = []
    found_if = False
    time_elapsed = 0
    while len(interfaces) == 0 and time_elapsed < timeout:
        iface = 'N/A'
        address = 'N/A'
        state = 'N/A'
        output = subprocess.check_output(['/usr/bin/env', 'ip', 'addr'])
        for line in output.splitlines():
            line = line.strip()
            # found an interface 
            # -> remember state and address
            if 'state UP' in line:
                found_if = True
                state = 'UP'
                iface = line.split(':')[1].strip()
            elif up_only is False and 'state DOWN' in line:
                found_if = True
                state = 'DOWN'
                iface = line.split(':')[1].strip()
            # extract and remember inet address 
            # --> usually 3 lines down
            if 'inet' in line and found_if is True:
                address = line.split(' ')[1].strip()   
                # append the new interface
                interfaces.append((iface, address, state))
                # reset local values
                # -> the next line with 'state UP' or 'state DOWN' has to be checked again
                found_if = False
                iface = 'N/A'
                address = 'N/A'
                state = 'N/A'
        # no interface found yet
        if len(interfaces) == 0:
            time.sleep(1)
            time_elapsed += 1             

    return interfaces
#}}}
 
#{{{ Rotate file
def rotate_file(current, max_copies):
    previous = current + r'.%d'
    for fnum in range(max_copies - 1, -1, -1):
        if os.path.exists(previous % fnum):
            try:
                os.rename(previous % fnum, previous % (fnum + 1))
                # Windows-workaround if "previous" exists
            except OSError:
                os.remove(previous % (fnum + 1))
                os.rename(previous % fnum, previous % (fnum + 1))
    if os.path.exists(current):
        shutil.copy(current, previous % 0)
#}}}

#{{{ MD5
def md5(filename):
    """
    Returns the MD5 sum of the given file.
    """

    md5sum = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5sum.update(chunk)
    return md5sum.hexdigest()
#}}}

#{{{ Generate node uuid    
def gen_node_uuid():
    """
    Generates a UUID for EXASOL cluster nodes (40 chars long). 
    """
    return (uuid.uuid4().hex + uuid.uuid4().hex)[:40].upper()
#}}}
