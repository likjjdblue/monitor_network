#!/usr/bin/env python
#-*- coding: utf-8 -*-

from os import path,makedirs,kill
from time import sleep
import subprocess
import re
import datetime

###被监控的URL 响应时间阀值（单位：秒）
MaxHttpResponseTime=1

###   被监控的HTTP URL 地址 ####
MonitorURL='www.baidu.com'

### ping 最大响应时间阀值(单位：毫秒)
PingMaxRTT=30

###  PING 对端地址（IP ，域名都可以）
PingAddr='www.baidu.com'

###  被TCPDUMP 抓包的网卡名称 (只能配置单个网卡)
NICName='ens33'


GlobalSleepInterval=10




BaseDir=path.dirname(path.realpath(__file__))
GlobalLogFile=open(path.join(BaseDir, 'running.log'), mode='ab',buffering=0)

def parseHttpLog():
    ### 检查HTTP 记录，如果HTTP 请求正常返回True,否则False
    TmpFileContent=''
    with open(path.join(BaseDir, 'tmp', 'http.log'), mode='rb') as f:
        TmpFileContent=f.read()

    ReObj=re.search('time_total:\s*(.*?)\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
    if  ReObj:
        TmpHttpResponseElapse=float(ReObj.group(1))
        if TmpHttpResponseElapse>=MaxHttpResponseTime:
            print ('Http 响应时间异常! '+str(TmpHttpResponseElapse))
            GlobalLogFile.write('Http 响应时间异常! '+str(TmpHttpResponseElapse)+'\n')
            return False

    if path.isfile(path.join(BaseDir, 'tmp', 'http_error.log')):
        print ('Http 请求过程发生异常！')
        GlobalLogFile.write('Http 请求过程发生异常！'+'\n')
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
                isNetworkGood=False
                GlobalLogFile.write('PING 存在丢包情况'+'\n')
                print ('PING 存在丢包情况')
            continue

        if 'rtt'  in line:
            ReObj=re.search(r'^.*?=(.*?)ms',line)
            TmpMaxRTT=float(ReObj.group(1).strip().split('/')[2])
            if TmpMaxRTT>=PingMaxRTT:
                isNetworkGood=False
                GlobalLogFile.write('PING 最大响应时间过大'+'\n')
                print ('PING 最大响应时间过大')
            break
    TmpFile.close()
    return isNetworkGood




class TcpdumpProcess:
    def __init__(self,TmpTcpdumpExec='/usr/sbin/tcpdump', TmpNICName=None):
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
    def __init__(self,TmpUrl=None, TmpCurlExec='/usr/bin/curl', TmpTimeout=60):
        self.URL=TmpUrl
        self.Timeout=TmpTimeout
        self.CURLExec=TmpCurlExec

    def start(self):
        if not path.isdir(path.join(BaseDir, 'tmp')):
            makedirs(path.join(BaseDir, 'tmp'))


        TmpCmd=self.CURLExec+' -w @'+str(path.join(BaseDir, 'conf', 'format.txt'))+' -o /dev/null --max-time '\
               +str(self.Timeout)+' -s -S '+self.URL
        self.Pobj=subprocess.Popen(TmpCmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        with open(path.join(BaseDir, 'tmp', 'http.log'), mode='wb') as f:
            f.write(self.Pobj.stdout.read())
        print (self.Pobj.stdout.read())

        TmpCurlErrorContent=self.Pobj.stderr.read()
        if len(TmpCurlErrorContent):
            with open(path.join(BaseDir, 'tmp', 'http_error.log'), mode='wb') as f:
                f.write(TmpCurlErrorContent)

    def stop(self):
        print ('killing CURL process....')
        kill(self.Pobj.pid, 9)
        self.Pobj.wait()


        del self.Pobj

while True:
    TmpCurrentTimeStamp=datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    GlobalLogFile.write('\n'+'Current time is '+TmpCurrentTimeStamp+'\n')
    print ('\n'+'Current time is '+TmpCurrentTimeStamp)
    #### 构造实例 ###
    TcpdumpObj=TcpdumpProcess(TmpNICName=NICName)
    PingObj=PingProcess(TmpIPAddr=PingAddr)
    HttpObj=HttpProcess(TmpUrl=MonitorURL)

    ### 启动实例 ####
    TcpdumpObj.start()
    sleep(3)
    PingObj.start()
    HttpObj.start()

    ###依次销毁实例 ###
    HttpObj.stop()
    del HttpObj

    PingObj.stop()
    del PingObj

    TcpdumpObj.stop()
    del TcpdumpObj

    ### 解析日志 ####
    HttpResult=parseHttpLog()
    PingResult=parsePingLog()

    if (not HttpResult) or (not PingResult):
        if not path.isdir(path.join(BaseDir, 'logs')):
            makedirs(path.join(BaseDir, 'logs'))
        GlobalLogFile.write('generate logs folder....'+'\n')
        print ('generate logs folder....')
        TmpCmd='mv '+path.join(BaseDir, 'tmp')+' '+path.join(BaseDir, 'logs', TmpCurrentTimeStamp)
        subprocess.Popen(TmpCmd, shell=True)
    print ('Pause for next round.....')
    GlobalLogFile.write('Pause for next round.....'+'\n')
    sleep (GlobalSleepInterval)
