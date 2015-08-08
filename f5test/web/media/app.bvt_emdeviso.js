$(function(){

    //defaults
    $.fn.editable.defaults.send = 'never'; 
    $.fn.editable.defaults.emptytext = 'Click to edit';

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
        },

        // Attributes
        task_uri: '/bvt/emdeviso',
        inputs: ko.mapping.fromJS({
          iso: ko.observable().extend({ remote: { type: 'file' }, required: false }),
          hfiso: ko.observable().extend({ remote: { type: 'file' }, required: false }),
          email: ko.observable(),
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
