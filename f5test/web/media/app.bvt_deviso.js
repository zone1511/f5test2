$(function(){

    //defaults
    $.fn.editable.defaults.send = 'never'; 
    $.fn.editable.defaults.emptytext = 'Click to edit';

    //editables
    $('#debug').editable({
        //value: [1],    
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
        task_uri: '/bvt/deviso',
        inputs: ko.mapping.fromJS({
          iso: ko.observable().extend({ remote: { type: 'file' }, required: true }),
          email: ko.observable(),
          debug: ko.observableArray([]),
          tests: ko.observable("tests/_examples/test_icontrol.py"),
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
