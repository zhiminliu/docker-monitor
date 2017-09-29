# docker-monitor
docker-monitor docker api monitor 
#注意只适用于python2.7(因为tornado版本的原因,python2.6或许会报错)
#NO.1 在数据库建库(直接复杂就OK了)
  CREATE DATABASE `docker_admin` /*!40100 DEFAULT CHARACTER SET utf8 */;
#NO.2 创建表(直接导进入就好了docker_admin.sql)
  mysql -uroot -h127.0.0.1 docker_admin < docker_admin.sql (数据库的地址,端口密码,因环境不一样,大家改下即可)
#NO.3 安装依赖包
  pip install mysql;pip install tornado;pip install docker-py;
#NO.4 修改默认端口,数据库的配置
  vim ws_app.py
        #数据库的配置
            self.ip='dbhost'#数据库ip
            self.user='root'#数据库用户
            self.passwd='123456'#数据库密码
            self.dbs='docker_admin'#数据库库名
        #默认端口
            把 server.listen(8011) 中的8011 改成您需要的端口
#NO.5 启动
  python ws_app.py
