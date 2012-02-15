/*
  ###########################################################################
  #
  # This program is part of Zenoss Core, an open source monitoring platform.
  # Copyright (C) 2012, Zenoss Inc.
  #
  # This program is free software; you can redistribute it and/or modify it
  # under the terms of the GNU General Public License version 2 or (at your
  # option) any later version as published by the Free Software Foundation.
  #
  # For complete information please visit: http://www.zenoss.com/oss/
  #
  ###########################################################################
*/
(function() {
    /**
     * A regular text field that allows a person to provide an example of
     * valid input. This will appear in italics next to the input
     *
     *
     *@class Zenoss.form.ExampleTextField
     *@extends Ext.form.field.Text
     */
    Ext.define("Zenoss.form.ExampleTextField", {
        alias:['widget.exampletextfield'],
        extend:"Ext.form.field.Text",
        /**
         * @cfg {String} example A custom example message to display to the bottom right of the field.
         */
        config: {
            example: null
        },
        constructor: function(config){
            config = config || {};
            config.style = config.style || {};
            // make sure there is enough room for the example
            Ext.applyIf(config.style, {
                paddingBottom: 20
            });
            this.callParent([config]);
        },
        onRender: function() {
            this.callParent(arguments);
            if (this.example) {
                Ext.DomHelper.append(this.el.id, {
                    tag: 'span',
                    cls: 'example',
                    html: _t('Example:') + " " + this.example
                });
            }
        }
    });


}());

