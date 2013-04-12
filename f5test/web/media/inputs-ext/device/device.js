/**
Device address and credentials editable input.
Internally value stored as {address: "10.1.1.2", adminusername: "admin", adminpassword: "admin",
                            rootusername: "root", rootpassword: "default"}

@class device
@extends abstractinput
@final
@example
<a href="#" id="device" data-type="device">awesome</a>
<script>
$(function(){
    $('#device').editable({
        url: '/post',
        title: 'Enter device's address and credentials',
        value: {
            address: "169.254.2.1", 
            adminusername: "admin", 
            adminpassword: "admin",
            rootusername: "root", 
            rootpassword: "default"
        }
    });
});
</script>
**/
(function ($) {
    var Device = function (options) {
        this.init('device', options, Device.defaults);
    };

    //inherit from Abstract input
    $.fn.editableutils.inherit(Device, $.fn.editabletypes.abstractinput);

    $.extend(Device.prototype, {
        /**
        Renders input from tpl

        @method render() 
        **/        
        render: function() {
           this.$input = this.$tpl.find('input');
        },
        
        /**
        Default method to show value in element. Can be overwritten by display option.
        
        @method value2html(value, element) 
        **/
        value2html: function(value, element) {
            value = ko.mapping.toJS(value);
            console.log(value);

            if(!value.address) {
                $(element).empty();
                return; 
            }
            
            var html = $('<div>').text(value.address).html() + ' / ' + 
                       (value.adminpassword ? $('<div>').text(value.adminpassword).html() + ' / ' : '') +
                       (value.rootpassword ? $('<div>').text(value.rootpassword).html() + '' : '');
            $(element).html(html);
        },
        
        /**
        Gets value from element's html
        
        @method html2value(html) 
        **/        
        html2value: function(html) {        
          return null;  
        },
      
       /**
        Converts value to string. 
        It is used in internal comparing (not for sending to server).
        
        @method value2str(value)  
       **/
       value2str: function(value) {
           //console.log(value);
           var str = '';
           if(value) {
               for(var k in value) {
                   str = str + k + ':' + value[k] + ';';  
               }
           }
           return str;
       }, 
       
       /*
        Converts string to value. Used for reading value from 'data-value' attribute.
        
        @method str2value(str)  
       */
       str2value: function(str) {
           /*
           this is mainly for parsing value defined in data-value attribute. 
           If you will always set value by javascript, no need to overwrite it
           */
           return str;
       },                
       
       /**
        Sets value of input.
        
        @method value2input(value) 
        @param {mixed} value
       **/         
       value2input: function(value) {
            value = ko.mapping.toJS(value);

           //console.log(value);
           this.$input.filter('[name="address"]').val(value.address);
           this.$input.filter('[name="adminusername"]').val(value.adminusername);
           this.$input.filter('[name="adminpassword"]').val(value.adminpassword);
           this.$input.filter('[name="rootusername"]').val(value.rootusername);
           this.$input.filter('[name="rootpassword"]').val(value.rootpassword);
       },       
       
       /**
        Returns value of input.
        
        @method input2value() 
       **/          
       input2value: function() { 
           return {
              address: this.$input.filter('[name="address"]').val(), 
              adminusername: this.$input.filter('[name="adminusername"]').val(), 
              adminpassword: this.$input.filter('[name="adminpassword"]').val(),
              rootusername: this.$input.filter('[name="rootusername"]').val(), 
              rootpassword: this.$input.filter('[name="rootpassword"]').val()
           };
       },        
       
        /**
        Activates input: sets focus on the first field.
        
        @method activate() 
       **/        
       activate: function() {
            this.$input.filter('[name="address"]').focus();
       },  
       
       /**
        Attaches handler to submit form in case of 'showbuttons=false' mode
        
        @method autosubmit() 
       **/       
       autosubmit: function() {
           this.$input.keydown(function (e) {
                if (e.which === 13) {
                    $(this).closest('form').submit();
                }
           });
       }       
    });

    Device.defaults = $.extend({}, $.fn.editabletypes.abstractinput.defaults, {
        tpl: '<div class="editable-device"><label><span>Address: </span><input type="text" name="address" class="input-medium"></label></div>'+
             '<div class="editable-device device-adminusername"><label><span>Admin Username: </span><input type="text" name="adminusername" class="input-small"></label></div>'+
             '<div class="editable-device device-adminpassword"><label><span>Admin Password: </span><input type="text" name="adminpassword" class="input-small"></label></div>'+
             '<div class="editable-device device-rootusername"><label><span>Root Username: </span><input type="text" name="rootusername" class="input-small"></label></div>'+
             '<div class="editable-device device-rootpassword"><label><span>Root Password: </span><input type="text" name="rootpassword" class="input-small"></label></div>',

        inputclass: ''
    });

    $.fn.editabletypes.device = Device;

}(window.jQuery));
