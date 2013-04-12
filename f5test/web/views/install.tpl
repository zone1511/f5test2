{% extends "base.tpl" %}
{% block install_active %}active{% endblock %}

{% block title %}Install{% endblock %}

{% block description %}
     <h2>Install</h2>
     <p>Install a build on a TMOS based device. Click on the dotted links to edit values. Check out the console tab for any log messages.</p>
{% endblock %}

{% block options %}
                <table id="options" class="table table-bordered table-striped" style="clear: both">
                    <tbody> 
                        <tr>         
                            <td width="15%">Address</td>
                            <td width="50%" colspan="2"><a href="#" id="address" data-bind="editable: inputs.address" data-type="text" data-original-title="Enter device's IP address"></a><a href="#" target="_blank" data-bind="visible: inputs.address, attr: { href: open_url }"><span class="label label-info">Open <i class="icon-share-alt icon-white"></i></span></a></td>
                            <td width="35%"><span class="muted">Device IP address</span></td>
                        </tr>
                        <tr>
                            <td>Admin Password</td>
                            <td colspan="2"><a href="#" id="admin_password" data-bind="editable: inputs.admin_password" data-type="text" data-original-title="Enter admin password"></a></td>
                            <td><span class="muted">admin user password</span></td>
                        </tr>
                        <tr>
                            <td>Root Password</td>
                            <td colspan="2"><a href="#" id="root_password" data-bind="editable: inputs.root_password" data-type="text" data-original-title="Enter root password"></a></td>
                            <td><span class="muted">root user password</span></td>
                        </tr>
                        <tr>
                            <td>Configuration</td>
                            <td colspan="2">
                                <a href="#" id="config" class="hide" data-bind="editable: inputs.config" data-type="select" data-original-title="Roll forward configuration?"></a>
	                            <div>
	                                <button type="button" class="btn btn-mini" data-bind="toggle: inputs.config() == 'essential', click: function(){ inputs.config('essential') }">clean</button>
	                                <button type="button" class="btn btn-mini" data-bind="toggle: !inputs.config(), click: function(){ inputs.config('') }">roll forward</button>
	                            </div>                            
                            </td>
                            <td><span class="muted">Configuration roll forward or not</span></td>
                        </tr>
                        <tr>
                            <td>Product</td>
                            <td colspan="2">
                                <a href="#" id="product" class="hide" data-bind="editable: inputs.product" data-type="select" data-original-title="Select product"></a>
	                            <div>
					                <button type="button" class="btn btn-mini" data-bind="toggle: inputs.product() == 'bigiq', click: function(){ inputs.product('bigiq'); inputs.version('bigiq-mgmt') }">BIG-IQ</button>
					                <button type="button" class="btn btn-mini" data-bind="toggle: inputs.product() == 'em', click: function(){ inputs.product('em'); inputs.version('3.1.1') }">EM</button>
					                <button type="button" class="btn btn-mini" data-bind="toggle: inputs.product() == 'bigip', click: function(){ inputs.product('bigip'); inputs.version('corona-bugs') }">BIG-IP</button>
	                            </div>                            
                            </td>
                            <td><span class="muted">Product to be installed</span></td>
                        </tr>
                        <tr>
                            <td rowspan="3">Specifications</td>
                            <td width="10%">Version</td><td><a href="#" id="version" data-bind="editable: inputs.version" data-type="text" data-original-title="Enter version or project name"></a></td>
                            <td rowspan="3"><span class="muted">Examples:<br>11.3.0, HF3<br>10.2.4, ENG, 577.30<br>corona-bugs, none, TC</span></td>
                        </tr>
                        <tr>
                            <td>Hotfix</td><td><a href="#" id="hotfix" data-bind="editable: inputs.hotfix" data-type="text" data-emptytext="none" data-original-title="Enter hotfix identifier (e.g. HF1 or ENG)"></a></td>
                        </tr>
                        <tr>
                            <td>Build</td><td><a href="#" id="build" data-bind="editable: inputs.build" data-type="text" data-emptytext="latest" data-original-title="Enter build number, BOTD or TC"></a></td>
                        </tr>
                        <tr>
                            <td>ISO</td>
                            <td colspan="2"><a href="#" id="customiso" data-bind="editable: inputs.customiso" data-type="text" data-inputclass="input-xxlarge" data-original-title="Enter the full path to an ISO file"></a></td>
                            <td><span class="muted">Provide a custom ISO file as base image</span></td>
                        </tr>
                        <tr>
                            <td>Disk Format</td>
                            <td colspan="2">
                                <a href="#" id="format" class="hide" data-bind="editable: inputs.format" data-type="select" data-original-title="Choose disk format scheme"></a>
                                <div>
                                    <button type="button" class="btn btn-mini" data-bind="toggle: !inputs.format(), click: function(){ inputs.format('') }">unchanged</button>
                                    <button type="button" class="btn btn-mini" data-bind="toggle: inputs.format() == 'volumes', click: function(){ inputs.format('volumes') }">volumes</button>
                                    <button type="button" class="btn btn-mini" data-bind="toggle: inputs.format() == 'partitions', click: function(){ inputs.format('partitions') }">partitions</button>
                                </div>                            
                            </td>
                            <td><span class="muted">Perform a disk re-initialization prior to installation</span></td>
                        </tr>

                    </tbody>
                </table>
{% endblock %}

{% block head %}
{% endblock %}

{% block js %}
    <script src="/media/app.install.js"></script>
{% endblock %}
