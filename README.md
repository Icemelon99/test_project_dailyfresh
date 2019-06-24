**基于Django的电商网站**

网站名：dailyfresh  
框架：Django  
用途：学习交流  
语言：python3  
依赖包：见dailyfresh_freeze.txt  
开发环境：ubuntu18.04  
完成功能：用户注册系统，商品显示与搜索，购物车，订单系统，第三方支付  
使用工具：nginx, fastdfs, celery, redis, mysql, uWSGI  
开发博客：参[学习笔记](https://me.csdn.net/weixin_44806420)  
部署：使用nginx负载均衡服务器处理分发动态请求给uWSGI服务器(其与Django服务器使用WSGI交互)，使用nginx处理图片/静态页面/静态文件(/static路径下的所有文件)，部署架构如下  
![text](https://img-blog.csdnimg.cn/20190617160131250.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3dlaXhpbl80NDgwNjQyMA==,size_16,color_FFFFFF,t_70)
