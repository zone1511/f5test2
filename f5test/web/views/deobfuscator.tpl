{% extends "base.tpl" %}

{% block title %}BIG-IQ Password Deobfuscator{% endblock %}

{% block description %}
     <p>Paste the encrypted string below. Example: <code>lrIlNvVdwgpwnJNK+net8w==</code></p>
     <input type="text" data-bind="value: inputs.input" style="margin-bottom: 0px; width: 400px;"></input>

     <button id="start-btn" class="btn btn-primary" data-bind="click: start">
     <i class=""></i><span>Decrypt</span></button>
{% endblock %}

{% block options %}
{% endblock %}

{% block content %}
{% endblock %}

{% block head %}
{% endblock %}

{% block js %}
    <script src="/media/app.deobfuscator.js"></script>
{% endblock %}
