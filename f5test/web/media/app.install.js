$(function(){

    //defaults
    $.fn.editable.defaults.send = 'never'; 
    $.fn.editable.defaults.emptytext = 'Click to edit';

    //editables
    $('#debug').editable({
        source: [
              {value: 1, text: 'enabled'},
        ],
        display: function(value, sourceData) {
             var colors = {"": "gray", 1: "green", 2: "blue"},
                 elem = $.grep(sourceData, function(o){return o.value == value;});
                 
             if(elem.length) {    
                 $(this).text(elem[0].text).css("color", colors[value]); 
             } else {
                 $(this).text('disabled').css("color", colors['']);
             }
        }
    });

    $('#device').on('shown', function() {
          if ($(this).data('editable').input.$tpl)
                $(this).data('editable').input.$tpl.filter('.device-rootusername,.device-adminusername,.device-adminpassword').hide();
    });

    $('#product').editable({
        source: [
            {value: 'em', text: 'EM'},
            {value: 'bigiq', text: 'BIG-IQ'},
            {value: 'bigip', text: 'BIG-IP'}
        ]
    });

    $('#config').editable({
        display: function(value, sourceData) {
             if(value == null)
             	return;
             var colors = {'': "gray", 'essential': "green"},
                 elem = $.grep(sourceData, function(o){return o.value == value;});

             if(elem.length) {    
                 $(this).text(elem[0].text).css("color", colors[value]); 
             } else {
                 $(this).text('disabled').css("color", colors['']);
             }
        },
        source: [
            {value: '', text: 'roll forward'},
            {value: 'essential', text: 'clean'}
        ]
    });

    $('#format').editable({
        prepend: "leave unchanged",
        source: [
            {value: 'volumes', text: 'volumes'},
            {value: 'partitions', text: 'partitions'}
        ],
        display: function(value, sourceData) {
             if(value == null)
             	return;
             var colors = {"": "gray", 1: "green", 2: "blue"},
                 elem = $.grep(sourceData, function(o){return o.value == value;});

             if(elem.length) {    
                 $(this).text(elem[0].text).css("color", colors[value]); 
             } else {
                 $(this).empty(); 
             }
        }   
    });

    $('#user .editable').on('hidden', function(e, reason){
         if(reason === 'save' || reason === 'nochange') {
             var $next = $(this).closest('tr').next().find('.editable');
             if($('#autoopen').is(':checked')) {
                 setTimeout(function() {
                     $next.editable('show');
                 }, 300); 
             } else {
                 $next.focus();
             } 
         }
    });

    var MyTask = Task.extend({
    
        // Define the default values for the model's attributes
        defaults: {
        },

        constructor: function(attributes, options){
            this.constructor.__super__.constructor();
            this.open_url = ko.computed(function() {
                return "https://" + this.inputs.address();
            }, this);
            this.inputs.version.extend({ remote: { type: 'project',
                                                   product: this.inputs.product } });
            this.inputs.build.extend({ remote: { type: 'build',
                                                 project: this.inputs.version,
                                                 hotfix: this.inputs.hotfix,
                                                 product: this.inputs.product } });
            this.inputs.hotfix.extend({ remote: { type: 'hotfix',
                                                 project: this.inputs.version,
                                                 build: this.inputs.build,
                                                 product: this.inputs.product } });
        },

        // Attributes
        task_uri: '/install',
        inputs: ko.mapping.fromJS({
          address: ko.observable().extend({ required: true }),
          admin_password: ko.observable('admin'),
          root_password: ko.observable('default'),
          product: ko.observable('bigiq').extend({ required: true }),
          version: ko.observable('bigiq-mgmt').extend({ required: true }),
          build: ko.observable(),
          hotfix: ko.observable(),
          customiso: ko.observable().extend({ remote: { type: 'file' } }),
          config: ko.observable(),
          format: ko.observable()
        }),

        // Methods
        /*refresh: function() {
            console.log('refreshed');
        },*/

    });

    var task = new MyTask();
    task.setup_routes();
    ko.applyBindings(task);

});
