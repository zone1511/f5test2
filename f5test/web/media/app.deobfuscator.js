$(function(){

    //defaults
    $.fn.editable.defaults.send = 'never'; 
    $.fn.editable.defaults.emptytext = 'Click to edit';


    var MyTask = Task.extend({
    
        // Define the default values for the model's attributes
        defaults: {
        },

        // Start button
        start: function() {
            var self = this,
                input = $('input').val();

            var data = {'input': input};

            $.ajax({
                type: 'POST',
                url: self.task_uri,
                data: JSON.stringify(data), 
                contentType: "application/json; charset=utf-8",
                dataType: 'json'
            }).success(function(response) {
                if(response) {
                    // Mark all fields as "saved" (i.e. remove bold style)
                    //$elems.removeClass('editable-unsaved');
                    self.inputs.input(response.input);
                } else {
                   /* server-side validation error */
                }
            });
        },
        

        // Attributes
        task_uri: '/deobfuscator',
        inputs: ko.mapping.fromJS({
          input: ko.observable()
        }),

    });

    var task = new MyTask();
    //task.setup_routes();
    ko.applyBindings(task);

});
