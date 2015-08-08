{% extends "base.tpl" %}
{% block bvt_active %}active{% endblock %}

{% block title %}BIG-IQ User Build Request{% endblock %}

{% block description %}
     <h2>BIG-IQ User Build Request</h2>
     <p>This is intended for Developers to validate user builds against the BVT test suite (or a subset of it). Note that if the <code>ISO</code> parameter is not specified, the latest build from <span class="label label-inverse">bigiq-mgmt</span> branch will be assumed. Click on the dotted links to edit values. Check out the console tab for any log messages.</p>
{% endblock %}

{% block options %}
                <table id="options" class="table table-bordered table-striped" style="clear: both">
                    <tbody> 
                        <tr>         
                            <td width="15%">ISO</td>
                            <td width="50%"><a href="#" id="iso" data-bind="editable: inputs.iso" data-type="text" data-inputclass="input-xxlarge" data-placeholder="Required" data-original-title="Enter the path to the ISO file"></a></td>
                            <td width="35%"><span class="muted">e.g. /build/bigiq/project/bigiq-mgmt/daily/build7932.0/BIG-IQ-bigiq-mgmt-4.6.0.0.0.7932.iso (default: current build)</span></td>
                        </tr>
                        <tr>         
                            <td width="15%">Hotfix ISO</td>
                            <td width="50%"><a href="#" id="hfiso" data-bind="editable: inputs.hfiso" data-type="text" data-inputclass="input-xxlarge" data-placeholder="Required" data-original-title="Enter the path to the ISO file"></a></td>
                            <td width="35%"><span class="muted">e.g. /build/bigiq/v4.5.0-hf2/daily/build7131.0/Hotfix-BIG-IQ-4.5.0-2.0.7131-HF2.iso</span></td>
                        </tr>
                        <tr>
                            <td>Email</td>
                            <td><a href="#" id="email" data-bind="editable: inputs.email" data-type="text" data-original-title="Enter an email"></a></td>
                            <td><span class="muted">Email recipient to receive test report</span></td>
                        </tr>
                        <tr>
                            <td>High Availability</td>
                            <td><a href="#" id="ha" data-bind="editable: inputs.ha" data-type="checklist" data-original-title="Selection"></a></td>
                            <td><span class="muted">Include any HA tests in addition to standalone?</span></td>
                        </tr>  
                        <tr>
                            <td>Module</td>
                            <td><a href="#" id="module" data-bind="editable: inputs.module" data-type="select2" data-original-title="Select modules"></a></td>
                            <td><span class="muted">Modules to be tested</span></td>
                        </tr>
                        <tr>
                            <td>UI vs API</td>
                            <td>
                                <a href="#" id="ui" class="hide" data-bind="editable: inputs.ui" data-type="select"></a>
	                            <div>
	                                <button type="button" class="btn btn-mini" data-bind="toggle: inputs.ui() == 'api', click: function(){ inputs.ui('api') }">API</button>
	                                <button type="button" class="btn btn-mini" data-bind="toggle: inputs.ui() == 'ui', click: function(){ inputs.ui('ui') }">UI</button>
	                                <button type="button" class="btn btn-mini" data-bind="toggle: !inputs.ui(), click: function(){ inputs.ui(false) }">API + UI</button>
	                            </div>
							</td>
                            <td><span class="muted">Include UI tests?</span></td>
                        </tr>

                    </tbody>
                </table>
{% endblock %}

{% block head %}
    <link href="/media/select2/select2.css" rel="stylesheet">
    <script src="/media/select2/select2.js"></script>

{% endblock %}

{% block js %}
    <script src="/media/app.bvt_deviso.js"></script>
{% endblock %}
