一个基于Django的电商网站。

网站名：dailyfresh
框架：Django
用途：学习交流
语言：python3
依赖包：见dailyfresh_freeze.txt
开发环境：ubuntu18.04
完成功能：用户注册系统，商品显示与搜索，购物车，订单系统，第三方支付
使用工具：nginx, fastdfs, celery, redis, mysql, uWSGI
部署：使用nginx负载均衡服务器处理分发动态请求给uWSGI服务器(其与Django服务器使用WSGI交互)，使用nginx处理图片/静态页面/静态文件(/static路径下的所有文件)


