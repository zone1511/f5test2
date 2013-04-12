{% extends "base.tpl" %}
{% block add_active %}active{% endblock %}

{% block title %}Demo{% endblock %}

{% block description %}
     <h2>Demo task</h2>
     <p>This task adds two different integers provided by the <code>Number 1</code> and <code>Number 2</code> options. Click on the dotted links to edit values. Check out the console tab for any log messages.</p>
{% endblock %}

{% block options %}
                <table id="options" class="table table-bordered table-striped" style="clear: both">
                    <tbody> 
                        <tr>         
                            <td width="15%">Number 1</td>
                            <td width="50%"><a href="#" id="number_1" data-bind="editable: inputs.number_1" data-type="text" data-placeholder="Required" data-original-title="Enter a number"></a></td>
                            <td width="35%"><span class="muted">Simple integer field</span></td>
                        </tr>
                        <tr>
                            <td width="15%">Number 2</td>
                            <td width="50%"><a href="#" id="number_2" data-bind="editable: inputs.number_2" data-type="text" data-original-title="Enter a number"></a></td>
                            <td width="35%"><span class="muted">Simple integer field</span></td>
                        </tr>

                        <tr>
                            <td width="15%">Username</td>
                            <td width="50%"><a href="#" id="username" data-bind="editable: inputs.username" data-type="text" data-original-title="Enter username">superuser</a></td>
                            <td width="35%"><span class="muted">Simple text field</span></td>
                        </tr>
                        <tr>         
                            <td>First name</td>
                            <td><a href="#" id="firstname" data-bind="editable: inputs.firstname" data-type="text" data-placement="right" data-placeholder="Required" data-original-title="Enter your firstname"></a></td>
                            <td><span class="muted">Required text field, originally empty</span></td>
                        </tr>  
                        <tr>         
                            <td>Sex</td>
                            <td><a href="#" id="sex" data-bind="editable: inputs.sex" data-type="select" data-original-title="Select sex"></a></td>
                            <td><span class="muted">Select, loaded from js array. Custom display</span></td>
                        </tr>
                        <tr>         
                            <td>Fresh fruits</td>
                            <td><a href="#" id="fruits" data-bind="editable: inputs.fruits" data-type="checklist" data-value="2,3" data-original-title="Select fruits"></a></td>
                            <td><span class="muted">Checklist</span></td>
                        </tr>

                    </tbody>
                </table>
{% endblock %}

{% block js %}
    <script src="/media/app.add.js"></script>
{% endblock %}
