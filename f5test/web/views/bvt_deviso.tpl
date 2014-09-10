{% extends "base.tpl" %}
{% block bvt_active %}active{% endblock %}

{% block title %}BIG-IQ Request{% endblock %}

{% block description %}
     <h2>BIG-IQ Request</h2>
     <p>This is intended for Developers who need to validate BIG-IQ user builds. Note that if the <code>ISO</code> parameter is not specified, the latest build from <span class="label label-inverse">bigiq-mgmt</span> branch will be assumed. Click on the dotted links to edit values. Check out the console tab for any log messages.</p>
{% endblock %}

{% block options %}
                <table id="options" class="table table-bordered table-striped" style="clear: both">
                    <tbody> 
                        <tr>         
                            <td width="15%">ISO</td>
                            <td width="50%"><a href="#" id="iso" data-bind="editable: inputs.iso" data-type="text" data-inputclass="input-xxlarge" data-placeholder="Required" data-original-title="Enter the path to the ISO file"></a></td>
                            <td width="35%"><span class="muted">e.g. /vol/3/user/harrison/EM-3.2.0.0.0.3.iso</span></td>
                        </tr>

                        <tr>
                            <td>Email</td>
                            <td><a href="#" id="email" data-bind="editable: inputs.email" data-type="text" data-original-title="Enter an email"></a></td>
                            <td><span class="muted">Email recipient to receive test report</span></td>
                        </tr>
                        <tr>
                            <td>Suite</td>
                            <td><a href="#" id="suite" data-bind="editable: inputs.suite" data-type="select" data-original-title="Which test suite?"></a></td>
                            <td><span class="muted">Select the test suite to be run</span></td>
                        </tr>  

                    </tbody>
                </table>
{% endblock %}

{% block js %}
    <script src="/media/app.bvt_deviso.js"></script>
{% endblock %}
