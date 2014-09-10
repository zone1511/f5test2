<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <meta name="author" content="Ionut Turturica">
        <meta http-equiv="cache-control" content="max-age=0" />
        <meta http-equiv="cache-control" content="no-cache" />
        <meta http-equiv="expires" content="Tue, 01 Jan 1980 1:00:00 GMT" />
        <meta http-equiv="pragma" content="no-cache" />

        <title>{% block title %}{% endblock %} :: Shiraz</title>
    
        <link href="/media/bootstrap/css/bootstrap.css" rel="stylesheet">
        <script src="/media/jquery/jquery-1.11.0.min.js"></script>
        <script src="/media/bootstrap/js/bootstrap.min.js"></script>
        <script src="/media/spinjs/spin.min.js"></script>

        <script src="/media/knockoutjs/knockout-3.0.0.js"></script>
        <script src="/media/knockoutjs/knockout.x-editable.js"></script>
        <script src="/media/knockoutjs/knockout.validation.min.js"></script>
        <script src="/media/knockoutjs/knockout.app.min.js"></script>
        <script src="/media/knockoutjs/knockout.mapping-latest.js"></script>
        <script src="/media/sammyjs/sammy-0.7.4.min.js"></script>
        <link href="/media/highlight.js/styles/arta.css" rel="stylesheet">
        <link href="/media/css/app.css" rel="stylesheet">
    
        <link href="/media/bootstrap-editable/css/bootstrap-editable.css" rel="stylesheet">
        <script src="/media/bootstrap-editable/js/bootstrap-editable.min.js"></script>
        {% block head %}{% endblock %}
    </head>

    <body> 
		<div class="navbar xnavbar-inverse navbar-fixed-top">
		  <div class="navbar-inner">
		    <div class="container">
		        <a class="brand" href="/">
                  <img src="/media/css/Apps-wine-icon-big2.png" width="32" height="32"></img>
		          Shiraz
		        </a>
		        <ul class="nav">
		          <!-- <li class="{% block add_active %}{% endblock %}"><a href="/add">Demo</a></li>  -->
                  <li class="{% block install_active %}{% endblock %}"><a href="/install">Install</a></li>
                  <li class="{% block config_active %}{% endblock %}"><a href="/config">Configure</a></li>
                  <li class="{% block ictester_active %}{% endblock %}"><a href="/tester/icontrol">iCTester</a></li>
		          <li class="{% block bvt_active %}{% endblock %} dropdown">
		              <a href="#" class="dropdown-toggle" data-toggle="dropdown">BVT
		                  <b class="caret"></b>
		              </a>
		              <ul class="dropdown-menu">
		                  <li class=""><a href="/bvt/basic">BIG-IP: EM Request</a></li>
		                  <li class=""><a href="/bvt/bigiq">BIG-IP: BIG-IQ Request</a></li>
		                  <li class=""><a href="/bvt/deviso">BIG-IQ User Build Request</a></li>
		                  <li class="disabled"><a href="#">Advanced</a></li>
		              </ul>
		          </li>
		        </ul>
		    </div>
		  </div>
		</div>

        <div class="container"> 

            <header style="margin-top: 55px;">
	            {% block description %}{% endblock %}
            </header>
	
            <div id="success" class="alert alert-success fade in hide"><button type="button" class="close" data-dismiss="alert">×</button><span></span></div>
            <div id="info" class="alert alert-info fade in hide"><button type="button" class="close" data-dismiss="alert">×</button><span></span></div>
            <div id="validation" class="alert alert-error fade in hide"><button type="button" class="close" data-dismiss="alert">×</button><span></span></div>

            {% block content %}
            <ul class="nav nav-tabs">
                <li class="active"><a href="#main" data-toggle="tab"><i class="icon-cog"></i>Options</a></li>
                <li><a href="#console" data-toggle="tab"><i class="icon-align-justify"></i>Console</a></li>
            </ul>
            
            <div class="tab-content">
	            <div class="tab-pane active fade in" id="main">
	                {% block options %}{% endblock %}
	                <div style="padding-right: 5px;">
	                <button id="start-btn" data-bind="click: start, disable: isRunning()" class="btn btn-primary"><i class="icon-white" data-bind="css: isRunning() ? 'icon-time' : 'icon-play'"></i> <span data-bind="text: isRunning() ? 'Processing...' : 'Start'"></span></button>
	                <button id="stop-btn" data-bind="click: stop, visible: isRunning()" class="btn btn-danger"><i class="icon-stop icon-white"></i> Stop!</button>
	                <!--button id="stop-btn" data-bind="click: toggleEditable, visible: task_id() && !isRunning()" class="btn">Edit</button-->
	
	                <div id="status" class="pull-right">
	                    <div data-bind="css: getStatusCss, attr: { title: status }" class="status-icon"></div>
	                </div>
	                </div>
	            </div>

	            <div class="tab-pane fade" id="console">
	                <!--h3>Console <small data-bind="visible: status">(<span data-bind="text: status"></span>)</small></h3--> 
	                <!--div><textarea id="console" rows="8" style="width: 70%" autocomplete="off">{{ status or '' }}</textarea></div-->
	                
	                <pre class="code"><code data-bind="foreach: logs" class="logs javascript"><span data-bind="css: name"><span data-bind="text: timestamp"></span> <span data-bind="text: levelname, css: levelname"></span> <span data-bind="text: message"></span>
</span></code></pre>
	<pre data-bind="visible: isError()" class="code"><code data-bind="text: traceback" class="javascript"></code></pre>
	<pre data-bind="visible: isSuccess()" class="code"><code class="nginx" style="min-height: 0">Return value: <span data-bind="text: value" class="title"></span></code></pre>
	            </div>
            </div>
            {% endblock %}

        </div>
        <footer class="footer" style="clear: both; padding-top: 10px">
            <div class="container">
	            <p><a href="#">Home</a> &copy; 2013 F5 Networks, Inc. All rights reserved.</p> 
	            <p><small>Contact: <a href="mailto:i.turturica@f5.com?subject=Shiraz question">Ionut Turturica</a></small></p>
            </div> 
        </footer>
        
        <script src="/media/app.base.js"></script>
        {% block js %}{% endblock %}

    </body>

</html>
