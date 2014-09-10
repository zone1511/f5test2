{% extends "base.tpl" %}
{% block ictester_active %}active{% endblock %}

{% block title %}iControl Tester{% endblock %}

{% block description %}
     <h2>iControl Tester</h2>
     <p>Test any iControl method quick and easy. Click on the dotted links to edit values.
     Arguments: may be passed one per line (in Python syntax), strings with no whitespace don't need quotes.
     </p>
     <p>For more information about iControl API visit the <a href="http://172.27.32.101/tier2/iControl-11.6.0/sdk/api_reference/iControl.html" target="_blank">online SDK</a>.</p>
{% endblock %}

{% macro options() %}
                <table id="options" class="table table-bordered table-striped" style="clear: both">
                    <tbody> 
                        <tr>         
                            <td width="15%">Address</td>
                            <td width="50%"><a href="#" id="address" data-bind="editable: inputs.address" data-type="text" data-original-title="Enter device's address"></a><a href="#" target="_blank" data-bind="visible: inputs.address, attr: { href: open_url }"><span class="label label-info">Open <i class="icon-share-alt icon-white"></i></span></a></td>
                            <td width="35%"><span class="muted">Device IP address</span></td>
                        </tr>
                        <tr>
                            <td>Password</td>
                            <td><a href="#" id="password" data-bind="editable: inputs.password" data-type="text" data-original-title="Enter admin password"></a></td>
                            <td><span class="muted">admin password</span></td>
                        </tr>
                        <tr>
                            <td>Method</td>
                            <td><a href="#" id="method" data-bind="editable: inputs.method" data-type="text" data-inputclass="input-xlarge" data-original-title="Enter method to be called"></a></td>
                            <td><span class="muted">iControl Module.Interface.method</span></td>
                        </tr>
                        <tr>
                            <td>Arguments</td>
                            <td><a href="#" id="arguments" data-bind="editable: inputs.arguments" data-type="textarea" data-inputclass="input-xxlarge code" data-original-title="Enter method arguments"></a></td>
                            <td><span class="muted">Method's arguments</span></td>
                        </tr>
                    </tbody>
                </table>
{% endmacro %}

{% block content %}
            <ul class="nav nav-tabs">
                <li class="active"><a href="#main" data-toggle="tab"><i class="icon-cog"></i>Options</a></li>
            </ul>
            
            <div class="tab-content">
                <div class="tab-pane active fade in" id="main">
                    {{ options() }}
                </div>

                <div style="padding-right: 5px; padding-bottom: 20px;">
                    <button id="start-btn" data-bind="click: start, disable: isRunning()" class="btn btn-primary"><i class="icon-white" data-bind="css: isRunning() ? 'icon-time' : 'icon-play'"></i> <span data-bind="text: isRunning() ? 'Processing...' : 'Start'"></span></button>
                    <button id="stop-btn" data-bind="click: stop, visible: isRunning()" class="btn btn-danger"><i class="icon-stop icon-white"></i> Stop!</button>
                    <!--button id="stop-btn" data-bind="click: toggleEditable, visible: task_id() && !isRunning()" class="btn">Edit</button-->
    
                    <div id="status" class="pull-right">
                        <div data-bind="css: getStatusCss, attr: { title: status }" class="status-icon"></div>
                    </div>
                </div>

			    <div class="container console collapse in">
                    <span data-bind="visible: isError()" class="label label-important pull-right">Error</span>
			        <span data-bind="visible: isSuccess()" class="label pull-right">Response</span>
			        <pre data-bind="visible: isError()" class="code"><code data-bind="text: traceback" class="python"></code></pre>
			        <pre data-bind="visible: isSuccess()" class="code"><code style="min-height: 0" data-bind="text: value"></code></pre>
			    </div>
    
            </div>
{% endblock %}


{% block js %}
    <script src="/media/app.tester_icontrol.js"></script>
    <script src="/media/highlight.js/highlight.pack.js"></script>
{% endblock %}
