#-*- encoding:utf-8 -*-  
#author: zhiminliu
  
import tornado.web  
import tornado.websocket  
import tornado.httpserver  
import tornado.ioloop  
#import paramiko
import time
#import socket
import sys
#import threading
import Queue
import json
import MySQLdb
import MySQLdb.cursors
#from threading import Thread
import threading
from docker import Client



class mysql_cmd():
    def __init__(self):
        #self.ip='192.168.235.94'
        self.ip='dbhost'#数据库ip
        #self.user='root'
        self.user='user'#数据库用户
        #self.passwd='biostime123'    
        self.passwd='123456'#数据库密码
        #self.dbs='docker_admin'
        self.dbs='docker_admin'#数据库库名
        self.db=MySQLdb.connect(self.ip,self.user,self.passwd,self.dbs,charset="utf8",cursorclass=MySQLdb.cursors.DictCursor)
        self.cursor=self.db.cursor()
    def select_cmd(self,sql):
        try:
            self.cursor.execute(sql)
            results=self.cursor.fetchall()
        except:
            results=''
            print "error: unable to fetch data"
        #self.db.close()
        return results
    def run_cmd(self,sql):
        try:
            self.cursor.execute(sql)
        except:
            print "error:unable to insert data"
        self.db.close()
    def run_close(self):
        self.db.close()

class webhot(threading.Thread):
    def __init__(self,queue):
        threading.Thread.__init__(self)
        self.queue=queue
    def run(self):
        while True:
            if self.queue.empty():
                break
            #print self.queue.get()
            cli_obj=self.queue.get()
            stamp=int(time.time())
            datetime=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            cli=cli_obj["cli"]
            Id=cli_obj["Id"]
            ip=cli_obj["ip"]
            #print Id,ip
            try:
                status=cli_obj["status"]
                if status == "up":
                    container_collect=cli.stats(Id)
                    old_result=json.loads(container_collect.next())
                    time.sleep(2)
                    new_result=json.loads(container_collect.next())
                    container_collect.close()
                    cpu_total_usage=new_result['cpu_stats']['cpu_usage']['total_usage'] - old_result['cpu_stats']['cpu_usage']['total_usage']
                    cpu_system_uasge=new_result['cpu_stats']['system_cpu_usage'] - old_result['cpu_stats']['system_cpu_usage']
                    cpu_num=len(old_result['cpu_stats']['cpu_usage']['percpu_usage'])
                    cpu_percent=round((float(cpu_total_usage)/float(cpu_system_uasge))*cpu_num*100.0,2)
                    mem_usage=new_result['memory_stats']['usage']
                    mem_limit=new_result['memory_stats']['limit']
                    mem_percent=round(float(mem_usage)/float(mem_limit)*100.0,2)

                else:
                    pass
            except Exception,ex:
                cpu_percent="0"
                mem_percent="0"
            try:
                mysql_obj=mysql_cmd()
                sql="insert into docker_status (ip,container_id,status,cpu_percent,mem_percent,network,stamp,time) values ('%s','%s','%s','%s','%s','%s','%s','%s')"%(ip,Id,status,cpu_percent,mem_percent,'',stamp,datetime)
                mysql_obj.run_cmd(sql)
            except Exception,ex:
                pass

class MyThread(threading.Thread):  
    def __init__(self):  
        threading.Thread.__init__(self)  
    def run(self):  
        while True:
            mysql_obj=mysql_cmd()
            sql="select ip,port from machine_info where status='监控'"
            machine_obj=mysql_obj.select_cmd(sql)
            mysql_obj.run_close()
            queue=Queue.Queue()
            for i in machine_obj:
                try:
                    cli=Client(base_url='tcp://%s:%s'%(i["ip"],i["port"]), version='auto',timeout=60)
                    containers_obj=cli.containers(all=True)
                    for ii in containers_obj:
                        if 'Up' in ii["Status"]:
                            status="up"
                        else:
                            status="exit"
                        Id=ii["Id"]
                        ip=i["ip"]
                        cli_obj={"cli":cli,"Id":Id,"status":status,"ip":ip}
                        queue.put(cli_obj)
                    for i in range(0,10):
                        Threadclass=webhot(queue)
                        Threadclass.start()
                except Exception,ex:                    
                    #print i
                    print str(ex)
            time.sleep(60)

class index(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')  
    
    def post(self):  
        ##获取参数
        self.render('index.html')

class containers_status(tornado.web.RequestHandler):
    def get(self):
        action=self.get_argument("action")
        ip=self.get_argument("ip")
        container_id=self.get_argument("container_id")
        if action == "select":
            mysql_obj=mysql_cmd()
            machine_obj=mysql_obj.select_cmd('select ip from machine_info')
            if ip != "":
                sql="SELECT container_id FROM docker_status WHERE ip='%s' GROUP BY container_id;"%(ip)
                container_obj=mysql_obj.select_cmd(sql)
                mysql_obj.run_close()
            else:
                sql="SELECT container_id FROM docker_status WHERE ip=(SELECT ip FROM machine_info LIMIT 1) GROUP BY container_id;"
                container_obj=mysql_obj.select_cmd(sql)
                mysql_obj.run_close()
            self.render('containers_status.html',machine_obj=machine_obj,container_obj=container_obj,ip=ip,container_id=container_id)

class machine_info(tornado.web.RequestHandler):
    def get(self):
        action=self.get_argument("action")
        #arg_obj=self.request.arguments
        #action=arg_obj["action"][0]
        if action == "select":
            mysql_obj=mysql_cmd()    
            machine_obj=mysql_obj.select_cmd('select * from machine_info')
            mysql_obj.run_close()
            self.render('machine_info.html',machine_obj=machine_obj)
        elif action == "add":
            machine_json={'status': '', 'area': '', 'ip': '', 'id': '', 'remarks': '', 'port': ''}
            self.render('machine_edit.html',machine_json=machine_json,sid='0')
        elif action == "update":
            sid=self.get_argument("sid")
            mysql_obj=mysql_cmd()
            sql="select * from machine_info where id=%s"%(sid)
            machine_obj=mysql_obj.select_cmd(sql)
            mysql_obj.run_close()
            machine_json=machine_obj[0]
            self.render('machine_edit.html',machine_json=machine_json,sid=sid)
        elif action == "delete":
            sid=self.get_argument("sid")
            mysql_obj=mysql_cmd()
            sql="DELETE FROM machine_info WHERE id=%s;"%(sid)
            mysql_obj.run_cmd(sql)
            self.redirect("machine_info?action=select")
        else:
            self.render('machine_info.html')
    def post(self):
        ##获取参数
        if self.get_argument("action") == "edit":
            area=self.get_argument("area")
            ip=self.get_argument("ip")
            port=self.get_argument("port")
            status=self.get_argument("status")
            remarks=self.get_argument("remarks")
            mysql_obj=mysql_cmd()
            sid=self.get_argument("sid")            
            if sid == "0":
                sql="insert into machine_info (area,ip,port,status,remarks) values ('%s','%s','%s','%s','%s')"%(area,ip,port,status,remarks)
            else:
                sql="UPDATE  machine_info SET area='%s',ip='%s',port='%s',status='%s',remarks='%s' where id=%s;"%(area,ip,port,status,remarks,sid)
            mysql_obj.run_cmd(sql)
            self.redirect("machine_info?action=select")

class monitor_info(tornado.web.RequestHandler):
    def get(self):
        if self.get_argument("action") == "monitor":
            container_id=self.get_argument("container_id")
            datetime=self.get_argument("datetime")
            sql="SELECT stamp,cpu_percent,mem_percent FROM docker_status WHERE container_id='%s'"%(container_id)
            mysql_obj=mysql_cmd()
            container_obj=mysql_obj.select_cmd(sql)
            mysql_obj.run_close()
            data_json={}
            data_json["mem_percent"]=[]
            data_json["cpu_percent"]=[]


            for i in container_obj:
                try:
                    stamp=(int(i["stamp"])+28800)*1000
                    data_json["cpu_percent"].append([stamp,float(i["cpu_percent"])])
                    data_json["mem_percent"].append([stamp,float(i["mem_percent"])])
                except Exception,ex:
                    #print str(ex)
                    pass

            self.write(json.dumps(data_json))
        
class Application(tornado.web.Application):  
    def __init__(self):  
        handlers = [  
            (r'/',index),
            (r'/machine_info',machine_info),
            (r'/containers_status',containers_status),
            (r'/monitor',monitor_info),
        ]  
  
        settings = { "template_path": ".","static_path": "static","cookie_secret": "bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=","login_url":"/"}  
        tornado.web.Application.__init__(self, handlers, **settings)  
  
if __name__ == '__main__':  
    ws_app = Application()  
    server = tornado.httpserver.HTTPServer(ws_app)  
    server.listen(8011)
    #DaemonThread.instance().start()
    t1=MyThread()
    t1.setDaemon(True)
    t1.start() 
    tornado.ioloop.IOLoop.instance().start()  
  
''''' 
python ws_app.py 
'''  

