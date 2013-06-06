$(function(){

    //defaults
    $.fn.editable.defaults.send = 'never'; 
    $.fn.editable.defaults.emptytext = 'Click to edit';

    //editables
    $('#provision').editable({
        inputclass: 'input-large',
        select2: {
           tags: ['ltm', 'gtm', 'asm', 'afm'],
           multiple: true
        }
    });

    $('#timezone').editable({
        showbuttons: false,
        source: [
              {value: 'America/Los_Angeles', text: 'US West'},
              {value: 'America/New_York', text: 'US East'},
        ]
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
        },

        // Attributes
        task_uri: '/config',
        inputs: ko.mapping.fromJS({
          //device: { rootpassword: 'default' },
          address: ko.observable().extend({ required: true }),
          password: ko.observable('default'),
          provision: ko.observableArray([]),
          selfip_internal: ko.observable(),
          selfip_external: ko.observable(),
          license: ko.observable(),
          timezone: ko.observable('America/Los_Angeles'),
          clean: ko.observable(false),
          
          email: ko.observable(),
          debug: ko.observableArray([]),
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
