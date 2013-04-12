$(function(){

    //defaults
    $.fn.editable.defaults.url = '/post';
    $.fn.editable.defaults.send = 'never'; 
    $.fn.editable.defaults.emptytext = 'Click to edit';

    //enable / disable
    $('#enable').click(function() {
        $('#user .editable').editable('toggleDisabled');
    });
    
    //editables
    /*
    $('#number_1, #number_2').editable()
    .each(function() {$(this).data('editable').input.value2submit = function(value){return parseInt(value)}});
    */

    $('#username').editable({
           url: '/post',
           //pk: 1,
           type: 'text',
           name: 'username',
           title: 'Enter username'
    });
    
    $('#sex').editable({
        prepend: "not selected",
        source: [
            {value: 1, text: 'Male'},
            {value: 2, text: 'Female'}
        ],
        display: function(value, sourceData) {
             var colors = {"": "gray", 1: "green", 2: "blue"},
                 elem = $.grep(sourceData, function(o){return o.value == value;});
                 
             if(elem.length) {    
                 $(this).text(elem[0].text).css("color", colors[value]); 
             } else {
                 $(this).empty(); 
             }
        }   
    })
    .each(function() {$(this).data('editable').input.value2submit = function(value){return parseInt(value)}});
    
    $('#fruits').editable({
       limit: 3,
       source: [
        {value: 1, text: 'banana'},
        {value: 2, text: 'peach'},
        {value: 3, text: 'apple'},
        {value: 4, text: 'watermelon'},
        {value: 5, text: 'orange'}
       ]
    }).data('editable').input.value2submit = function(value){return $.map(value, function(value){ return parseInt(value) })};
    
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

    var AddTask = Task.extend({
    
        // Define the default values for the model's attributes
        defaults: {
        },

        constructor: function(attributes, options){
            this.constructor.__super__.constructor();
            //console.log('child constr');
            //console.log(this.blah);
        },

        // Attributes
        task_uri: '/add',
        inputs: ko.mapping.fromJS({
          number_1: ko.observable().extend({ nullableInt: true }),
          number_2: ko.observable().extend({ nullableInt: true }),
          username: ko.observable(),
          firstname: ko.observable().extend({ required: true, minLength: 3}),
          sex: ko.observable(),
          fruits: ko.observableArray([2,3])
        }),

        // Methods
        /*refresh: function() {
            console.log('refreshed');
        },*/

    });

    var task = new AddTask();
    task.setup_routes();
    ko.applyBindings(task);

});
