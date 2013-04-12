{% extends "base.tpl" %}
{% block bvt_active %}active{% endblock %}

{% block title %}BVT Basic{% endblock %}

{% block description %}
     <h2>BVT Basic</h2>
     <p>This is intended for non-EM people who need to validate their builds. Note that <code>Project</code> and <code>Build</code> parameters are required. Click on the dotted links to edit values. Check out the console tab for any log messages.</p>
{% endblock %}

{% block options %}
                <table id="options" class="table table-bordered table-striped" style="clear: both">
                    <tbody> 
                        <tr>         
                            <td width="15%">Project</td>
                            <td width="50%"><a href="#" id="project" data-bind="editable: inputs.project" data-type="text" data-placeholder="Required" data-original-title="Enter a project"></a></td>
                            <td width="35%"><span class="muted">e.g. 11.3.0, corona-bugs</span></td>
                        </tr>
                        <tr>
                            <td>Build</td>
                            <td><a href="#" id="build" data-bind="editable: inputs.build" data-type="text" data-placeholder="Required" data-original-title="Enter a build"></a></td>
                            <td><span class="muted">e.g. 1102.0</span></td>
                        </tr>

                        <tr>
                            <td>Email</td>
                            <td><a href="#" id="submitted_by" data-bind="editable: inputs.submitted_by" data-type="text" data-original-title="Enter an email"></a></td>
                            <td><span class="muted">Email recipient to receive test report</span></td>
                        </tr>
                        <tr>         
                            <td>Debug</td>
                            <td><a href="#" id="debug" data-bind="editable: inputs.debug" data-type="checklist" data-value="1" data-original-title="Enable debug?"></a></td>
                            <td><span class="muted">Run in debug mode</span></td>
                        </tr>  
                        <tr data-bind="visible: inputs.debug().length">
                            <td>Tests</td>
                            <td><a href="#" id="tests" data-bind="editable: inputs.tests" data-type="textarea" data-inputclass="input-xxlarge" data-original-title="Enter test files or directories, one per line"></a></td>
                            <td><span class="muted">The path(s) to the test files</span></td>
                        </tr>

                    </tbody>
                </table>
{% endblock %}

{% block js %}
    <script src="/media/app.bvt_basic.js"></script>
{% endblock %}
