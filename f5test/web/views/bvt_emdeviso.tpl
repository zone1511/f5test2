{% extends "base.tpl" %}
{% block bvt_active %}active{% endblock %}

{% block title %}EM User Build Request{% endblock %}

{% block description %}
     <h2>EM User Build Request</h2>
     <p>This is intended for Developers to validate user builds against the BVT test suite. Note that <code>ISO</code> or <code>Hotfix ISO</code> parameters are required. If testing a hotfix then <code>ISO</code> can be omitted. For BIG-IPs the latest released version (including hotfix) will be used. Click on the dotted links to edit values. Check out the console tab for any log messages.</p>
{% endblock %}

{% block options %}
                <table id="options" class="table table-bordered table-striped" style="clear: both">
                    <tbody> 
                        <tr>         
                            <td width="15%">ISO</td>
                            <td width="50%"><a href="#" id="iso" data-bind="editable: inputs.iso" data-type="text" data-inputclass="input-xxlarge" data-placeholder="Required" data-original-title="Enter the path to the ISO file"></a></td>
                            <td width="35%"><span class="muted">e.g. /build/em/v3.1.1/dist/release/EM-3.1.1.40.0.iso (default: current build)</span></td>
                        </tr>
                        <tr>         
                            <td width="15%">Hotfix ISO</td>
                            <td width="50%"><a href="#" id="hfiso" data-bind="editable: inputs.hfiso" data-type="text" data-inputclass="input-xxlarge" data-placeholder="Required" data-original-title="Enter the path to the ISO file"></a></td>
                            <td width="35%"><span class="muted">e.g. /build/em/v3.1.1-hf4/dist/release/Hotfix-EM-3.1.1-68.0-HF4.iso</span></td>
                        </tr>
                        <tr>
                            <td>Email</td>
                            <td><a href="#" id="email" data-bind="editable: inputs.email" data-type="text" data-original-title="Enter an email"></a></td>
                            <td><span class="muted">Email recipient to receive test report</span></td>
                        </tr>

                    </tbody>
                </table>
{% endblock %}

{% block head %}
    <link href="/media/select2/select2.css" rel="stylesheet">
    <script src="/media/select2/select2.js"></script>

{% endblock %}

{% block js %}
    <script src="/media/app.bvt_emdeviso.js"></script>
{% endblock %}
