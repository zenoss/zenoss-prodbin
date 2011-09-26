/*
  ###########################################################################
  #
  # This program is part of Zenoss Core, an open source monitoring platform.
  # Copyright (C) 2010, Zenoss Inc.
  #
  # This program is free software; you can redistribute it and/or modify it
  # under the terms of the GNU General Public License version 2 or (at your
  # option) any later version as published by the Free Software Foundation.
  #
  # For complete information please visit: http://www.zenoss.com/oss/
  #
  ###########################################################################
*/

/* package level */
(function() {

    Ext.ns('Zenoss.form');
    /**
     * This is a display field that takes an array as its value and
     * renders them with one element per line
     **/
    Ext.define("Zenoss.form.MultiLineDisplayField", {
        alias:['widget.multilinedisplayfield'],
        extend:"Ext.form.DisplayField",
        constructor: function(config) {
            // if a string was passed in then defer to the parents behavior
            if ((typeof config.value) != 'string') {
                config.value = config.value.join('<br />');
            }

            Zenoss.form.MultiLineDisplayField.superclass.constructor.apply(this, arguments);
        }
    });

}());
