# use unpack from struct and argv from sys
from struct import unpack; from sys import argv
import os.path

# setup args as a variable to hold argv -- there will be three
# in total script, input file, output file.
args = argv
usage = "\nUsage: python Driv3rs.py [SOS_DRIVER_FILE] [output_file.csv]\n"

# check that user passed required number of arguments
if len(args) < 3:
    print usage
    exit()
# stick passed arugments into variables for later
disk_img = args[1]
output_csv = args[2]

# this function unpacks several read operations --
# text, binary, and single-byte. Each uses unpack from
# struct and attempts converts the resulting tuple into
# into either a string or integer, depending upon need.
def readUnpack(bytes, **options):
    if options.get("type") == 't':
        SOS = SOSfile.read(bytes)
        text_unpacked = unpack('%ss' % bytes, SOS)
        return ''.join(text_unpacked)

    if options.get("type") == 'b':
        SOS = SOSfile.read(bytes)
        offset_unpacked = unpack ('< H', SOS)
        return int('.'.join(str(x) for x in offset_unpacked))

    if options.get("type") == '1':
        SOS = SOSfile.read(bytes)
        offset_unpacked = unpack ('< B', SOS)
        return int(ord(SOS))

# this function takes a byte and performs bit operations
# to determine integer value. Outputs as a string. Used in
# the versioning DIB pullout. Values are stored in HEX.
def nibblize(byte, **options):
    if options.get("direction") == 'high':
        return str(int(hex(byte >> 4), 0))
    if options.get("direction") == 'low':
        return str(int(hex(byte & 0x0F), 0))

# dictionary for device types and sub types.
dev_types ={273: 'Character Device, Write-Only, Formatter',
            321: 'Character Device, Write-Only, RS232 Printer',
            577: 'Character Device, Write-Only, Silentype',
            833: 'Character Device, Write-Only, Parallel Printer',
            323: 'Character Device, Write-Only, Sound Port',
            353: 'Character Device, Read-Write, System Console',
            354: 'Character Device, Read-Write, Graphics Screen',
            355: 'Character Device, Read-Write, Onboard RS232',
            356: 'Character Device, Read-Write, Parallel Card',
            481: 'Block Device, Disk ///',
            721: 'Block Device, PROFile',
            4337: 'Block Device, CFFA3000'}

# dictionary for known manufacturers. currently only David Schmidt
# and Apple Computer are known. Apple Computer is a defined as a range
# from 1-31.
mfgs =     {17491: 'David Schmidt'}

# open SOS.DRIVER file to interrogate, then read first
# eight bytes and determine if file is actual SOS.DRIVER file.
# will be replaced with logic to read full disk images (PRODOS)
SOSfile = open(disk_img, 'rb')
filetype = readUnpack(8, type = 't')

if filetype == 'SOS DRVR':
    print "This is a proper SOS.DRIVER file."
else:
    print "This is not a proper SOS.DRIVER file"
    exit()

# read two bytes immediately after "SOS DRVR" to determine jump
# to first major driver. Print out what's found. Start a count of
# found major drivers for upcoming loop and initalize a list to
# hold driver dictionaries.
rel_offset = readUnpack(2, type = 'b')
#print "The first relative offset value is", rel_offset, hex(rel_offset)
drivers = 0
drivers_list=[]

# loop that determines beginning of all major drivers in this particular
# SOS.DRIVER file, logs the offsets into a dictionary for later use.
# for each driver found, we:
# 1. Jump past the bytes indicating the comment length.
# 2. Look at the next two bytes and determine if they are xFFFF.
# 3. If not, place offset in dictionary.
# 4. When FFFF is encountered, we've reached the end of all drivers.
loop = True
while loop :
    driver = {}
    SOSfile.seek(rel_offset,1)
    driver['comment_start'] = SOSfile.tell()
    rel_offset = readUnpack(2, type = 'b')
    if rel_offset == 0xFFFF:
        loop = False
    else :
        drivers_list.append(driver)
        SOSfile.seek(rel_offset,1)
        rel_offset = readUnpack(2, type = 'b')
        SOSfile.seek(rel_offset,1)
        rel_offset = readUnpack(2, type = 'b')

# utilizing the offsets found, we now push through each Device information
# Block to log information about a driver. Comments therein.

# first deal with comment length and comment text.
# comment length is two bytes (either the length in hex or 0x0000)
# log both to list/dictionary
for i in range(0,len(drivers_list)):
    SOSfile.seek(drivers_list[i]['comment_start'],0)
    comment_len = readUnpack(2, type = 'b')
    drivers_list[i]['comment_len'] = comment_len
    if comment_len != 0x0000:
        comment_txt = readUnpack(comment_len, type = 't')
        drivers_list[i]['comment_txt'] = comment_txt
    else:
        drivers_list[i]['comment_txt'] = 'None'

    # these two bytes are the intermediate offset value used to jump
    # to the next major driver. We skip here while going through the DIB.
    SOSfile.seek(2,1)

    # Officially, the link pointer is the beginning of the DIB.
    # comments are optional. We log dib_start to indicate where the
    # actual DIB for a driver begins.
    drivers_list[i]['dib_start'] = SOSfile.tell()

    # the link pointer is two bytes and points to the next DIB
    # when there are multiples -- .D1, .D2, etc.
    link_ptr = readUnpack(2, type = 'b')
    drivers_list[i]['link_ptr'] = link_ptr

    # entry field is two bytes pointing to the area in memory
    # where the driver is placed during SOS bootup.
    entry = readUnpack(2, type = 'b')
    drivers_list[i]['entry'] = entry

    # the name length and name are next. Name length is one byte.
    # name field is _always_ 15 bytes long but name can be anything
    # up to 15 bytes
    name_len = readUnpack(1, type = '1')
    drivers_list[i]['name_len'] = name_len
    name = readUnpack(name_len, type = 't')
    drivers_list[i]['name'] = name
    SOSfile.seek(15 - name_len,1)

    # flag byte determine whether a driver is active, inactive
    # or shall be loaded on a page boundary. This is set up in
    # the System Configuration Program
    flag = readUnpack(1, type = '1')
    if flag == 192:
        drivers_list[i]['flag'] = 'ACTIVE, Load on Boundary'
    elif flag == 128:
        drivers_list[i]['flag'] = 'ACTIVE'
    else:
        drivers_list[i]['flag'] = 'INACTIVE'

    # if the driver is for a card that is loaded into a slot
    # and that slot has been defined in the SCP and placed into
    # the current SOS.DRIVER file, we log it here.
    slot_num = readUnpack(1, type = '1')
    if slot_num == 0:
        drivers_list[i]['slot_num'] = 'None'
    else:
        drivers_list[i]['slot_num'] = slot_num

    # the unit byte is concerned with the device number encountered.
    # for the major drivers, it's always 0 and if there are other
    # DIBs, such as for a driver that supports multiple disk drives,
    # the unit byte is incremented each time by 1.
    unit = readUnpack(1, type = '1')
    drivers_list[i]['unit'] = unit

    # dev_type is the type of device. We currently use a dict
    # and populate the field accordingly. This dictionary was
    # built from Apple's published Driver Writer's Manual.
    # The type is determined via two bytes. The LSB is the sub-type
    # and the MSB is the type.
    dev_type = readUnpack(2, type ='b')
    try:
        drivers_list[i]['dev_type'] = dev_types[dev_type]
    except:
        drivers_list[i]['dev_type'] = 'Unknown'

    # we skip the Filler byte ($19) as Apple reserved it.
    SOSfile.seek(1,1)

    # block_num refers to the number of logical blocks in a device
    # it is not guaranteed to be populated with anything
    # we log the block number defined or that the the device is
    # a character device. otherwise Undefined
    block_num = readUnpack(2, type = 'b')
    if block_num != 0:
        drivers_list[i]['block_num'] = block_num
    else:
        drivers_list[i]['block_num'] = 'Character Device or Undefined'

    # the manufacturer byte was ill-defined at the time the driver
    # writer's manual was published. 1 through 31 were reserved for
    # Apple Computer. Others were supposed to get their codes from
    # Apple. At the time we wrote this script, we used Apple devices
    # and the CFFA3000 and populated a dictionary. This dictionary
    # will get more k/v pairs as time goes on.
    mfg = readUnpack(2, type = 'b')
    try:
        drivers_list[i]['mfg'] = mfgs[mfg]
    except:
        if 1 <= mfg <= 31:
            drivers_list[i]['mfg'] = 'Apple Computer'
        else:
            drivers_list[i]['mfg'] = hex(mfg)

    # version bytes are integer values stored across two bytes.
    # a nibble corresponds to a major version number, one of two minor
    # version numbers, or a "further qualification" as Apple
    # called it. The format is V-v0-v1-Q. Q was not well-defined.
    # Basically if the value is 0xA, 0xB, or 0xE, then the Q
    # corresponds to: Alpha, Beta, and Experimental. Otherwise,
    # Q is merely a number. Q was worked out via the SCP.
    ver_byte0 = readUnpack(1, type = '1')
    ver_byte1 = readUnpack(1, type = '1')
    V   = nibblize(ver_byte1, direction = 'high')
    v0  = nibblize(ver_byte1, direction = 'low')
    v1  = nibblize(ver_byte0, direction = 'high')
    Q   = nibblize(ver_byte0, direction = 'low')
    if Q == '10':
        drivers_list[i]['version'] = V + '.' + v0 + v1 + ' Alpha'
    elif Q == '11':
        drivers_list[i]['version'] = V + '.' + v0 + v1 + ' Beta'
    elif Q == '14':
        drivers_list[i]['version'] = V + '.' + v0 + v1 + ' Experimental'
    else:
        drivers_list[i]['version'] = V + '.' + v0 + v1

# here we run a new loop to determine how many other DIBs exist
# under a major driver. This is primarily for drivers that are designed
# to support more than one device. for instance, the CFFA3000 is
# written to support seven drives (.D1 - .D7). otherwise, nothing
# else changes save the unit number, which is incremented by 1 for
# each device supported.
# generally we enter each major drive DIB and look at the link field.
# if the link field is not 0000, we know there are other DIBs.
# we can open up a new loop to run through the interior DIBs until
# we encount a 0000 in a link field, then we stop.
for i in range(0,len(drivers_list)):
    link_ptr = drivers_list[i]['link_ptr']
    total_devs = 1
    if link_ptr != 0x0000:
        SOSfile.seek(drivers_list[i]['dib_start'],0)
        SOSfile.seek(drivers_list[i]['link_ptr'],1)
        sub_loop = True
        while sub_loop:
            sub_link = readUnpack(2, type = 'b')
            if sub_link != 0x0000:
                total_devs = total_devs + 1
                SOSfile.seek(32,1)
            else:
                sub_loop = False
    drivers_list[i]['num_devices'] = total_devs

# closing the SOS.DRIVER file
SOSfile.close()

# here begins writing out the CSV file. the order is mainly
# structured like the structure in the Driver Writer's Manual.
# first, check if file exists and, if so, omit header
exists = os.path.exists(output_csv)
if exists == False:
    csvout = open(output_csv, 'w')
    csvout.write('output_csv,comment_start,comment_len,comment_txt,\
    dib_start,link_ptr,entry,name_len,name,flag,slot_num,num_devices,unit,\
    dev_type,block_num,mfg,version\n')
else:
    csvout = open(output_csv, 'a')

for i in range(0,len(drivers_list)):
    csvout.write(output_csv + ',' + \
    hex(drivers_list[i]['comment_start']) + ',' + \
    hex(drivers_list[i]['comment_len']) + ',' + \
    drivers_list[i]['comment_txt'] + ',' + \
    hex(drivers_list[i]['dib_start']) + ',' + \
    hex(drivers_list[i]['link_ptr']) + ',' + \
    hex(drivers_list[i]['entry']) + ',' + \
    hex(drivers_list[i]['name_len']) + ',' + \
    drivers_list[i]['name'] + ',' + \
    '"' + drivers_list[i]['flag'] + '"' + ',' + \
    str(drivers_list[i]['slot_num']) + ',' + \
    str(drivers_list[i]['num_devices']) + ',' + \
    str(drivers_list[i]['unit']) + ','  + \
    '"' + drivers_list[i]['dev_type'] + '"' + ',' + \
    str(drivers_list[i]['block_num']) + ',' + \
    drivers_list[i]['mfg'] + ',' + \
    str(drivers_list[i]['version'])
    )
    csvout.write('\n')
csvout.close()
