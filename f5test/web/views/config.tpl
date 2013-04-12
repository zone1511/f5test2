{% extends "base.tpl" %}
{% block config_active %}active{% endblock %}

{% block title %}Configure{% endblock %}

{% block description %}
     <h2>Configure</h2>
     <p>Configure a TMOS based device. Click on the dotted links to edit values. Check out the console tab for any log messages.</p>
{% endblock %}

{% block options %}
                <table id="options" class="table table-bordered table-striped" style="clear: both">
                    <tbody> 
                        <tr>         
                            <td width="15%">Address</td>
                            <td width="50%"><a href="#" id="address" data-bind="editable: inputs.address" data-type="text" data-original-title="Enter device's address"></a><a href="#" target="_blank" data-bind="visible: inputs.address, attr: { href: open_url }"><span class="label label-info">Open <i class="icon-share-alt icon-white"></i></span></a></td>
                            <td width="35%"><span class="muted">Device IP address</span></td>
                        </tr>
                        <tr>
                            <td>Password</td>
                            <td><a href="#" id="password" data-bind="editable: inputs.password" data-type="text" data-original-title="Enter root password"></a></td>
                            <td><span class="muted">root password</span></td>
                        </tr>
                        <tr>
                            <td>RegKey</td>
                            <td><a href="#" id="license" data-bind="editable: inputs.license" data-type="text" data-inputclass="input-large" data-original-title="Enter regkey"></a></td>
                            <td><span class="muted">Base RegKey</span></td>
                        </tr>
                        <tr>         
                            <td>Clean</td>
                            <td>
                                <a href="#" id="clean" class="hide" data-bind="editable: inputs.clean" data-type="text" data-original-title="Are you sure?"></a>
                                <div>
                                    <button type="button" class="btn btn-mini" data-bind="toggle: inputs.clean(), text: inputs.clean() ? 'yes' : 'no', click: function(){ inputs.clean(!inputs.clean()) }">yes</button>
                                </div>
                            </td>
                            <td><span class="muted">Restore factory defaults</span></td>
                        </tr>  
                        <tr data-bind="visible: !inputs.clean()">
                            <td>Provisioning</td>
                            <td><a href="#" id="provision" data-type="select2" data-bind="editable: inputs.provision" data-original-title="Select or type TMOS modules"></a></td>
                            <td><span class="muted">Modules to be provisioned; by default it will set the existing provisioning.</span></td>
                        </tr>
                        <tr data-bind="visible: !inputs.clean()">
                            <td rowspan="2">Self IPs</td>
                            <td><a href="#" id="selfip_internal" data-type="text" data-bind="editable: inputs.selfip_internal" data-emptytext="Internal" data-original-title="IP address with prefix (e.g. 10.10.0.1/16)"></a></td>
                            <td rowspan="2"><span class="muted">Self IPs for internal and external VLANs.</span></td>
                        </tr>
                        <tr data-bind="visible: !inputs.clean()">
                            <td><a href="#" id="selfip_external" data-type="text" data-bind="editable: inputs.selfip_external" data-emptytext="External" data-original-title="IP address with prefix (e.g. 10.11.0.1/16)"></a></td>
                        </tr>
                        <tr data-bind="visible: !inputs.clean()">
                            <td>Timezone</td>
                            <td><a href="#" id="timezone" data-bind="editable: inputs.timezone" data-type="select" data-inputclass="input-large" data-original-title="Select timezone"></a></td>
                            <td><span class="muted">Timezone to be set</span></td>
                        </tr>

                    </tbody>
                </table>
{% endblock %}

{% block head %}
    <link href="/media/select2/select2.css" rel="stylesheet">
    <script src="/media/select2/select2.js"></script>

{% endblock %}

{% block js %}
    <script src="/media/app.config.js"></script>
{% endblock %}
