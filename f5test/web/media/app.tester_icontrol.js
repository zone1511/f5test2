$(function(){

    //defaults
    $.fn.editable.defaults.send = 'never'; 
    $.fn.editable.defaults.emptytext = 'Click to edit';

    $(document).ready(function() {
      $('pre code').each(function(i, e) { hljs.highlightBlock(e) });
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
        interval: 100,
        task_uri: '/tester/icontrol',
        inputs: ko.mapping.fromJS({
          address: ko.observable().extend({ required: true }),
          password: ko.observable('admin'),
          method: ko.observable('System.SystemInfo.get_system_information').extend({ required: true }),
          arguments: ko.observable()
        }),

    });

    var task = new MyTask();
    task.setup_routes();
    ko.applyBindings(task);

    // Re-highlight console content on value change
    task.value.subscribe(function(e) {
        $('pre code').each(function(i, e) { hljs.highlightBlock(e) });
    });

    task.traceback.subscribe(function(e) {
        $('pre code').each(function(i, e) { hljs.highlightBlock(e) });
    });

});
