#!/usr/bin/env python
#-*- coding: utf-8 -*-

from os import path,makedirs,kill
from time import sleep
import subprocess
import re
import datetime


BaseDir=path.dirname(path.realpath(__file__))
httptimeout=1
pingMaxRTT=30
GlobalSleepInterval=10
NICName='ens33'


def parseHttpLog():
    ### 检查HTTP 记录，如果HTTP 请求正常返回True,否则False
    TmpFileContent=''
    with open(path.join(BaseDir, 'tmp', 'http.log'), mode='rb') as f:
        TmpFileContent=f.read()

    ReObj=re.search('time_total:\s*(.*?)\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
    if  ReObj:
        TmpHttpResponseElapse=float(ReObj.group(1))
        if TmpHttpResponseElapse>=httptimeout:
            return False
    return True

def parsePingLog():
    ### 检查 ICMP 日志,正常返回True,否则False ###

    isNetworkGood=True
    TmpMaxRTT=0

    TmpFile=open(path.join(BaseDir, 'tmp', 'ping.log'), mode='r')
    for line in TmpFile:
        if 'packets' in line:
            ReObj=re.search(r'(.*?)\s+packets.*?,\s+(.*?)\s+received.*?\n',line,flags=re.UNICODE|re.MULTILINE)
            TmpSent=int(ReObj.group(1).strip())
            TmpReceived=int(ReObj.group(2).strip())
            if TmpReceived<TmpSent:
                print ('ICMP lost packets')
                isNetworkGood=False
            continue

        if 'rtt'  in line:
            ReObj=re.search(r'^.*?=(.*?)ms',line)
            TmpMaxRTT=float(ReObj.group(1).strip().split('/')[2])
            if TmpMaxRTT>=pingMaxRTT:
                isNetworkGood=False
            print ('Max rtt is '+str(TmpMaxRTT))
            break
    TmpFile.close()
    return isNetworkGood




class TcpdumpProcess:
    def __init__(self,TmpTcpdumpExec='/usr/sbin/tcpdump', TmpNICName=NICName):
        self.TcpdumpExec=TmpTcpdumpExec
        self.NICName=TmpNICName

    def start(self):
        if not path.isdir(path.join(BaseDir, 'tmp')):
            makedirs(path.join(BaseDir, 'tmp'))

        TmpCmd=self.TcpdumpExec+' -vvvv -U -i '+self.NICName+' -w '+path.join(BaseDir, 'tmp', 'tcpdump.log')
        self.Pobj=subprocess.Popen(TmpCmd.split(), stderr=subprocess.PIPE)

    def stop(self):
        print ('killing TCPDUMP process....')
        kill(self.Pobj.pid, 9)
        self.Pobj.wait()

        del self.Pobj


class PingProcess:
    def __init__(self,TmpPingExec='/usr/bin/ping',TmpIPAddr=None):
        self.PingExec=TmpPingExec
        self.IPaddr=TmpIPAddr

    def start(self):
        if not path.isdir(path.join(BaseDir, 'tmp')):
            makedirs(path.join(BaseDir, 'tmp'))

        TmpCmd=self.PingExec+' -i 0.01   '+self.IPaddr
        print (TmpCmd)

        self.TmpOutputFileObj=open(path.join(BaseDir, 'tmp', 'ping.log'), mode='wb')
        self.Pobj=subprocess.Popen(TmpCmd.split(), stdout=self.TmpOutputFileObj)


    def stop(self):
        print ('killing PING process....')
        kill(self.Pobj.pid, 2)
        self.Pobj.wait()

        self.TmpOutputFileObj.close()
        del self.Pobj


class HttpProcess:
    def __init__(self,TmpUrl, TmpCurlExec='/usr/bin/curl', TmpTimeout=60):
        self.URL=TmpUrl
        self.Timeout=TmpTimeout
        self.CURLExec=TmpCurlExec

    def start(self):
        if not path.isdir(path.join(BaseDir, 'tmp')):
            makedirs(path.join(BaseDir, 'tmp'))


        TmpCmd=self.CURLExec+' -w @'+str(path.join(BaseDir, 'conf', 'format.txt'))+' -o /dev/null --max-time '\
               +str(self.Timeout)+' -s '+self.URL
        self.Pobj=subprocess.Popen(TmpCmd.split(), stdout=subprocess.PIPE)

        with open(path.join(BaseDir, 'tmp', 'http.log'), mode='wb') as f:
            f.write(self.Pobj.stdout.read())
        print (self.Pobj.stdout.read())

    def stop(self):
        print ('killing CURL process....')
        kill(self.Pobj.pid, 9)
        self.Pobj.wait()


        del self.Pobj

while True:
    TmpCurrentTimeStamp=datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    print ('\n'+'Current time is '+TmpCurrentTimeStamp+'\n')
    #### 构造实例 ###
    TcpdumpObj=TcpdumpProcess()
    PingObj=PingProcess(TmpIPAddr='www.baidu.com')
    HttpObj=HttpProcess(TmpUrl='www.baidu.com')

    ###
    TcpdumpObj.start()
    PingObj.start()
    HttpObj.start()

    HttpObj.stop()
    del HttpObj

    PingObj.stop()
    del PingObj

    TcpdumpObj.stop()
    del TcpdumpObj

    HttpResult=parseHttpLog()
    PingResult=parsePingLog()

    if (not HttpResult) or (not PingResult):
        if not path.isdir(path.join(BaseDir, 'logs')):
            makedirs(path.join(BaseDir, 'logs'))
        print ('generate logs folder....')
        TmpCmd='mv '+path.join(BaseDir, 'tmp')+' '+path.join(BaseDir, 'logs', TmpCurrentTimeStamp)
        subprocess.Popen(TmpCmd, shell=True)
        sleep (GlobalSleepInterval)
