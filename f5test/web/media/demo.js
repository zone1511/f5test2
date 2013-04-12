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
    $('#number_1, #number_2').editable()
    .each(function() {$(this).data('editable').input.value2submit = function(value){return parseInt(value)}});

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




	function MyViewModel() {
	    // Data
	    var self = this;
	    self.interval = 1000;
	    self.task_id = ko.observable();
	    self.status = ko.observable();
	    self.logs = ko.observableArray();
	    self.traceback = ko.observable();

	    self.task_uri = '/add';
		self.revoke_uri = '/revoke';
		self.status_uri = '/status';
	    self.inputs = ko.mapping.fromJS({
	    	number_1: ko.observable(),
         	number_2: ko.observable(),
         	username: ko.observable(),
         	firstname: ko.observable().extend({ required: true, minLength: 3}),
         	sex: ko.observable(),
         	fruits: ko.observableArray([2,3])
        });

	    //console.log(self.inputs.sex.fn);

	    // Behaviours    
	    this.start = function() {
		    //$('#start-btn').attr('disabled', 'disabled');
		    $('.alert').hide();
		    var data,
		        $elems = $('.editable'),
		        errors = $elems.editable('validate'); //run validation for all values
		    if($.isEmptyObject(errors)) {
		        data = $elems.editable('getValue'); //get all values
		        $.ajax({
		            type: 'POST',
		            url: self.task_uri,
		            data: JSON.stringify(data), 
		            contentType: "application/json; charset=utf-8",
		            dataType: 'json'
		        }).success(function(response) {
		            if(response) {
		            	self.toggleEditable();
			            self.task_id(response.id);
			            //setTimeout( function() { self.goTask() }, 1000);
			            self.goTask();
		            } else {
		               /* server-side validation error */
		            }
		        }).error(function(response) {
		            /* ajax error */
		            var msg = response.status + ' ' + response.statusText;
		            $('#failure.alert').html(msg).show();
		        });
		    } else {
		        /* client-side validation error */
	            var msg = '';
	            $.each(errors, function(k, v) { msg += k+": "+v+"<br>"; });
				$('#validation.alert').html(msg).show();
		    }
	    };
		this.stop = function() {
			self.inputs.firstname('booo');
			self.inputs.sex(1);
			self.inputs.fruits([1]);
			self.revokeTask();
		};
	    
	    // Methods
	    self.toggleEditable = function() { $('#user .editable').editable('toggleDisabled'); }
	    self.goTask = function() { location.hash = self.task_id() };
	    self.revokeTask = function() {
		    $('.alert').hide();
		    //console.log('revoking...');
	    	url = self.revoke_uri + '/' + self.task_id();
	        $.getJSON(url, function (data) {
	        	self.status(data.status);
	        });
	    }
	    self.isError = function() { return self.status() == 'FAILURE' };
	    self.refresh = function () {
	    	url = self.status_uri + '/' + self.task_id();
	        $.getJSON(url, function (data) {
	        	if (data.result && data.result.logs) {
	        		self.logs(data.result.logs)
	        	} else {
	        		self.logs([])
	        	}
	        	
        		if (data.traceback) {
	        		self.traceback(data.traceback)
	        	}
	        	
	        	console.log(data);
	        	self.status(data.status);
	        	if (data.result && data.result.user_input)
	        		ko.mapping.fromJS(data.result.user_input, self.inputs);

				if (data.status == 'PENDING')
	        		self.pending_count--;
	        	else if (data.status != 'STARTED')
	        		clearTimeout(interval);
	        	
	        	if (self.pending_count <= 0) {
	        		$('#failure.alert').show().find("span").text("Task not found!");
		            clearTimeout(interval);
		        }

	        	if (data.status == 'SUCCESS')
		            $('#success.alert').show().find("span").text("Return value: " + data.value);

	        	if (data.status == 'FAILURE' || data.status == 'REVOKED') 
		            $('#failure.alert').show().find("span").text("Task stopped!");

	        }).error(function () {
	            //If there is an error stop pulling from the server
	            clearTimeout(interval);
	        });
	        interval = setTimeout(function () { self.refresh() }, self.interval);
	    };

	    // Client-side routes    
	    Sammy(function() {
	        this.get(self.task_uri, function() { self.logs([]); });
	        this.get('#:task_id', function() {
	            self.task_id(this.params.task_id);
	            self.pending_count = 3; // Retry on PENDING status before giving up.
	            self.refresh();
	        });

	    }).run();    

	};
	
	ko.applyBindings(new MyViewModel());
});
