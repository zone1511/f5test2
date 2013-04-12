$(function(){

    /*
    
    You can now create a spinner using any of the variants below:
    
    $("#el").spin(); // Produces default Spinner using the text color of #el.
    $("#el").spin("small"); // Produces a 'small' Spinner using the text color of #el.
    $("#el").spin("large", "white"); // Produces a 'large' Spinner in white (or any valid CSS color).
    $("#el").spin({ ... }); // Produces a Spinner using your custom settings.
    
    $("#el").spin(false); // Kills the spinner.
    
    */
    (function($) {
        $.fn.spin = function(opts, color) {
            var presets = {
                "tiny": { lines: 8, length: 2, width: 2, radius: 3 },
                "small": { lines: 8, length: 4, width: 3, radius: 5 },
                "large": { lines: 10, length: 8, width: 4, radius: 8 },
                "custom": { lines: 13, length: 5, width: 2, radius: 5, trail: 30, speed: 0.5 },
                "custom-inverse": { lines: 13, length: 5, width: 2, radius: 5, trail: 30, speed: 0.5,
                                    color: '#fff', left: 464, top: 210 }
            };
            if (Spinner) {
                return this.each(function() {
                    var $this = $(this),
                        data = $this.data();
                    
                    if (data.spinner) {
                        data.spinner.stop();
                        delete data.spinner;
                    }
                    if (opts !== false) {
                        if (typeof opts === "string") {
                            if (opts in presets) {
                                opts = presets[opts];
                            } else {
                                opts = {};
                            }
                            if (color) {
                                opts.color = color;
                            }
                        }
                        data.spinner = new Spinner($.extend({color: $this.css('color')}, opts)).spin(this);
                    }
                });
            } else {
                throw "Spinner class not available.";
            }
        };
    })(jQuery);


    // Custom validators
    ko.validation.rules['nullableInt'] = {
        validator: function (val, validate) {
            return typeof val === "undefined" || val === null || val === "" || (validate && /^-?\d*$/.test(val.toString()));
        },
        message: 'Must be empty or an integer value'
    };
    
    ko.validation.rules['remote'] = {
        validator: function ( val, parms ) { 
            var self = this,
                is_valid = true,
                defaults = {
                    url: '/validate',
                    async: false,
                    type: 'POST',
                    contentType: "application/json; charset=utf-8",
                    dataType: "json",
                    data: { value: val },
                    error: function(r) {
                        if (r.status == 406) {
                            var data = $.parseJSON(r.responseText);
                            self.message = data.message;
                            is_valid = false
                        }
                    }
            };

            var data = $.extend( defaults.data, parms );
            for (var k in data)
                if (ko.isObservable(data[k]))
                    data[k] = data[k]()
            
            defaults.data = JSON.stringify(data);
            if (val)
                $.ajax( defaults );
            return is_valid;
        },
        message: 'Validation error!'
    };
    ko.validation.registerExtenders();

    // We're doing our own radio button toggling, disabling Bootstrap's.
    ko.bindingHandlers.toggle = {
        update: function(element, valueAccessor, allBindingsAccessor) {
            valueAccessor() ? $(element).addClass('active') : $(element).removeClass('active')
        }
    };

    Task = KnockoutApp.Model.extend({
    
        // Define the default values for the model's attributes
        defaults: {
        },

        constructor: function(attributes, options){
            var self = this;
            self.getStatusCss = ko.computed(function(e) {
                return self.isError() ? 'sprite-warning_32' :
                       self.isRevoked() ? 'sprite-block_32' :
                       self.isSuccess() ? 'sprite-tick_32' : 'hide';
            }, self);
            
            $.ajaxSetup({ timeout: 30000 });
            
            $('#status').spin('custom').find('.spinner').hide().attr('data-bind', "visible: isRunning()");
        },

        // Attributes
        interval: 1000,
        revoke_uri: '/revoke',
        status_uri: '/status',
        
        start_btn: '#start-btn',
        updated: false,

        task_id: ko.observable(),
        status: ko.observable(),
        value: ko.observable(),
        logs: ko.observableArray(),
        traceback: ko.observable(),


        // Start button
        start: function() {
            $('.alert').hide();
            var data,
                self = this,
                $elems = $('.editable'),
                errors = $elems.editable('validate'); //run validation for all values

            if($.isEmptyObject(errors)) {
                var data = $elems.editable('getValue'); //get all values
                $('.console').fadeOut();
                //$('.console').slideUp();

                $.ajax({
                    type: 'POST',
                    url: self.task_uri,
                    data: JSON.stringify(data), 
                    contentType: "application/json; charset=utf-8",
                    dataType: 'json'
                }).success(function(response) {
                    if(response) {
                        self.task_id(response.id);
                        self.logs([]);

                        // Mark all fields as "saved" (i.e. remove bold style)
                        $elems.removeClass('editable-unsaved');
                        
                        // Give it a little delay before task gets distributed
                        setTimeout( function() { self.goTask() }, 100);
                    } else {
                       /* server-side validation error */
                    }
                }).error(function(response, textStatus, errorThrown) {
                    /* ajax error */
                    console.log(textStatus);
                    var msg = response.status + ' ' + response.statusText;
                    $('#failure.alert').html(msg).show();
                }).always(function() {
                    $('.console').fadeIn();
                    //$('.console').slideDown();
                });
            } else {
                /* client-side validation error */
                var msg = '';
                $.each(errors, function(k, v) { msg += k+": "+v+"<br>"; });
                $('#validation.alert').html(msg).show();
            }
        },
        
        // Stop button
        stop: function() {
            this.revokeTask();
        },
        
        toggleEditable: function() { $('.editable').editable('toggleDisabled') },
        goTask: function() { location.hash = this.task_id() },
        isSuccess: function() { return this.status() == 'SUCCESS' },
        isError: function() { return this.status() == 'FAILURE' },
        isRevoked: function() { return this.status() == 'REVOKED' },
        isRunning: function() { return this.status() == 'PENDING' ||
                                       this.status() == 'STARTED' },

        revokeTask: function() {
            $('.alert').hide();
            var url = this.revoke_uri + '/' + this.task_id(),
                self = this;
            $.getJSON(url, function (data) {
                self.status(data.status);
            });
        },
        
        stop_refresh: function (interval) {
            $('.spinner').hide();
            clearTimeout(interval);
        },

        refresh: function () {
            var self = this,
                interval,
                url = this.status_uri + '/' + this.task_id() + '?s=' + this.logs().length;

            $.getJSON(url, function (data) {
                if (data.result && data.result.logs) {
                    ko.utils.arrayPushAll(self.logs, data.result.logs);
                } else {
                    self.logs([])
                }

                self.value(data.value);
                
                if (data.traceback) {
                    self.traceback(data.traceback)
                }

                self.status(data.status);

                if (!self.updated && data.result && data.result.user_input) {
                    ko.mapping.fromJS(data.result.user_input, self.inputs);
                    self.updated = true;
                }

                if (data.status == 'PENDING')
                    self.pending_count--;
                else if (data.status != 'STARTED')
                    self.stop_refresh(interval);
                
                if (self.pending_count <= 0) {
                    $('#failure.alert').show().find("span").text("Task expired?");
                    self.stop_refresh(interval);
                }

            }).error(function () {
                // If there is an error stop pulling from the server
                self.stop_refresh(interval);
            });
            interval = setTimeout(function () { self.refresh() }, self.interval);
        },

        // Client-side routes    
        setup_routes: function() {
            var self = this;
            Sammy(function() {
                this.get(self.task_uri, function() { self.logs([]) });
                this.get('#:task_id', function() {
                    self.task_id(this.params.task_id);
                    self.pending_count = 3; // Retry on PENDING status before giving up.
                    self.refresh();
                });
            }).run();
        },

    });

});
